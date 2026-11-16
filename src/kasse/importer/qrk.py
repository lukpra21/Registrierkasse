"""Einmaliger Import aus einer QRK-Sicherung (Firmendaten, Steuersätze, Warengruppen, Artikel, Verkäufe).

Verkäufe landen als *Altbelege* in einer eigenen Tabelle – nur für Statistik und
Nachschlagen. Sie sind NICHT Teil der RKSV-Belegkette dieser Kasse; das DEP der
alten Kasse bleibt die QRK-Sicherung bzw. deren DEP-7-Export.

Die QRK-Sicherung wird NUR LESEND geöffnet. Unterstützt werden:
- ein Verzeichnis (z. B. entpackte Sicherung ``qrk_20261028-1``),
- eine ZIP-Datei,
- direkt eine SQLite-Datenbankdatei.

Die Spaltennamen werden tolerant ermittelt, da sich das QRK-Schema zwischen
Versionen unterscheidet. Mit ``inspiziere()`` lässt sich das Schema (ohne Daten)
ausgeben, falls etwas nicht erkannt wird.

Übernommene Daten landen ausschließlich in der lokalen Kassendatenbank des
Benutzers – nie im Programm bzw. Repository.
"""

from __future__ import annotations

import base64
import re
import sqlite3
import tempfile
import zipfile
from contextlib import contextmanager
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from pathlib import Path

from ..db import setze_einstellung
from ..geld import euro_zu_cent

# QRK legt für Sonderbelege interne "Artikel" an – diese nicht übernehmen
QRK_INTERNE_ARTIKEL = (
    "startbeleg", "kontrollbeleg", "kontroll null beleg", "monatsbeleg", "jahresbeleg", "schlussbeleg",
    "nullbeleg", "sammelbeleg", "storno", "trainingsbeleg", "zahlungsbeleg für rechnung",
)

# QRK payedBy -> eigene Zahlungsart (nur Umsatzbelege; 4–11 sind Abschlüsse/Sonderbelege)
QRK_ZAHLUNGSARTEN = {0: "Bar", 1: "Karte", 2: "Karte", 3: "Gutschein"}


def _intern(name: str) -> bool:
    return name.lower().startswith(QRK_INTERNE_ARTIKEL)

# QRK globals -> eigene Einstellungen
FIRMEN_SCHLUESSEL = {
    "shopname": "firma_name",
    "shopowner": "firma_inhaber",
    "shopaddress": "firma_adresse",
    "shopuid": "firma_uid",
    "shopcashregisterid": "qrk_kassen_id",
}


@dataclass
class ImportBericht:
    datenbank: str = ""
    firmendaten: dict[str, str] = field(default_factory=dict)
    steuersaetze: list[str] = field(default_factory=list)
    warengruppen: int = 0
    artikel: int = 0
    artikel_uebersprungen: int = 0
    artikel_zusammengefasst: int = 0
    altbelege: int = 0
    altbelege_storno: int = 0
    altbelege_umsatz_cent: int = 0
    altbelege_zeitraum: str = ""
    positionen_ohne_artikel: int = 0
    kassen_id: str = ""
    hinweise: list[str] = field(default_factory=list)

    def text(self) -> str:
        z = [f"Quelle: {self.datenbank}"]
        z.append("Firmendaten: " + (", ".join(f"{k}={v!r}" for k, v in self.firmendaten.items()) or "keine"))
        z.append("Steuersätze: " + (", ".join(f"{s} %" for s in self.steuersaetze) or "keine"))
        z.append(f"Warengruppen: {self.warengruppen}")
        z.append(f"Artikel: {self.artikel} (übersprungen: {self.artikel_uebersprungen},"
                 f" Doppelte zusammengefasst: {self.artikel_zusammengefasst})")
        if self.altbelege:
            umsatz = f"{self.altbelege_umsatz_cent / 100:,.2f}".replace(",", " ").replace(".", ",").replace(" ", ".")
            z.append(f"Verkäufe (Altbelege, Kasse {self.kassen_id or '?'}): {self.altbelege} Belege,"
                     f" davon {self.altbelege_storno} Storno, {self.altbelege_zeitraum}, Umsatz {umsatz} €")
            if self.positionen_ohne_artikel:
                z.append(f"Positionen zu gelöschten QRK-Artikeln (nur Bezeichnung): {self.positionen_ohne_artikel}")
        z += [f"Hinweis: {h}" for h in self.hinweise]
        return "\n".join(z)


