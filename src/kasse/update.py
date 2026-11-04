"""Automatische Updates.

Unter ``update_url`` (Einstellungen) liegt eine JSON-Datei, die beim Release
erzeugt wird:

    {"version": "0.3.0", "url": "https://…/Registrierkasse-Setup-0.3.0.exe",
     "sha256": "…", "hinweis": "Neu: …"}

Die Kasse prüft beim Start, lädt das Setup auf Wunsch herunter, prüft die
SHA-256-Prüfsumme und startet die Installation. Nur HTTPS ist erlaubt.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

from . import __version__


class UpdateFehler(RuntimeError):
    pass


def _version(t: str) -> tuple[int, ...]:
    return tuple(int(x) for x in t.strip().lstrip("v").split(".") if x.isdigit())


def _https(url: str) -> str:
    if not url.lower().startswith("https://"):
        raise UpdateFehler("Update-Adresse muss mit https:// beginnen")
    return url


def pruefen(update_url: str | None, aktuell: str = __version__, timeout: float = 8.0) -> dict | None:
    """Liefert die Update-Info, wenn eine neuere Version verfügbar ist, sonst None."""
    if not update_url:
        return None
    try:
        with urllib.request.urlopen(_https(update_url), timeout=timeout) as r:
            info = json.loads(r.read().decode())
    except UpdateFehler:
        raise
    except Exception as e:
        raise UpdateFehler(f"Update-Prüfung fehlgeschlagen: {e}") from e
    if not {"version", "url", "sha256"} <= info.keys():
        raise UpdateFehler("Update-Information unvollständig")
    return info if _version(info["version"]) > _version(aktuell) else None


def herunterladen(info: dict, ziel_ordner: Path | None = None) -> Path:
    ziel_ordner = ziel_ordner or Path(tempfile.gettempdir())
    ziel = ziel_ordner / Path(info["url"].split("?")[0]).name
    h = hashlib.sha256()
    with urllib.request.urlopen(_https(info["url"]), timeout=60) as r, open(ziel, "wb") as f:
        while block := r.read(1 << 16):
            h.update(block)
            f.write(block)
    if h.hexdigest().lower() != info["sha256"].lower():
        ziel.unlink(missing_ok=True)
        raise UpdateFehler("Prüfsumme des Updates stimmt nicht – Installation abgebrochen")
    return ziel


def installieren(setup: Path) -> None:
    """Startet das Setup (Inno Setup, ohne Rückfragen) und beendet die Kasse."""
    if sys.platform != "win32":
        raise UpdateFehler("Automatische Installation nur unter Windows")
    subprocess.Popen([str(setup), "/SILENT", "/CLOSEAPPLICATIONS", "/RESTARTAPPLICATIONS"], close_fds=True)
