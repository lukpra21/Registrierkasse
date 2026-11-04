"""Export für den Steuerberater.

- ``belege_csv``: alle Kassenbelege eines Zeitraums mit Aufteilung nach Steuersätzen
- ``rechnungen_csv``: Ausgangsrechnungen (inkl. Zahlungsstatus)
- ``bmd_buchungen``: Tageslosungen als Buchungszeilen im BMD-NTCS-Importformat
  (Semikolon, Dezimalkomma, Windows-1252). Kontonummern sind über die
  Einstellungen anpassbar – Feldbelegung mit dem Steuerberater abstimmen.
"""

from __future__ import annotations

import csv
import io
import sqlite3
import zipfile
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

from .db import einstellung
from .geld import netto_aus_brutto, rksv_betrag

SPALTEN = {"20": "betrag_normal", "10": "betrag_ermaessigt1", "13": "betrag_ermaessigt2",
           "0": "betrag_null", "19": "betrag_besonders"}

STANDARD_KONTEN = {
    "konto_kassa": "2700",
    "konto_karte": "2880",  # Verrechnungskonto Kartenzahlungen
    "konto_erloes_20": "4000",
    "konto_erloes_10": "4010",
    "konto_erloes_13": "4013",
    "konto_erloes_0": "4090",
    "konto_erloes_19": "4019",
}

STEUERCODE = {"20": "1", "10": "1", "13": "1", "19": "1", "0": "0"}


def _konto(con, schluessel: str) -> str:
    return einstellung(con, schluessel, STANDARD_KONTEN.get(schluessel, "")) or STANDARD_KONTEN.get(schluessel, "")


def _csv(zeilen: list[list], kopf: list[str], encoding="utf-8-sig") -> bytes:
    puffer = io.StringIO()
    w = csv.writer(puffer, delimiter=";", lineterminator="\r\n")
    w.writerow(kopf)
    w.writerows(zeilen)
    return puffer.getvalue().encode(encoding, errors="replace")


def belege_csv(con: sqlite3.Connection, von: str, bis: str) -> bytes:
    kopf = ["Belegnummer", "Datum", "Uhrzeit", "Art", "Zahlungsart", "Kunde", "Kassier",
            "Brutto 20%", "Brutto 10%", "Brutto 13%", "Brutto 0%", "Brutto 19%", "Brutto gesamt",
            "Netto gesamt", "USt gesamt", "Storno von", "Ausfall"]
    zeilen = []
    for b in con.execute(
        "SELECT b.*, k.name AS kunde, u.name AS kassier, s.belegnummer AS storno_nr FROM belege b"
        " LEFT JOIN kunden k ON k.id = b.kunde_id LEFT JOIN benutzer u ON u.id = b.benutzer_id"
        " LEFT JOIN belege s ON s.id = b.storno_von"
        " WHERE substr(b.zeitpunkt, 1, 10) BETWEEN ? AND ? ORDER BY b.belegnummer", (von, bis)):
        brutto = {s: b[sp] for s, sp in SPALTEN.items()}
        netto = sum(netto_aus_brutto(v, s) for s, v in brutto.items() if v)
        gesamt = sum(brutto.values())
        zeilen.append([b["belegnummer"], b["zeitpunkt"][:10], b["zeitpunkt"][11:], b["art"], b["zahlungsart"] or "",
                       b["kunde"] or "", b["kassier"] or "", *(rksv_betrag(brutto[s]) for s in ("20", "10", "13", "0", "19")),
                       rksv_betrag(gesamt), rksv_betrag(netto), rksv_betrag(gesamt - netto), b["storno_nr"] or "",
                       "ja" if b["ausfall"] else ""])
    return _csv(zeilen, kopf)