def _ist_sqlite(pfad: Path) -> bool:
    try:
        with open(pfad, "rb") as f:
            return f.read(16) == b"SQLite format 3\x00"
    except OSError:
        return False


def _finde_db(verzeichnis: Path) -> Path:
    kandidaten = [p for p in verzeichnis.rglob("*") if p.is_file() and _ist_sqlite(p)]
    if not kandidaten:
        raise FileNotFoundError(f"Keine SQLite-Datenbank in {verzeichnis} gefunden")
    # QRK legt je Jahr eine (kumulative) Datenbank an: die mit dem jüngsten Beleg nehmen
    def rang(k: Path):
        with _nur_lesen(k) as con:
            if not _tabelle(con, "products"):
                return (0, "", 0)
            letzter = ""
            if t := _tabelle(con, "receipts"):
                sp = _spalten(con, t)
                if c := _spalte(sp, "timestamp"):
                    letzter = con.execute(f'SELECT MAX("{c}") FROM "{t}"').fetchone()[0] or ""
            return (1, str(letzter), k.stat().st_size)
    return max(kandidaten, key=rang)


_DB_ENDUNGEN = (".db", ".db-wal", ".db-shm", ".sqlite", ".sqlite3")


@contextmanager
def _nur_lesen(pfad: Path):
    con = sqlite3.connect(f"{pfad.resolve().as_uri()}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    try:
        yield con
    finally:
        con.close()


@contextmanager
def qrk_datenbank(quelle: Path | str):
    quelle = Path(quelle)
    if quelle.is_dir():
        db = _finde_db(quelle)
        with _nur_lesen(db) as con:
            yield db, con
    elif zipfile.is_zipfile(quelle):
        with tempfile.TemporaryDirectory() as tmp, zipfile.ZipFile(quelle) as z:
            infos = [i for i in z.infolist() if i.filename.lower().endswith(_DB_ENDUNGEN)] or z.infolist()
            for info in infos:
                ziel = (Path(tmp) / info.filename).resolve()
                if not str(ziel).startswith(str(Path(tmp).resolve())):
                    continue  # Schutz vor Pfad-Traversal
                z.extract(info, tmp)
            db = _finde_db(Path(tmp))
            with _nur_lesen(db) as con:
                yield db, con
    elif _ist_sqlite(quelle):
        with _nur_lesen(quelle) as con:
            yield quelle, con
    else:
        raise ValueError(f"{quelle} ist weder Verzeichnis, ZIP noch SQLite-Datenbank")


def _tabelle(con: sqlite3.Connection, name: str) -> str | None:
    row = con.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND lower(name) = lower(?)", (name,)
    ).fetchone()
    return row[0] if row else None


def _spalten(con: sqlite3.Connection, tabelle: str) -> dict[str, str]:
    return {r[1].lower(): r[1] for r in con.execute(f'PRAGMA table_info("{tabelle}")')}


def _spalte(spalten: dict[str, str], *namen: str) -> str | None:
    for n in namen:
        if n.lower() in spalten:
            return spalten[n.lower()]
    return None


def inspiziere(quelle: Path | str) -> str:
    """Schema der QRK-Datenbank (Tabellen, Spalten, Zeilenanzahl) – ohne Inhalte."""
    with qrk_datenbank(quelle) as (db, con):
        z = [f"Datenbank: {db}"]
        for (name,) in con.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"):
            anzahl = con.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0]
            z.append(f"{name} ({anzahl} Zeilen): {', '.join(_spalten(con, name).values())}")
        return "\n".join(z)


def _prozent(wert) -> str | None:
    try:
        d = Decimal(str(wert).replace(",", "."))
    except (InvalidOperation, TypeError):
        return None
    return format(d.normalize(), "f")


def _dezimal(wert) -> Decimal:
    try:
        return Decimal(str(wert if wert not in (None, "") else 0))
    except InvalidOperation:
        return Decimal(0)


def _menge_text(d: Decimal) -> str:
    return format(d.normalize(), "f")


def _namensschluessel(name: str) -> str:
    return re.sub(r"[\s*]+", " ", name).strip().lower()


