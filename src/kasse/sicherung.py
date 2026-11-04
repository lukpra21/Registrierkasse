"""Automatische Datensicherung.

- Konsistente Kopie der laufenden Datenbank über die SQLite-Backup-API
- zusätzlich DEP-Export (RKSV-Datenerfassungsprotokoll) je Sicherung
- Integritätsprüfung der Sicherung
- Verschlüsselung (AES-256-GCM) mit Sicherungspasswort aus der Windows-Anmeldeinformationsverwaltung
- Rotation: die letzten N Sicherungen bleiben erhalten
- Ziel frei wählbar (USB-Stick, NAS, OneDrive-/Cloud-Ordner) – idealerweise NICHT
  dasselbe Laufwerk wie die Kasse.

Ausgelöst wird die Sicherung
- beim Programmstart, wenn die letzte Sicherung älter als das Intervall ist,
- nach jedem Tagesabschluss bzw. Monatsbeleg,
- per Windows-Aufgabenplanung (``kasse sicherung-planen``).
"""

from __future__ import annotations

import datetime as dt
import hashlib
import io
import os
import sqlite3
import tempfile
import subprocess
import sys
import zipfile
from pathlib import Path

from .config import datenverzeichnis
from .db import einstellung, setze_einstellung
from .rksv.dep import dep_export_datei

PRAEFIX = "kasse-sicherung-"


def sicherungsziel(con: sqlite3.Connection) -> Path:
    ziel = Path(einstellung(con, "sicherung_ziel") or (datenverzeichnis() / "sicherungen"))
    ziel.mkdir(parents=True, exist_ok=True)
    return ziel


MAGIC = b"RKSICH1\0"


def _schluessel(passwort: str, salz: bytes) -> bytes:
    return hashlib.scrypt(passwort.encode(), salt=salz, n=2**15, r=8, p=1, maxmem=64 * 1024 * 1024, dklen=32)


def verschluesseln(daten: bytes, passwort: str) -> bytes:
    """AES-256-GCM, Schlüssel per scrypt aus dem Sicherungspasswort."""
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    salz, nonce = os.urandom(16), os.urandom(12)
    return MAGIC + salz + nonce + AESGCM(_schluessel(passwort, salz)).encrypt(nonce, daten, MAGIC)


def entschluesseln(daten: bytes, passwort: str | None) -> bytes:
    if not daten.startswith(MAGIC):
        return daten  # unverschlüsselte (ältere) Sicherung
    from cryptography.exceptions import InvalidTag
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    if not passwort:
        raise ValueError("Sicherung ist verschlüsselt – Passwort erforderlich")
    salz, nonce, rest = daten[8:24], daten[24:36], daten[36:]
    try:
        return AESGCM(_schluessel(passwort, salz)).decrypt(nonce, rest, MAGIC)
    except InvalidTag as e:
        raise ValueError("Falsches Passwort oder beschädigte Sicherung") from e


def _sicherungen(ziel: Path) -> list[Path]:
    return sorted([*ziel.glob(f"{PRAEFIX}*.zip"), *ziel.glob(f"{PRAEFIX}*.rksich")], key=lambda p: p.name)


def sichern(con: sqlite3.Connection, ziel: Path | None = None, behalten: int | None = None,
            passwort: str | None = None) -> Path:
    """Erstellt eine Sicherung. Mit Sicherungspasswort (Einstellungen) wird sie verschlüsselt (.rksich)."""
    from . import geheim

    ziel = ziel or sicherungsziel(con)
    behalten = behalten or int(einstellung(con, "sicherung_behalten", "30") or 30)
    passwort = passwort if passwort is not None else geheim.lesen("sicherung")
    stempel = dt.datetime.now().strftime("%Y%m%d-%H%M%S-%f")

    with tempfile.TemporaryDirectory() as tmp:
        db_kopie = Path(tmp) / "kasse.db"
        dst = sqlite3.connect(db_kopie)
        with dst:
            con.backup(dst)
        ok = dst.execute("PRAGMA integrity_check").fetchone()[0]
        dst.close()
        if ok != "ok":
            raise RuntimeError(f"Integritätsprüfung der Sicherung fehlgeschlagen: {ok}")
        dep = dep_export_datei(con, Path(tmp) / "dep-export.json")
        puffer = io.BytesIO()
        with zipfile.ZipFile(puffer, "w", zipfile.ZIP_DEFLATED) as z:
            z.write(db_kopie, "kasse.db")
            z.write(dep, "dep-export.json")
        daten = puffer.getvalue()

    if passwort:
        archiv = ziel / f"{PRAEFIX}{stempel}.rksich"
        inhalt = verschluesseln(daten, passwort)
    else:
        archiv = ziel / f"{PRAEFIX}{stempel}.zip"
        inhalt = daten
    teil = archiv.with_name(archiv.name + ".teil")
    teil.write_bytes(inhalt)
    # Kontrolle: Sicherung zurücklesen und prüfen
    with zipfile.ZipFile(io.BytesIO(entschluesseln(teil.read_bytes(), passwort))) as z:
        if z.testzip() is not None:
            teil.unlink()
            raise RuntimeError("Sicherungsarchiv ist beschädigt")
    teil.replace(archiv)

    for alt in _sicherungen(ziel)[:-behalten]:
        alt.unlink()
    setze_einstellung(con, "sicherung_zuletzt", dt.datetime.now().isoformat(timespec="seconds"))
    setze_einstellung(con, "sicherung_verschluesselt", "1" if passwort else "0")
    con.commit()
    return archiv