def rechnungen_csv(con: sqlite3.Connection, von: str, bis: str) -> bytes:
    kopf = ["Rechnungsnummer", "Datum", "Kunde", "UID Kunde", "Zahlungsart", "Netto", "USt", "Brutto", "Bezahlt am"]
    zeilen = []
    for d in con.execute(
        "SELECT d.*, k.name, k.uid FROM dokumente d JOIN kunden k ON k.id = d.kunde_id"
        " WHERE d.typ = 'Rechnung' AND d.datum BETWEEN ? AND ? ORDER BY d.nummer", (von, bis)):
        steuern: dict[str, int] = {}
        for p in con.execute("SELECT * FROM dokumentpositionen WHERE dokument_id = ?", (d["id"],)):
            s = int((Decimal(p["menge"]) * p["einzelpreis_cent"]).quantize(Decimal("1"), ROUND_HALF_UP))
            steuern[p["steuer_prozent"]] = steuern.get(p["steuer_prozent"], 0) + s
        brutto = sum(steuern.values())
        netto = sum(netto_aus_brutto(v, s) for s, v in steuern.items())
        zeilen.append([d["nummer"], d["datum"], d["name"], d["uid"] or "", d["zahlungsart"] or "",
                       rksv_betrag(netto), rksv_betrag(brutto - netto), rksv_betrag(brutto), d["bezahlt_am"] or ""])
    return _csv(zeilen, kopf)


def bmd_buchungen(con: sqlite3.Connection, von: str, bis: str) -> bytes:
    """Tageslosung je Tag, Zahlungsart und Steuersatz (Soll Kassa/Karte an Erlös)."""
    kopf = ["satzart", "konto", "gkonto", "belegnr", "belegdat", "buchsymbol", "buchcode",
            "prozent", "steuercode", "betrag", "steuer", "text"]
    zeilen = []
    tage = con.execute(
        "SELECT DISTINCT substr(zeitpunkt, 1, 10) FROM belege WHERE art IN ('Barumsatz', 'Storno')"
        " AND substr(zeitpunkt, 1, 10) BETWEEN ? AND ? ORDER BY 1", (von, bis)).fetchall()
    for (tag,) in tage:
        # Anteil je Zahlungsart, aufgeteilt nach Steuersätzen der Belege
        verteilung: dict[tuple[str, str], int] = {}
        for b in con.execute("SELECT * FROM belege WHERE art IN ('Barumsatz', 'Storno') AND substr(zeitpunkt, 1, 10) = ?",
                             (tag,)):
            gesamt = sum(b[sp] for sp in SPALTEN.values())
            zahlungen = con.execute("SELECT art, betrag_cent FROM zahlungen WHERE beleg_id = ?", (b["id"],)).fetchall()
            if not zahlungen:
                zahlungen = [(b["zahlungsart"] or "Bar", gesamt)]
            # anteilige Aufteilung je Zahlungsart; Rundungsrest geht an die letzte Zahlung,
            # damit die Summe je Steuersatz exakt stimmt
            for satz, sp in SPALTEN.items():
                if not b[sp]:
                    continue
                rest = b[sp]
                for i, (art, betrag) in enumerate(zahlungen):
                    anteil = rest if i == len(zahlungen) - 1 else (round(b[sp] * betrag / gesamt) if gesamt else 0)
                    rest -= anteil
                    verteilung[(art, satz)] = verteilung.get((art, satz), 0) + anteil
        datum = f"{tag[8:10]}.{tag[5:7]}.{tag[0:4]}"
        for (art, satz), brutto in sorted(verteilung.items()):
            if not brutto:
                continue
            netto = netto_aus_brutto(brutto, satz)
            konto = _konto(con, "konto_kassa" if art == "Bar" else "konto_karte")
            zeilen.append(["0", konto, _konto(con, f"konto_erloes_{satz}"), tag.replace("-", ""), datum, "KA", "1",
                           satz, STEUERCODE.get(satz, "1"), rksv_betrag(brutto), rksv_betrag(-(brutto - netto)),
                           f"Tageslosung {art} {satz}%"])
    return _csv(zeilen, kopf, encoding="cp1252")


def paket(con: sqlite3.Connection, von: str, bis: str, ziel: Path | str) -> Path:
    """ZIP mit allen Exporten für den Steuerberater."""
    from .rksv.dep import dep_export
    import json

    ziel = Path(ziel)
    with zipfile.ZipFile(ziel, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("belege.csv", belege_csv(con, von, bis))
        z.writestr("rechnungen.csv", rechnungen_csv(con, von, bis))
        z.writestr("bmd-buchungen.csv", bmd_buchungen(con, von, bis))
        z.writestr("dep-export.json", json.dumps(dep_export(con), indent=2, ensure_ascii=False))
    return ziel
