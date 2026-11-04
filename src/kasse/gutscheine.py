"""Wertgutscheine (Mehrzweckgutscheine).

Umsatzsteuerliche Behandlung (mit dem Steuerberater abstimmen):
- Verkauf: Position zum Steuersatz 0 % (Betrag-Satz-Null im RKSV-Beleg); die
  Umsatzsteuer entsteht erst bei Einlösung.
- Einlösung: Waren mit ihren Steuersätzen + negative Gutschein-Position mit 0 %.
"""

from __future__ import annotations

import datetime as dt
import secrets
import sqlite3

from .rksv.kasse import KassenFehler

ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # ohne verwechselbare Zeichen


def neuer_code(con: sqlite3.Connection) -> str:
    while True:
        code = "-".join("".join(secrets.choice(ALPHABET) for _ in range(4)) for _ in range(3))
        if not con.execute("SELECT 1 FROM gutscheine WHERE code = ?", (code,)).fetchone():
            return code


def normalisieren(code: str) -> str:
    c = code.strip().upper().replace(" ", "").replace("-", "")
    return "-".join(c[i:i + 4] for i in range(0, len(c), 4))


def pruefen(con: sqlite3.Connection, code: str) -> dict:
    g = con.execute("SELECT * FROM gutscheine WHERE code = ?", (normalisieren(code),)).fetchone()
    if not g:
        raise KassenFehler("Gutschein nicht gefunden")
    if g["gueltig_bis"] and g["gueltig_bis"] < dt.date.today().isoformat():
        raise KassenFehler(f"Gutschein abgelaufen ({g['gueltig_bis']})")
    if g["rest_cent"] <= 0:
        raise KassenFehler("Gutschein ist bereits vollständig eingelöst")
    return dict(g)


def anlegen(con: sqlite3.Connection, code: str, wert_cent: int, beleg_id: int, gueltig_jahre: int = 30) -> None:
    if wert_cent <= 0:
        raise KassenFehler("Gutscheinwert muss positiv sein")
    heute = dt.date.today()
    bis = heute.replace(year=heute.year + gueltig_jahre) if gueltig_jahre else None
    con.execute("INSERT INTO gutscheine (code, wert_cent, rest_cent, verkauf_beleg_id, erstellt, gueltig_bis)"
                " VALUES (?,?,?,?,?,?)", (code, wert_cent, wert_cent, beleg_id, heute.isoformat(),
                                          bis.isoformat() if bis else None))


def einloesen(con: sqlite3.Connection, code: str, betrag_cent: int, beleg_id: int) -> None:
    g = pruefen(con, code)
    if betrag_cent > g["rest_cent"]:
        raise KassenFehler("Einlösebetrag höher als das Gutscheinguthaben")
    con.execute("UPDATE gutscheine SET rest_cent = rest_cent - ? WHERE id = ?", (betrag_cent, g["id"]))
    con.execute("INSERT INTO gutschein_buchungen VALUES (?,?,?)", (g["id"], beleg_id, betrag_cent))


def liste(con: sqlite3.Connection) -> list[dict]:
    return [dict(r) for r in con.execute("SELECT * FROM gutscheine ORDER BY id DESC LIMIT 300")]
