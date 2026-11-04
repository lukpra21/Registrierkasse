"""Benutzer mit PIN und Rollen.

Rollen:
- ``chef``: alles
- ``kassier``: kassieren, Belege ausgeben, Kassenbuch (Einlage/Entnahme), Zählprotokoll

Solange kein Benutzer angelegt ist, ist keine Anmeldung nötig (Einzelbetrieb).
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
import sqlite3

from .rksv.kasse import KassenFehler

ROLLEN = ("chef", "kassier")


def _hash(pin: str, salz: bytes) -> bytes:
    return hashlib.scrypt(pin.encode(), salt=salz, n=2**14, r=8, p=1, dklen=32)


def pin_hash(pin: str) -> str:
    if not pin.isdigit() or not 4 <= len(pin) <= 8:
        raise KassenFehler("PIN muss aus 4–8 Ziffern bestehen")
    salz = os.urandom(16)
    return base64.b64encode(salz + _hash(pin, salz)).decode()


def pin_pruefen(pin: str, gespeichert: str) -> bool:
    roh = base64.b64decode(gespeichert)
    return hmac.compare_digest(roh[16:], _hash(pin, roh[:16]))


def gibt_benutzer(con: sqlite3.Connection) -> bool:
    return con.execute("SELECT 1 FROM benutzer WHERE aktiv = 1").fetchone() is not None


def speichern(con: sqlite3.Connection, name: str, rolle: str, pin: str | None = None,
              benutzer_id: int | None = None, aktiv: bool = True) -> int:
    name = name.strip()
    if not name:
        raise KassenFehler("Name fehlt")
    if rolle not in ROLLEN:
        raise KassenFehler("Unbekannte Rolle")
    if benutzer_id is None:
        if not pin:
            raise KassenFehler("PIN fehlt")
        if not gibt_benutzer(con) and rolle != "chef":
            raise KassenFehler("Der erste Benutzer muss die Rolle Chef haben")
        bid = con.execute("INSERT INTO benutzer (name, pin_hash, rolle) VALUES (?,?,?)",
                          (name, pin_hash(pin), rolle)).lastrowid
    else:
        bid = benutzer_id
        con.execute("UPDATE benutzer SET name = ?, rolle = ?, aktiv = ? WHERE id = ?", (name, rolle, int(aktiv), bid))
        if pin:
            con.execute("UPDATE benutzer SET pin_hash = ? WHERE id = ?", (pin_hash(pin), bid))
    chefs = con.execute("SELECT COUNT(*) FROM benutzer WHERE rolle = 'chef' AND aktiv = 1").fetchone()[0]
    if gibt_benutzer(con) and chefs == 0:
        con.rollback()
        raise KassenFehler("Mindestens ein aktiver Chef-Benutzer ist erforderlich")
    con.commit()
    return bid


def anmelden(con: sqlite3.Connection, pin: str) -> dict | None:
    """Sucht den aktiven Benutzer mit dieser PIN (PINs sind je Benutzer eindeutig zu wählen)."""
    for b in con.execute("SELECT * FROM benutzer WHERE aktiv = 1"):
        if pin_pruefen(pin, b["pin_hash"]):
            return {"id": b["id"], "name": b["name"], "rolle": b["rolle"]}
    return None


def liste(con: sqlite3.Connection) -> list[dict]:
    return [{"id": b["id"], "name": b["name"], "rolle": b["rolle"], "aktiv": b["aktiv"]}
            for b in con.execute("SELECT * FROM benutzer ORDER BY aktiv DESC, name")]