def _kassen_id_aus_dep(q: sqlite3.Connection) -> str | None:
    """Kassen-ID der alten Kasse aus dem ersten DEP-Eintrag (JWS-Payload ``_R1-AT1_<Kassen-ID>_…``)."""
    t = _tabelle(q, "dep")
    if not t:
        return None
    c = _spalte(_spalten(q, t), "data")
    if not c:
        return None
    row = q.execute(f'SELECT "{c}" FROM "{t}" ORDER BY rowid LIMIT 1').fetchone()
    try:
        teil = str(row[0]).split(".")[1]
        payload = base64.urlsafe_b64decode(teil + "=" * (-len(teil) % 4)).decode()
        return payload.split("_")[2] or None
    except Exception:  # noqa: BLE001 - nur Komfort
        return None


# Zeile im QRK-Tagesabschluss: "Menge: Bezeichnung: Einzelpreis: Summe: Steuer%"
_BERICHT_ZEILE = re.compile(r"^\s*([\d.,-]+):\s*(.+?):\s*([\d.,-]+):\s*([\d.,-]+):\s*([\d.,]+)%\s*$")


def _zahl_bericht(t: str) -> Decimal | None:
    try:
        return Decimal(t.replace(".", "").replace(",", "."))
    except InvalidOperation:
        return None


def _namen_aus_berichten(q: sqlite3.Connection, gesucht: list[tuple]) -> dict:
    """Bezeichnungen gelöschter QRK-Artikel aus den Tagesabschluss-Texten rekonstruieren.

    ``gesucht``: (QRK-Produkt-ID, Belegdatum, Einzelpreis brutto, Steuersatz). Je Produkt-ID gewinnt die
    Bezeichnung, die am häufigsten mit gleichem Preis und Steuersatz im Tagesabschluss dieses Tages steht.
    """
    if not gesucht or not _tabelle(q, "reports") or not _tabelle(q, "receipts"):
        return {}
    tage = {g[1] for g in gesucht}
    nummern: dict[int, str] = {}
    for r in q.execute("SELECT receiptNum, substr(infodate, 1, 10) AS tag FROM receipts WHERE payedBy = 4"):
        if r["tag"] in tage:
            nummern[int(r["receiptNum"])] = r["tag"]
    zeilen: dict[str, list[tuple]] = {}
    if nummern:
        for r in q.execute("SELECT receiptNum, text FROM reports WHERE receiptNum IN (%s)"
                           % ",".join(str(n) for n in nummern)):
            m = _BERICHT_ZEILE.match(str(r["text"] or ""))
            if not m:
                continue
            preis, satz = _zahl_bericht(m.group(3)), _zahl_bericht(m.group(5))
            if preis is not None and satz is not None:
                zeilen.setdefault(nummern[int(r["receiptNum"])], []).append((m.group(2).strip(), preis, satz))
    stimmen: dict = {}
    for pid, tag, preis, satz in gesucht:
        for name, p, s in zeilen.get(tag, []):
            if p == preis and s == satz:
                stimmen.setdefault(pid, {}).setdefault(name, 0)
                stimmen[pid][name] += 1
    return {pid: max(st, key=st.get) for pid, st in stimmen.items()}


