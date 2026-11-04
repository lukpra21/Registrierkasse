"""Einmaliger Import aus einer QRK-Sicherung (Firmendaten, Steuersätze, Warengruppen, Artikel).

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
QRK_INTERNE_ARTIKEL = {
    "startbeleg", "kontrollbeleg", "monatsbeleg", "jahresbeleg", "schlussbeleg",
    "nullbeleg", "sammelbeleg", "storno", "stornobeleg", "trainingsbeleg",
}

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
    hinweise: list[str] = field(default_factory=list)

    def text(self) -> str:
        z = [f"Quelle: {self.datenbank}"]
        z.append("Firmendaten: " + (", ".join(f"{k}={v!r}" for k, v in self.firmendaten.items()) or "keine"))
        z.append("Steuersätze: " + (", ".join(f"{s} %" for s in self.steuersaetze) or "keine"))
        z.append(f"Warengruppen: {self.warengruppen}")
        z.append(f"Artikel: {self.artikel} (übersprungen: {self.artikel_uebersprungen})")
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
    # bevorzugt die Datenbank mit einer Tabelle 'products'
    for k in sorted(kandidaten, key=lambda p: -p.stat().st_size):
        with _nur_lesen(k) as con:
            if _tabelle(con, "products"):
                return k
    return kandidaten[0]


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
            for info in z.infolist():
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


def importiere(quelle: Path | str, ziel: sqlite3.Connection, probelauf: bool = False,
               nur_sichtbare: bool = False) -> ImportBericht:
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
        else:
            bericht.hinweise.append("Tabelle 'globals' nicht gefunden – keine Firmendaten")

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
        gruppen: dict[int, str] = {}
        if t := _tabelle(q, "groups"):
            sp = _spalten(q, t)
            c_id, c_name = _spalte(sp, "id"), _spalte(sp, "name")
            if c_id and c_name:
                for r in q.execute(f'SELECT * FROM "{t}"'):
                    if r[c_name] and str(r[c_name]).strip().lower() not in ("auto", ""):
                        gruppen[r[c_id]] = str(r[c_name]).strip()

        # ---- Artikel
        artikel = []
        if t := _tabelle(q, "products"):
            sp = _spalten(q, t)
            c = {
                "name": _spalte(sp, "name"),
                "nr": _spalte(sp, "itemnum", "itemNumber"),
                "barcode": _spalte(sp, "barcode"),
                "brutto": _spalte(sp, "gross"),
                "netto": _spalte(sp, "net"),
                "tax": _spalte(sp, "tax"),
                "gruppe": _spalte(sp, "group", "groupid"),
                "sichtbar": _spalte(sp, "visible"),
                "beschreibung": _spalte(sp, "description"),
            }
            if not c["name"] or not (c["brutto"] or c["netto"]):
                bericht.hinweise.append(f"Spalten in 'products' nicht erkannt: {list(sp.values())}")
            else:
                for r in q.execute(f'SELECT * FROM "{t}"'):
                    name = str(r[c["name"]] or "").strip()
                    sichtbar = int(r[c["sichtbar"]]) if c["sichtbar"] and r[c["sichtbar"]] is not None else 1
                    if not name or name.lower() in QRK_INTERNE_ARTIKEL or (nur_sichtbare and not sichtbar):
                        bericht.artikel_uebersprungen += 1
                        continue
                    steuer = _prozent(r[c["tax"]]) if c["tax"] else None
                    steuer = steuer if steuer is not None else "20"
                    if c["brutto"] and r[c["brutto"]] is not None:
                        brutto = euro_zu_cent(r[c["brutto"]])
                    else:
                        brutto = euro_zu_cent(Decimal(str(r[c["netto"]])) * (100 + Decimal(steuer)) / 100)
                    artikel.append({
                        "nr": str(r[c["nr"]]).strip() if c["nr"] and r[c["nr"]] not in (None, "") else None,
                        "barcode": str(r[c["barcode"]]).strip() if c["barcode"] and r[c["barcode"]] else None,
                        "name": name,
                        "gruppe": gruppen.get(r[c["gruppe"]]) if c["gruppe"] else None,
                        "brutto": brutto,
                        "steuer": steuer,
                        "sichtbar": sichtbar,
                        "beschreibung": r[c["beschreibung"]] if c["beschreibung"] else None,
                    })
                    if steuer not in bericht.steuersaetze:
                        bericht.steuersaetze.append(steuer)
        else:
            bericht.hinweise.append("Tabelle 'products' nicht gefunden – keine Artikel")

        bericht.warengruppen = len(set(gruppen.values()))
        bericht.artikel = len(artikel)

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
            ziel.execute(
                "INSERT INTO artikel (artikelnummer, barcode, name, warengruppe_id, brutto_cent, steuer_prozent,"
                " sichtbar, beschreibung, herkunft) VALUES (?,?,?,?,?,?,?,?, 'qrk-import')"
                " ON CONFLICT(artikelnummer) DO UPDATE SET name=excluded.name, barcode=excluded.barcode,"
                " warengruppe_id=excluded.warengruppe_id, brutto_cent=excluded.brutto_cent,"
                " steuer_prozent=excluded.steuer_prozent, sichtbar=excluded.sichtbar",
                (a["nr"], a["barcode"], a["name"], gid.get(a["gruppe"]), a["brutto"], a["steuer"],
                 a["sichtbar"], a["beschreibung"]),
            )
    return bericht
