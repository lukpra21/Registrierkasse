"""Kassenbuch: Kassastand, Einlagen/Entnahmen und Zählprotokoll (Kassasturz).

Kassastand = letzter Anfangsbestand
           + Einlagen − Entnahmen ± Differenzbuchungen
           + Barzahlungen aus Belegen (inkl. Stornos)
jeweils ab dem Zeitpunkt des letzten Anfangsbestands.
"""

from __future__ import annotations

import datetime as dt
import json
import sqlite3

from .rksv.kasse import KassenFehler

ARTEN = ("Anfangsbestand", "Einlage", "Entnahme", "Differenz")

#: Stückelung in Cent für das Zählprotokoll
STUECKELUNG = [50000, 20000, 10000, 5000, 2000, 1000, 500, 200, 100, 50, 20, 10, 5, 2, 1]


def _jetzt() -> str:
    return dt.datetime.now().isoformat(timespec="seconds")


def buchen(con: sqlite3.Connection, art: str, betrag_cent: int, text: str = "", benutzer_id: int | None = None) -> int:
    if art not in ARTEN:
        raise KassenFehler(f"Unbekannte Kassenbuch-Art: {art}")
    if art in ("Einlage", "Entnahme", "Anfangsbestand") and betrag_cent < 0:
        raise KassenFehler("Betrag darf nicht negativ sein")
    if art == "Entnahme" and betrag_cent > kassastand(con):
        raise KassenFehler("Entnahme höher als der Kassastand")
    bid = con.execute("INSERT INTO kassenbuch (zeitpunkt, art, betrag_cent, text, benutzer_id) VALUES (?,?,?,?,?)",
                      (_jetzt(), art, betrag_cent, text, benutzer_id)).lastrowid
    con.commit()
    return bid


def _seit(con: sqlite3.Connection) -> tuple[str, int]:
    row = con.execute("SELECT zeitpunkt, betrag_cent FROM kassenbuch WHERE art = 'Anfangsbestand'"
                      " ORDER BY id DESC LIMIT 1").fetchone()
    return (row[0], row[1]) if row else ("", 0)


def kassastand(con: sqlite3.Connection) -> int:
    seit, anfang = _seit(con)
    bewegungen = con.execute(
        "SELECT COALESCE(SUM(CASE art WHEN 'Entnahme' THEN -betrag_cent ELSE betrag_cent END), 0)"
        " FROM kassenbuch WHERE art != 'Anfangsbestand' AND zeitpunkt >= ?", (seit,)).fetchone()[0]
    bar = con.execute(
        "SELECT COALESCE(SUM(z.betrag_cent), 0) FROM zahlungen z JOIN belege b ON b.id = z.beleg_id"
        " WHERE z.art = 'Bar' AND b.zeitpunkt >= ?", (seit,)).fetchone()[0]
    return anfang + bewegungen + bar


def eintraege(con: sqlite3.Connection, datum: str | None = None) -> list[dict]:
    """Kassenbuch-Einträge inkl. Bareinnahmen je Tag (zusammengefasst)."""
    datum = datum or dt.date.today().isoformat()
    zeilen = [dict(r) | {"benutzer": r["benutzer"]} for r in con.execute(
        "SELECT k.*, u.name AS benutzer FROM kassenbuch k LEFT JOIN benutzer u ON u.id = k.benutzer_id"
        " WHERE substr(k.zeitpunkt, 1, 10) = ? ORDER BY k.id", (datum,))]
    bar = con.execute(
        "SELECT COALESCE(SUM(z.betrag_cent), 0), COUNT(DISTINCT b.id) FROM zahlungen z JOIN belege b ON b.id = z.beleg_id"
        " WHERE z.art = 'Bar' AND substr(b.zeitpunkt, 1, 10) = ?", (datum,)).fetchone()
    if bar[1]:
        zeilen.append({"zeitpunkt": datum, "art": "Bareinnahmen", "betrag_cent": bar[0],
                       "text": f"{bar[1]} Beleg(e) laut Kasse", "benutzer": None})
    return zeilen


def zaehlprotokoll(con: sqlite3.Connection, stueckelung: dict, benutzer_id: int | None = None,
                   differenz_buchen: bool = True) -> dict:
    """Erfasst einen Kassasturz. ``stueckelung`` = {Nennwert in Cent: Anzahl}."""
    ist = 0
    details = {}
    for wert, anzahl in stueckelung.items():
        wert, anzahl = int(wert), int(anzahl or 0)
        if wert not in STUECKELUNG or anzahl < 0:
            raise KassenFehler(f"Ungültige Stückelung: {wert}")
        if anzahl:
            details[str(wert)] = anzahl
            ist += wert * anzahl
    soll = kassastand(con)
    pid = con.execute("INSERT INTO zaehlprotokolle (zeitpunkt, soll_cent, ist_cent, details, benutzer_id) VALUES (?,?,?,?,?)",
                      (_jetzt(), soll, ist, json.dumps(details), benutzer_id)).lastrowid
    if differenz_buchen and ist != soll:
        con.execute("INSERT INTO kassenbuch (zeitpunkt, art, betrag_cent, text, benutzer_id) VALUES (?,?,?,?,?)",
                    (_jetzt(), "Differenz", ist - soll, f"Zählprotokoll Nr. {pid}", benutzer_id))
    con.commit()
    return {"id": pid, "soll": soll, "ist": ist, "differenz": ist - soll}
