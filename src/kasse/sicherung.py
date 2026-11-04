"""Automatische Datensicherung.

- Konsistente Kopie der laufenden Datenbank über die SQLite-Backup-API
- zusätzlich DEP-Export (RKSV-Datenerfassungsprotokoll) je Sicherung
- Integritätsprüfung der Sicherung
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
import sqlite3
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


def sichern(con: sqlite3.Connection, ziel: Path | None = None, behalten: int | None = None) -> Path:
    ziel = ziel or sicherungsziel(con)
    behalten = behalten or int(einstellung(con, "sicherung_behalten", "30") or 30)
    stempel = dt.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    arbeits = ziel / f".{PRAEFIX}{stempel}"
    arbeits.mkdir(parents=True, exist_ok=False)
    try:
        db_kopie = arbeits / "kasse.db"
        dst = sqlite3.connect(db_kopie)
        with dst:
            con.backup(dst)
        ok = dst.execute("PRAGMA integrity_check").fetchone()[0]
        dst.close()
        if ok != "ok":
            raise RuntimeError(f"Integritätsprüfung der Sicherung fehlgeschlagen: {ok}")
        dep = dep_export_datei(con, arbeits / "dep-export.json")

        archiv = ziel / f"{PRAEFIX}{stempel}.zip"
        with zipfile.ZipFile(archiv, "w", zipfile.ZIP_DEFLATED) as z:
            z.write(db_kopie, "kasse.db")
            z.write(dep, "dep-export.json")
        with zipfile.ZipFile(archiv) as z:
            if z.testzip() is not None:
                raise RuntimeError("Sicherungsarchiv ist beschädigt")
    finally:
        for f in arbeits.glob("*"):
            f.unlink()
        arbeits.rmdir()

    for alt in sorted(ziel.glob(f"{PRAEFIX}*.zip"))[:-behalten]:
        alt.unlink()
    setze_einstellung(con, "sicherung_zuletzt", dt.datetime.now().isoformat(timespec="seconds"))
    con.commit()
    return archiv


def sicherung_faellig(con: sqlite3.Connection) -> bool:
    zuletzt = einstellung(con, "sicherung_zuletzt")
    if not zuletzt:
        return True
    stunden = float(einstellung(con, "sicherung_intervall_stunden", "24") or 24)
    return dt.datetime.now() - dt.datetime.fromisoformat(zuletzt) >= dt.timedelta(hours=stunden)


def sichern_wenn_faellig(con: sqlite3.Connection) -> Path | None:
    return sichern(con) if sicherung_faellig(con) else None


def wiederherstellen(archiv: Path | str, ziel_db: Path | str) -> None:
    """Stellt eine Sicherung wieder her. Ziel darf nicht existieren (keine versehentliche Überschreibung)."""
    ziel_db = Path(ziel_db)
    if ziel_db.exists():
        raise FileExistsError(f"{ziel_db} existiert bereits – bitte zuerst umbenennen")
    with zipfile.ZipFile(archiv) as z:
        ziel_db.write_bytes(z.read("kasse.db"))


def windows_aufgabe_planen(uhrzeit: str = "21:00") -> str:
    """Legt eine tägliche Windows-Aufgabe 'Registrierkasse Sicherung' an."""
    if sys.platform != "win32":
        raise OSError("Aufgabenplanung nur unter Windows")
    befehl = f'"{sys.executable}" -m kasse.cli sicherung'
    subprocess.run(
        ["schtasks", "/Create", "/F", "/SC", "DAILY", "/ST", uhrzeit,
         "/TN", "Registrierkasse Sicherung", "/TR", befehl],
        check=True,
    )
    return befehl
