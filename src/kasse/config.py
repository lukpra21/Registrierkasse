"""Pfade und Laufzeitkonfiguration.

Alle Kassen- und Kundendaten liegen im Datenverzeichnis des Benutzers,
niemals im Programmverzeichnis bzw. Repository.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def datenverzeichnis() -> Path:
    if env := os.environ.get("KASSE_DATENVERZEICHNIS"):
        pfad = Path(env)
    elif sys.platform == "win32":
        pfad = Path(os.environ.get("APPDATA", Path.home())) / "Registrierkasse"
    else:
        pfad = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / "registrierkasse"
    pfad.mkdir(parents=True, exist_ok=True)
    return pfad


def datenbankpfad() -> Path:
    return datenverzeichnis() / "kasse.db"