def liste(con: sqlite3.Connection) -> list[dict]:
    ziel = sicherungsziel(con)
    return [{"datei": str(p), "name": p.name, "groesse": p.stat().st_size,
             "verschluesselt": p.suffix == ".rksich"} for p in reversed(_sicherungen(ziel))]


def sicherung_faellig(con: sqlite3.Connection) -> bool:
    zuletzt = einstellung(con, "sicherung_zuletzt")
    if not zuletzt:
        return True
    stunden = float(einstellung(con, "sicherung_intervall_stunden", "24") or 24)
    return dt.datetime.now() - dt.datetime.fromisoformat(zuletzt) >= dt.timedelta(hours=stunden)


def sichern_wenn_faellig(con: sqlite3.Connection) -> Path | None:
    return sichern(con) if sicherung_faellig(con) else None


def wiederherstellen(archiv: Path | str, ziel_db: Path | str, passwort: str | None = None) -> None:
    """Stellt eine Sicherung wieder her. Ziel darf nicht existieren (keine versehentliche Überschreibung)."""
    ziel_db = Path(ziel_db)
    if ziel_db.exists():
        raise FileExistsError(f"{ziel_db} existiert bereits – bitte zuerst umbenennen")
    with zipfile.ZipFile(io.BytesIO(entschluesseln(Path(archiv).read_bytes(), passwort))) as z:
        ziel_db.write_bytes(z.read("kasse.db"))
    pruef = sqlite3.connect(ziel_db)
    try:
        if pruef.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise ValueError("Wiederhergestellte Datenbank ist beschädigt")
    finally:
        pruef.close()


def wiederherstellung_vormerken(archiv: Path | str, db_pfad: Path | str, passwort: str | None = None) -> Path:
    """Legt die Sicherung als ``kasse.db.neu`` ab; sie wird beim nächsten Programmstart übernommen."""
    neu = Path(str(db_pfad) + ".neu")
    if neu.exists():
        neu.unlink()
    wiederherstellen(archiv, neu, passwort)
    return neu


def vorgemerkte_wiederherstellung_anwenden(db_pfad: Path | str) -> Path | None:
    """Beim Start (vor dem Öffnen der Datenbank): aktuelle DB aufheben und vorgemerkte übernehmen."""
    db_pfad = Path(db_pfad)
    neu = Path(str(db_pfad) + ".neu")
    if not neu.exists():
        return None
    alt = None
    if db_pfad.exists():
        alt = db_pfad.with_name(f"kasse-vor-wiederherstellung-{dt.datetime.now():%Y%m%d-%H%M%S}.db")
        db_pfad.replace(alt)
    neu.replace(db_pfad)
    return alt


def windows_aufgabe_planen(uhrzeit: str = "21:00") -> str:
    """Legt eine tägliche Windows-Aufgabe 'Registrierkasse Sicherung' an."""
    if sys.platform != "win32":
        raise OSError("Aufgabenplanung nur unter Windows")
    if getattr(sys, "frozen", False):  # installierte Version: eigene Kommandozeilen-EXE
        befehl = f'"{Path(sys.executable).with_name("kasse-cli.exe")}" sicherung'
    else:
        befehl = f'"{sys.executable}" -m kasse.cli sicherung'
    subprocess.run(
        ["schtasks", "/Create", "/F", "/SC", "DAILY", "/ST", uhrzeit,
         "/TN", "Registrierkasse Sicherung", "/TR", befehl],
        check=True,
    )
    return befehl
