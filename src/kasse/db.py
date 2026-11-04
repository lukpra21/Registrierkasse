"""SQLite-Datenhaltung."""

from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS einstellungen (
    schluessel TEXT PRIMARY KEY,
    wert       TEXT
);

-- RKSV-Satz: Normal | Ermaessigt-1 | Ermaessigt-2 | Null | Besonders
CREATE TABLE IF NOT EXISTS steuersaetze (
    id          INTEGER PRIMARY KEY,
    prozent     TEXT NOT NULL UNIQUE,
    rksv_satz   TEXT NOT NULL,
    bezeichnung TEXT
);

CREATE TABLE IF NOT EXISTS warengruppen (
    id       INTEGER PRIMARY KEY,
    name     TEXT NOT NULL UNIQUE,
    sichtbar INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS artikel (
    id             INTEGER PRIMARY KEY,
    artikelnummer  TEXT UNIQUE,
    barcode        TEXT,
    name           TEXT NOT NULL,
    warengruppe_id INTEGER REFERENCES warengruppen(id),
    brutto_cent    INTEGER NOT NULL,
    steuer_prozent TEXT NOT NULL,
    einheit        TEXT NOT NULL DEFAULT 'Stk',
    sichtbar       INTEGER NOT NULL DEFAULT 1,
    beschreibung   TEXT,
    herkunft       TEXT
);

CREATE TABLE IF NOT EXISTS kunden (
    id                INTEGER PRIMARY KEY,
    kundennummer      TEXT UNIQUE,
    name              TEXT NOT NULL,
    adresse           TEXT,
    uid               TEXT,
    email             TEXT,
    zahlungsziel_tage INTEGER NOT NULL DEFAULT 14
);

-- RKSV-Belege (Barumsätze, Null-/Start-/Monats-/Jahres-/Schlussbelege)
CREATE TABLE IF NOT EXISTS belege (
    id                  INTEGER PRIMARY KEY,
    belegnummer         INTEGER NOT NULL UNIQUE,
    art                 TEXT NOT NULL,
    zeitpunkt           TEXT NOT NULL,
    kunde_id            INTEGER REFERENCES kunden(id),
    zahlungsart         TEXT,
    betrag_normal       INTEGER NOT NULL DEFAULT 0,
    betrag_ermaessigt1  INTEGER NOT NULL DEFAULT 0,
    betrag_ermaessigt2  INTEGER NOT NULL DEFAULT 0,
    betrag_null         INTEGER NOT NULL DEFAULT 0,
    betrag_besonders    INTEGER NOT NULL DEFAULT 0,
    umsatzzaehler       INTEGER NOT NULL,
    zertifikat_serie    TEXT NOT NULL,
    jws                 TEXT NOT NULL,
    ausfall             INTEGER NOT NULL DEFAULT 0,
    storno_von          INTEGER REFERENCES belege(id)
);

CREATE TABLE IF NOT EXISTS belegpositionen (
    beleg_id         INTEGER NOT NULL REFERENCES belege(id),
    pos              INTEGER NOT NULL,
    artikel_id       INTEGER REFERENCES artikel(id),
    bezeichnung      TEXT NOT NULL,
    menge            TEXT NOT NULL,
    einzelpreis_cent INTEGER NOT NULL,
    steuer_prozent   TEXT NOT NULL,
    summe_cent       INTEGER NOT NULL,
    PRIMARY KEY (beleg_id, pos)
);

-- Lieferscheine und A4-Rechnungen für Geschäftskunden
CREATE TABLE IF NOT EXISTS dokumente (
    id          INTEGER PRIMARY KEY,
    typ         TEXT NOT NULL CHECK (typ IN ('Lieferschein', 'Rechnung')),
    nummer      TEXT NOT NULL,
    datum       TEXT NOT NULL,
    kunde_id    INTEGER NOT NULL REFERENCES kunden(id),
    zahlungsart TEXT,
    beleg_id    INTEGER REFERENCES belege(id),
    bezug_id    INTEGER REFERENCES dokumente(id),
    UNIQUE (typ, nummer)
);

-- welche Lieferscheine mit welcher Rechnung verrechnet wurden
CREATE TABLE IF NOT EXISTS dokument_bezug (
    rechnung_id     INTEGER NOT NULL REFERENCES dokumente(id),
    lieferschein_id INTEGER NOT NULL UNIQUE REFERENCES dokumente(id)
);

CREATE TABLE IF NOT EXISTS dokumentpositionen (
    dokument_id      INTEGER NOT NULL REFERENCES dokumente(id),
    pos              INTEGER NOT NULL,
    artikel_id       INTEGER REFERENCES artikel(id),
    bezeichnung      TEXT NOT NULL,
    menge            TEXT NOT NULL,
    einheit          TEXT NOT NULL DEFAULT 'Stk',
    einzelpreis_cent INTEGER NOT NULL,
    steuer_prozent   TEXT NOT NULL,
    PRIMARY KEY (dokument_id, pos)
);
"""

STANDARD_STEUERSAETZE = [
    ("20", "Normal", "Normalsteuersatz"),
    ("10", "Ermaessigt-1", "Ermäßigt 10 %"),
    ("13", "Ermaessigt-2", "Ermäßigt 13 %"),
    ("0", "Null", "Steuerfrei"),
    ("19", "Besonders", "Besonderer Steuersatz"),
]


def verbinden(pfad: Path | str) -> sqlite3.Connection:
    # check_same_thread=False: die Oberfläche ruft aus mehreren Threads auf (Zugriff per Lock serialisiert)
    con = sqlite3.connect(str(pfad), check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    con.executescript(SCHEMA)
    if con.execute("SELECT COUNT(*) FROM steuersaetze").fetchone()[0] == 0:
        con.executemany(
            "INSERT INTO steuersaetze (prozent, rksv_satz, bezeichnung) VALUES (?, ?, ?)",
            STANDARD_STEUERSAETZE,
        )
    con.commit()
    return con


def einstellung(con: sqlite3.Connection, schluessel: str, standard: str | None = None) -> str | None:
    row = con.execute("SELECT wert FROM einstellungen WHERE schluessel = ?", (schluessel,)).fetchone()
    return row[0] if row else standard


def setze_einstellung(con: sqlite3.Connection, schluessel: str, wert: str) -> None:
    con.execute(
        "INSERT INTO einstellungen (schluessel, wert) VALUES (?, ?) "
        "ON CONFLICT(schluessel) DO UPDATE SET wert = excluded.wert",
        (schluessel, wert),
    )