def importiere(quelle: Path | str, ziel: sqlite3.Connection, probelauf: bool = False,
               nur_sichtbare: bool = False, verkaeufe: bool = False) -> ImportBericht:
    bericht = ImportBericht()
    with qrk_datenbank(quelle) as (db, q):
        bericht.datenbank = str(db)

        # ---- Firmendaten
        if t := _tabelle(q, "globals"):
            sp = _spalten(q, t)
            c_name = _spalte(sp, "name")
            c_str = _spalte(sp, "strValue", "strvalue")
            c_val = _spalte(sp, "value")
            if c_name:
                for r in q.execute(f'SELECT * FROM "{t}"'):
                    key = str(r[c_name] or "").lower()
                    if key in FIRMEN_SCHLUESSEL:
                        wert = (r[c_str] if c_str else None) or (r[c_val] if c_val else None)
                        if wert not in (None, ""):
                            bericht.firmendaten[FIRMEN_SCHLUESSEL[key]] = str(wert)
            if not bericht.firmendaten:
                bericht.hinweise.append("Firmendaten in QRK nicht lesbar (neuere QRK-Versionen verschlüsseln sie)"
                                        " – bitte in den Einstellungen eintragen")
        else:
            bericht.hinweise.append("Tabelle 'globals' nicht gefunden – keine Firmendaten")
        if "qrk_kassen_id" not in bericht.firmendaten and (kid := _kassen_id_aus_dep(q)):
            bericht.firmendaten["qrk_kassen_id"] = kid
        bericht.kassen_id = bericht.firmendaten.get("qrk_kassen_id", "")

        # ---- Steuersätze
        if t := _tabelle(q, "taxTypes"):
            sp = _spalten(q, t)
            c_tax = _spalte(sp, "tax")
            c_loc = _spalte(sp, "taxlocation")
            for r in q.execute(f'SELECT * FROM "{t}"'):
                if c_loc and r[c_loc] and str(r[c_loc]).upper() != "AT":
                    continue
                p = _prozent(r[c_tax]) if c_tax else None
                if p is not None and p not in bericht.steuersaetze:
                    bericht.steuersaetze.append(p)

        # ---- Warengruppen
        gruppen: dict = {}
        if t := _tabelle(q, "groups"):
            sp = _spalten(q, t)
            c_id, c_name = _spalte(sp, "id"), _spalte(sp, "name")
            if c_id and c_name:
                for r in q.execute(f'SELECT * FROM "{t}"'):
                    if r[c_name] and str(r[c_name]).strip().lower() not in ("auto", ""):
                        gruppen[r[c_id]] = str(r[c_name]).strip()

        # ---- Gewichtsartikel erkennen (je verkauft mit Kommamenge)
        t_orders = _tabelle(q, "orders")
        gewicht: set = set()
        if t_orders:
            gewicht = {r[0] for r in q.execute(
                f'SELECT DISTINCT product FROM "{t_orders}" WHERE count <> CAST(count AS INTEGER)')}

        # ---- Artikel
        artikel: list[dict] = []
        qrk_namen: dict = {}       # QRK-Produkt-ID -> Name (auch interne/übersprungene)
        qrk_zu_artikel: dict = {}  # QRK-Produkt-ID -> Index in ``artikel``
        if t := _tabelle(q, "products"):
            sp = _spalten(q, t)
            c = {
                "id": _spalte(sp, "id"),
                "name": _spalte(sp, "name"),
                "nr": _spalte(sp, "itemnum", "itemNumber"),
                "barcode": _spalte(sp, "barcode"),
                "brutto": _spalte(sp, "gross"),
                "netto": _spalte(sp, "net"),
                "tax": _spalte(sp, "tax"),
                "gruppe": _spalte(sp, "group", "groupid"),
                "sichtbar": _spalte(sp, "visible"),
                "beschreibung": _spalte(sp, "description"),
                "geaendert": _spalte(sp, "lastchange"),
            }
            if not c["name"] or not (c["brutto"] or c["netto"]):
                bericht.hinweise.append(f"Spalten in 'products' nicht erkannt: {list(sp.values())}")
            else:
                kandidaten = []
                for r in q.execute(f'SELECT * FROM "{t}"'):
                    name = str(r[c["name"]] or "").strip()
                    if c["id"]:
                        qrk_namen[r[c["id"]]] = name
                    sichtbar = int(r[c["sichtbar"]]) if c["sichtbar"] and r[c["sichtbar"]] is not None else 1
                    if not name or _intern(name) or (nur_sichtbare and not sichtbar):
                        bericht.artikel_uebersprungen += 1
                        continue
                    kandidaten.append((r, name, sichtbar))
                # bevorzugt: sichtbar, zuletzt geändert, jüngste ID – die übrigen gleichnamigen werden zusammengefasst
                kandidaten.sort(key=lambda k: (k[2], str(k[0][c["geaendert"]] or "") if c["geaendert"] else "",
                                               k[0][c["id"]] if c["id"] else 0), reverse=True)
                nummern: dict[str, int] = {}
                for r, name, sichtbar in kandidaten:
                    nr = str(r[c["nr"]]).strip() if c["nr"] and r[c["nr"]] not in (None, "") else None
                    qid = r[c["id"]] if c["id"] else None
                    if nr and nr in nummern:
                        bisher = artikel[nummern[nr]]
                        if _namensschluessel(bisher["name"]) == _namensschluessel(name):
                            qrk_zu_artikel[qid] = nummern[nr]  # ältere Version desselben Artikels
                            bericht.artikel_zusammengefasst += 1
                            continue
                        bericht.hinweise.append(f"Artikelnummer {nr} doppelt ({bisher['name']} / {name})"
                                                f" – {name} ohne Nummer übernommen")
                        nr = None
                    steuer = _prozent(r[c["tax"]]) if c["tax"] else None
                    steuer = steuer if steuer is not None else "20"
                    if c["brutto"] and r[c["brutto"]] is not None:
                        brutto = euro_zu_cent(r[c["brutto"]])
                    else:
                        brutto = euro_zu_cent(Decimal(str(r[c["netto"]])) * (100 + Decimal(steuer)) / 100)
                    if nr:
                        nummern[nr] = len(artikel)
                    if qid is not None:
                        qrk_zu_artikel[qid] = len(artikel)
                    artikel.append({
                        "qrk_id": qid,
                        "nr": nr,
                        "barcode": str(r[c["barcode"]]).strip() if c["barcode"] and r[c["barcode"]] else None,
                        "name": name,
                        "gruppe": gruppen.get(r[c["gruppe"]]) if c["gruppe"] else None,
                        "brutto": brutto,
                        "steuer": steuer,
                        "sichtbar": sichtbar,
                        "einheit": "Stk",
                        "beschreibung": r[c["beschreibung"]] if c["beschreibung"] else None,
                    })
                    if steuer not in bericht.steuersaetze:
                        bericht.steuersaetze.append(steuer)
                for qid, idx in qrk_zu_artikel.items():
                    if qid in gewicht:
                        artikel[idx]["einheit"] = "kg"
        else:
            bericht.hinweise.append("Tabelle 'products' nicht gefunden – keine Artikel")

        bericht.warengruppen = len(set(gruppen.values()))
        bericht.artikel = len(artikel)

        # ---- Verkäufe (Altbelege)
        altbelege: list[dict] = []
        if verkaeufe:
            t_rec = _tabelle(q, "receipts")
            if not (t_rec and t_orders):
                bericht.hinweise.append("Tabellen 'receipts'/'orders' fehlen – keine Verkäufe übernommen")
            else:
                c_rabatt = _spalte(_spalten(q, t_orders), "discount")
                pos_je_beleg: dict = {}
                for o in q.execute(f'SELECT * FROM "{t_orders}" ORDER BY id'):
                    pos_je_beleg.setdefault(o["receiptId"], []).append(o)
                fehlend = []
                for r in q.execute(f'SELECT * FROM "{t_rec}" WHERE payedBy IN (0, 1, 2, 3) ORDER BY receiptNum'):
                    tag = str(r["timestamp"])[:10]
                    pos = []
                    for o in pos_je_beleg.get(r["receiptNum"], []):
                        menge, preis = _dezimal(o["count"]), _dezimal(o["gross"])
                        summe = menge * preis
                        rabatt = _dezimal(o[c_rabatt]) if c_rabatt else Decimal(0)
                        if rabatt:
                            summe = summe * (100 - rabatt) / 100
                        steuer = _prozent(o["tax"]) or "0"
                        pos.append({"qrk_id": o["product"], "menge": menge, "preis": euro_zu_cent(preis),
                                    "summe": euro_zu_cent(summe), "steuer": steuer})
                        if o["product"] not in qrk_namen:
                            fehlend.append((o["product"], tag, preis, _dezimal(steuer)))
                    storno = int(r["storno"] or 0)
                    altbelege.append({
                        "nr": int(r["receiptNum"]),
                        "zeit": str(r["timestamp"]).replace(" ", "T")[:19],
                        "art": "Storno" if storno == 2 else "Barumsatz",
                        "zahlung": QRK_ZAHLUNGSARTEN.get(int(r["payedBy"]), "Bar"),
                        "summe": euro_zu_cent(_dezimal(r["gross"])),
                        "storniert": 1 if storno == 1 else 0,
                        "pos": pos,
                    })
                rekonstruiert = _namen_aus_berichten(q, fehlend)
                for b in altbelege:
                    for p_ in b["pos"]:
                        qid = p_["qrk_id"]
                        p_["idx"] = qrk_zu_artikel.get(qid)
                        if p_["idx"] is not None:
                            p_["name"] = artikel[p_["idx"]]["name"]
                        else:
                            p_["name"] = qrk_namen.get(qid) or rekonstruiert.get(qid) or f"QRK-Artikel {qid}"
                            bericht.positionen_ohne_artikel += 1
                bericht.altbelege = len(altbelege)
                bericht.altbelege_storno = sum(1 for b in altbelege if b["art"] == "Storno")
                bericht.altbelege_umsatz_cent = sum(b["summe"] for b in altbelege)
                if altbelege:
                    bericht.altbelege_zeitraum = f"{altbelege[0]['zeit'][:10]} bis {altbelege[-1]['zeit'][:10]}"

    if probelauf:
        return bericht

    # ---- Schreiben (eine Transaktion)
    with ziel:
        for k, v in bericht.firmendaten.items():
            setze_einstellung(ziel, k, v)
        bekannt = {r[0] for r in ziel.execute("SELECT prozent FROM steuersaetze")}
        for p in bericht.steuersaetze:
            if p not in bekannt:
                bericht.hinweise.append(f"Steuersatz {p} % unbekannt – bitte RKSV-Satz zuordnen")
                ziel.execute("INSERT INTO steuersaetze (prozent, rksv_satz, bezeichnung) VALUES (?, 'Besonders', ?)",
                             (p, f"Import {p} %"))
        for name in sorted(set(gruppen.values())):
            ziel.execute("INSERT OR IGNORE INTO warengruppen (name) VALUES (?)", (name,))
        gid = {r["name"]: r["id"] for r in ziel.execute("SELECT id, name FROM warengruppen")}
        for a in artikel:
            herkunft = f"qrk:{a['qrk_id']}" if a["qrk_id"] is not None else "qrk-import"
            vorhanden = None
            if a["qrk_id"] is not None:
                vorhanden = ziel.execute("SELECT id FROM artikel WHERE herkunft = ?", (herkunft,)).fetchone()
            if not vorhanden and a["nr"]:
                vorhanden = ziel.execute("SELECT id FROM artikel WHERE artikelnummer = ?", (a["nr"],)).fetchone()
            werte = (a["nr"], a["barcode"], a["name"], gid.get(a["gruppe"]), a["brutto"], a["steuer"],
                     a["einheit"], a["sichtbar"], a["beschreibung"], herkunft)
            if vorhanden:
                ziel.execute("UPDATE artikel SET artikelnummer=?, barcode=?, name=?, warengruppe_id=?, brutto_cent=?,"
                             " steuer_prozent=?, einheit=?, sichtbar=?, beschreibung=COALESCE(?, beschreibung),"
                             " herkunft=? WHERE id=?", (*werte, vorhanden[0]))
                a["artikel_id"] = vorhanden[0]
            else:
                a["artikel_id"] = ziel.execute(
                    "INSERT INTO artikel (artikelnummer, barcode, name, warengruppe_id, brutto_cent, steuer_prozent,"
                    " einheit, sichtbar, beschreibung, herkunft) VALUES (?,?,?,?,?,?,?,?,?,?)", werte).lastrowid
        if altbelege:
            kid = bericht.kassen_id or None
            # erneuter Import ersetzt die Altbelege derselben alten Kasse vollständig
            ziel.execute("DELETE FROM altbelegpositionen WHERE altbeleg_id IN"
                         " (SELECT id FROM altbelege WHERE quelle = 'QRK' AND kassen_id IS ?)", (kid,))
            ziel.execute("DELETE FROM altbelege WHERE quelle = 'QRK' AND kassen_id IS ?", (kid,))
            for b in altbelege:
                bid = ziel.execute(
                    "INSERT INTO altbelege (quelle, kassen_id, belegnummer, zeitpunkt, art, zahlungsart, summe_cent,"
                    " storniert) VALUES ('QRK',?,?,?,?,?,?,?)",
                    (kid, b["nr"], b["zeit"], b["art"], b["zahlung"], b["summe"], b["storniert"])).lastrowid
                ziel.executemany(
                    "INSERT INTO altbelegpositionen (altbeleg_id, pos, artikel_id, bezeichnung, menge, einzelpreis_cent,"
                    " steuer_prozent, summe_cent) VALUES (?,?,?,?,?,?,?,?)",
                    [(bid, i, artikel[p_["idx"]]["artikel_id"] if p_["idx"] is not None else None,
                      p_["name"], _menge_text(p_["menge"]), p_["preis"], p_["steuer"], p_["summe"])
                     for i, p_ in enumerate(b["pos"], start=1)])
    return bericht
