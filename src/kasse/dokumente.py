"""Lieferscheine und Rechnungen (A4) für Geschäftskunden.

Rechnungen, die bar oder mit Karte bezahlt werden, sind Barumsätze und
werden zusätzlich als RKSV-Beleg signiert. Rechnungen auf Überweisung
laufen nur über den eigenen Rechnungsnummernkreis.
"""

from __future__ import annotations

import datetime as dt
import sqlite3
from dataclasses import dataclass
from decimal import Decimal

from .rksv.kasse import Kasse, KassenFehler, Position

BARZAHLUNGEN = ("Bar", "Karte", "Bankomat")
PRAEFIX = {"Lieferschein": "LS", "Rechnung": "RE"}


@dataclass
class DokPosition:
    bezeichnung: str
    menge: Decimal
    einzelpreis_cent: int  # brutto
    steuer_prozent: str
    einheit: str = "Stk"
    artikel_id: int | None = None


def _naechste_nummer(con: sqlite3.Connection, typ: str, datum: dt.date) -> str:
    praefix = f"{PRAEFIX[typ]}-{datum.year}-"
    row = con.execute(
        "SELECT nummer FROM dokumente WHERE typ = ? AND nummer LIKE ? ORDER BY nummer DESC LIMIT 1",
        (typ, praefix + "%"),
    ).fetchone()
    lfd = int(row[0].rsplit("-", 1)[1]) + 1 if row else 1
    return f"{praefix}{lfd:05d}"


def _anlegen(con, typ, kunde_id, positionen, zahlungsart=None, bezug_id=None, beleg_id=None, datum=None) -> int:
    datum = datum or dt.date.today()
    cur = con.execute(
        "INSERT INTO dokumente (typ, nummer, datum, kunde_id, zahlungsart, beleg_id, bezug_id) VALUES (?,?,?,?,?,?,?)",
        (typ, _naechste_nummer(con, typ, datum), datum.isoformat(), kunde_id, zahlungsart, beleg_id, bezug_id),
    )
    dok_id = cur.lastrowid
    for i, p in enumerate(positionen, start=1):
        con.execute(
            "INSERT INTO dokumentpositionen VALUES (?,?,?,?,?,?,?,?)",
            (dok_id, i, p.artikel_id, p.bezeichnung, str(p.menge), p.einheit, p.einzelpreis_cent, p.steuer_prozent),
        )
    con.commit()
    return dok_id


def lieferschein(con: sqlite3.Connection, kunde_id: int, positionen: list[DokPosition]) -> int:
    return _anlegen(con, "Lieferschein", kunde_id, positionen)


def positionen(con: sqlite3.Connection, dok_id: int) -> list[DokPosition]:
    return [
        DokPosition(r["bezeichnung"], Decimal(r["menge"]), r["einzelpreis_cent"], r["steuer_prozent"], r["einheit"], r["artikel_id"])
        for r in con.execute("SELECT * FROM dokumentpositionen WHERE dokument_id = ? ORDER BY pos", (dok_id,))
    ]


def rechnung(
    con: sqlite3.Connection,
    kunde_id: int,
    pos: list[DokPosition],
    zahlungsart: str = "Überweisung",
    kasse: Kasse | None = None,
    bezug_id: int | None = None,
) -> int:
    beleg_id = None
    if zahlungsart in BARZAHLUNGEN:
        if kasse is None:
            raise KassenFehler("Barzahlung erfordert einen RKSV-Beleg – Kasse übergeben")
        beleg_id = kasse.verkauf(
            [Position(p.bezeichnung, p.menge, p.einzelpreis_cent, p.steuer_prozent, p.artikel_id) for p in pos],
            zahlungsart=zahlungsart,
            kunde_id=kunde_id,
        )
    return _anlegen(con, "Rechnung", kunde_id, pos, zahlungsart, bezug_id, beleg_id)


def rechnung_aus_lieferscheinen(
    con: sqlite3.Connection, lieferschein_ids: list[int], zahlungsart: str = "Überweisung", kasse: Kasse | None = None
) -> int:
    kunden = {con.execute("SELECT kunde_id FROM dokumente WHERE id = ? AND typ = 'Lieferschein'", (i,)).fetchone()[0]
              for i in lieferschein_ids}
    if len(kunden) != 1:
        raise KassenFehler("Sammelrechnung nur für Lieferscheine desselben Kunden")
    marks = ",".join("?" * len(lieferschein_ids))
    if con.execute(f"SELECT 1 FROM dokument_bezug WHERE lieferschein_id IN ({marks})", lieferschein_ids).fetchone():
        raise KassenFehler("Mindestens ein Lieferschein wurde bereits verrechnet")
    alle: list[DokPosition] = []
    for i in lieferschein_ids:
        nr = con.execute("SELECT nummer, datum FROM dokumente WHERE id = ?", (i,)).fetchone()
        for p in positionen(con, i):
            p.bezeichnung = f"{p.bezeichnung} (LS {nr['nummer']} vom {nr['datum']})" if len(lieferschein_ids) > 1 else p.bezeichnung
            alle.append(p)
    re_id = rechnung(con, kunden.pop(), alle, zahlungsart, kasse, bezug_id=lieferschein_ids[0])
    con.executemany("INSERT INTO dokument_bezug VALUES (?, ?)", [(re_id, i) for i in lieferschein_ids])
    con.commit()
    return re_id
