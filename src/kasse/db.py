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

# Schema-Erweiterungen; Index + 1 = PRAGMA user_version nach Anwendung
MIGRATIONEN = [
    # 1: Benutzer, Zahlungen (Mischzahlung), Kassenbuch, Gutscheine, Lager, Rabatte, Ereignisprotokoll
    """
    CREATE TABLE benutzer (
        id       INTEGER PRIMARY KEY,
        name     TEXT NOT NULL UNIQUE,
        pin_hash TEXT NOT NULL,
        rolle    TEXT NOT NULL CHECK (rolle IN ('chef', 'kassier')),
        aktiv    INTEGER NOT NULL DEFAULT 1
    );
    ALTER TABLE belege ADD COLUMN benutzer_id INTEGER REFERENCES benutzer(id);
    ALTER TABLE belegpositionen ADD COLUMN rabatt_cent INTEGER NOT NULL DEFAULT 0;
    CREATE TABLE zahlungen (
        id         INTEGER PRIMARY KEY,
        beleg_id   INTEGER NOT NULL REFERENCES belege(id),
        art        TEXT NOT NULL,
        betrag_cent INTEGER NOT NULL,
        referenz   TEXT
    );
    CREATE INDEX zahlungen_beleg ON zahlungen(beleg_id);
    INSERT INTO zahlungen (beleg_id, art, betrag_cent)
        SELECT id, zahlungsart, betrag_normal + betrag_ermaessigt1 + betrag_ermaessigt2 + betrag_null + betrag_besonders
        FROM belege WHERE zahlungsart IS NOT NULL AND art IN ('Barumsatz', 'Storno');
    CREATE TABLE kassenbuch (
        id          INTEGER PRIMARY KEY,
        zeitpunkt   TEXT NOT NULL,
        art         TEXT NOT NULL CHECK (art IN ('Anfangsbestand', 'Einlage', 'Entnahme', 'Differenz')),
        betrag_cent INTEGER NOT NULL,
        text        TEXT,
        benutzer_id INTEGER REFERENCES benutzer(id)
    );
    CREATE TABLE zaehlprotokolle (
        id          INTEGER PRIMARY KEY,
        zeitpunkt   TEXT NOT NULL,
        soll_cent   INTEGER NOT NULL,
        ist_cent    INTEGER NOT NULL,
        details     TEXT,
        benutzer_id INTEGER REFERENCES benutzer(id)
    );
    CREATE TABLE gutscheine (
        id              INTEGER PRIMARY KEY,
        code            TEXT NOT NULL UNIQUE,
        wert_cent       INTEGER NOT NULL,
        rest_cent       INTEGER NOT NULL,
        verkauf_beleg_id INTEGER REFERENCES belege(id),
        erstellt        TEXT NOT NULL,
        gueltig_bis     TEXT
    );
    CREATE TABLE gutschein_buchungen (
        gutschein_id INTEGER NOT NULL REFERENCES gutscheine(id),
        beleg_id     INTEGER NOT NULL REFERENCES belege(id),
        betrag_cent  INTEGER NOT NULL
    );
    ALTER TABLE artikel ADD COLUMN lagerstand TEXT;
    ALTER TABLE artikel ADD COLUMN mindestbestand TEXT;
    CREATE TABLE lagerbewegungen (
        id         INTEGER PRIMARY KEY,
        artikel_id INTEGER NOT NULL REFERENCES artikel(id),
        zeitpunkt  TEXT NOT NULL,
        menge      TEXT NOT NULL,
        grund      TEXT NOT NULL
    );
    ALTER TABLE dokumente ADD COLUMN bezahlt_am TEXT;
    ALTER TABLE dokumente ADD COLUMN gemailt_am TEXT;
    UPDATE dokumente SET bezahlt_am = datum WHERE typ = 'Rechnung' AND beleg_id IS NOT NULL;
    CREATE TABLE ereignisse (
        id          INTEGER PRIMARY KEY,
        zeitpunkt   TEXT NOT NULL,
        benutzer_id INTEGER REFERENCES benutzer(id),
        art         TEXT NOT NULL,
        text        TEXT
    );
    """,
]

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
    _migrieren(con)
    if con.execute("SELECT COUNT(*) FROM steuersaetze").fetchone()[0] == 0:
        con.executemany(
            "INSERT INTO steuersaetze (prozent, rksv_satz, bezeichnung) VALUES (?, ?, ?)",
            STANDARD_STEUERSAETZE,
        )
    con.commit()
    return con


def _migrieren(con: sqlite3.Connection) -> None:
    version = con.execute("PRAGMA user_version").fetchone()[0]
    for i, skript in enumerate(MIGRATIONEN[version:], start=version + 1):
        con.executescript(f"BEGIN; {skript}; PRAGMA user_version = {i}; COMMIT;")


def ereignis(con: sqlite3.Connection, art: str, text: str = "", benutzer_id: int | None = None) -> None:
    """Protokolliert sicherheitsrelevante Vorgänge (Anmeldung, Lade öffnen, Einstellungen …)."""
    import datetime as dt

    con.execute("INSERT INTO ereignisse (zeitpunkt, benutzer_id, art, text) VALUES (?,?,?,?)",
                (dt.datetime.now().isoformat(timespec="seconds"), benutzer_id, art, text))


def einstellung(con: sqlite3.Connection, schluessel: str, standard: str | None = None) -> str | None:
    row = con.execute("SELECT wert FROM einstellungen WHERE schluessel = ?", (schluessel,)).fetchone()
    return row[0] if row else standard


def setze_einstellung(con: sqlite3.Connection, schluessel: str, wert: str) -> None:
    con.execute(
        "INSERT INTO einstellungen (schluessel, wert) VALUES (?, ?) "
        "ON CONFLICT(schluessel) DO UPDATE SET wert = excluded.wert",
        (schluessel, wert),
    )
