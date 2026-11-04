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
    "konto_gutschein": "3480",  # Verbindlichkeit aus ausgegebenen Gutscheinen
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
    kopf = ["Rechnungsnummer", "Datum", "Kunde", "UID Kunde", "Zahlungsart", "Netto", "USt", "Brutto", "Bezahlt am",
            "Storniert am"]
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
                       rksv_betrag(netto), rksv_betrag(brutto - netto), rksv_betrag(brutto), d["bezahlt_am"] or "",
                       d["storniert_am"] or ""])
    return _csv(zeilen, kopf)


def _ist_gutschein(bezeichnung: str) -> str | None:
    """'verkauf' bzw. 'einloesung' für Gutscheinpositionen, sonst None."""
    if bezeichnung.startswith("Wertgutschein "):
        return "verkauf"
    if bezeichnung.startswith("Gutschein ") and bezeichnung.endswith(" eingelöst"):
        return "einloesung"
    return None


def _aufteilen(betrag: int, schluessel: list[tuple[str, int]]) -> list[tuple[str, int]]:
    """Teilt ``betrag`` anteilig nach den Gewichten auf; Rundungsrest an den letzten Anteil."""
    gesamt = sum(g for _, g in schluessel)
    res, rest = [], betrag
    for i, (k, g) in enumerate(schluessel):
        anteil = rest if i == len(schluessel) - 1 else (round(betrag * g / gesamt) if gesamt else 0)
        rest -= anteil
        res.append((k, anteil))
    return res


def bmd_buchungen(con: sqlite3.Connection, von: str, bis: str) -> bytes:
    """Tageslosung je Tag, Zahlungs- und Erlöskonto (Soll Kassa/Karte/Gutschein an Erlös/Gutschein).

    Gutscheine: Verkauf = Verbindlichkeit (Konto ``konto_gutschein``, keine USt);
    Einlösung = Soll ``konto_gutschein`` an Erlös mit dem Steuersatz der Ware.
    """
    kopf = ["satzart", "konto", "gkonto", "belegnr", "belegdat", "buchsymbol", "buchcode",
            "prozent", "steuercode", "betrag", "steuer", "text"]
    zahl_konto = {"Bar": _konto(con, "konto_kassa"), "Karte": _konto(con, "konto_karte"),
                  "Gutschein": _konto(con, "konto_gutschein")}
    zeilen = []
    tage = con.execute(
        "SELECT DISTINCT substr(zeitpunkt, 1, 10) FROM belege WHERE art IN ('Barumsatz', 'Storno')"
        " AND substr(zeitpunkt, 1, 10) BETWEEN ? AND ? ORDER BY 1", (von, bis)).fetchall()
    for (tag,) in tage:
        # (Zahlungsart, Gegenkonto-Schlüssel, Steuersatz) -> Betrag
        verteilung: dict[tuple[str, str, str], int] = {}
        for b in con.execute("SELECT * FROM belege WHERE art IN ('Barumsatz', 'Storno') AND substr(zeitpunkt, 1, 10) = ?",
                             (tag,)):
            haben: dict[tuple[str, str], int] = {}  # (Gegenkonto-Schlüssel, Satz) -> Betrag
            gutschein_zahlung = 0
            for p in con.execute("SELECT * FROM belegpositionen WHERE beleg_id = ?", (b["id"],)):
                art = _ist_gutschein(p["bezeichnung"])
                if art == "einloesung":
                    gutschein_zahlung -= p["summe_cent"]  # Position ist negativ
                    continue
                schl = ("konto_gutschein", "0") if art == "verkauf" else (f"konto_erloes_{p['steuer_prozent']}", p["steuer_prozent"])
                haben[schl] = haben.get(schl, 0) + p["summe_cent"]
            zahlungen = [(z["art"], z["betrag_cent"]) for z in
                         con.execute("SELECT art, betrag_cent FROM zahlungen WHERE beleg_id = ?", (b["id"],))]
            if gutschein_zahlung:
                zahlungen.append(("Gutschein", gutschein_zahlung))
            if not zahlungen:
                zahlungen = [(b["zahlungsart"] if b["zahlungsart"] in zahl_konto else "Bar", sum(haben.values()))]
            for (schl, satz), betrag in haben.items():
                for art, anteil in _aufteilen(betrag, zahlungen):
                    k = (art, schl, satz)
                    verteilung[k] = verteilung.get(k, 0) + anteil
        datum = f"{tag[8:10]}.{tag[5:7]}.{tag[0:4]}"
        for (art, schl, satz), brutto in sorted(verteilung.items()):
            if not brutto:
                continue
            gutschein = schl == "konto_gutschein"
            netto = brutto if gutschein else netto_aus_brutto(brutto, satz)
            text = f"Gutscheinverkauf {art}" if gutschein else f"Tageslosung {art} {satz}%"
            zeilen.append(["0", zahl_konto.get(art, zahl_konto["Bar"]), _konto(con, schl), tag.replace("-", ""), datum,
                           "KA", "1", "0" if gutschein else satz, "0" if gutschein else STEUERCODE.get(satz, "1"),
                           rksv_betrag(brutto), rksv_betrag(-(brutto - netto)), text])
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
