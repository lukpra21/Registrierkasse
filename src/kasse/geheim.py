"""Geheimnisse (Passwörter, API-Schlüssel) in der Windows-Anmeldeinformationsverwaltung.

Über das Paket ``keyring``; unter Windows landet alles verschlüsselt im
Credential Manager des angemeldeten Benutzers. Umgebungsvariablen haben
Vorrang (z. B. für Tests oder Server-Betrieb).
"""

from __future__ import annotations

import os

DIENST = "Registrierkasse"

UMGEBUNG = {
    "atrust": "KASSE_ATRUST_PASSWORT",
    "sicherung": "KASSE_SICHERUNG_PASSWORT",
    "smtp": "KASSE_SMTP_PASSWORT",
    "viva": "KASSE_VIVA_SECRET",
}


class GeheimFehler(RuntimeError):
    pass


def _keyring():
    try:
        import keyring  # type: ignore[import-not-found]
        from keyring.backends import fail  # type: ignore[import-not-found]

        if isinstance(keyring.get_keyring(), fail.Keyring):
            return None
        return keyring
    except Exception:
        return None


def lesen(name: str) -> str | None:
    if (env := UMGEBUNG.get(name)) and os.environ.get(env):
        return os.environ[env]
    kr = _keyring()
    if kr is None:
        return None
    try:
        return kr.get_password(DIENST, name)
    except Exception:
        return None


def schreiben(name: str, wert: str) -> None:
    kr = _keyring()
    if kr is None:
        raise GeheimFehler("Kein sicherer Passwortspeicher verfügbar (Windows-Anmeldeinformationsverwaltung)")
    if wert:
        kr.set_password(DIENST, name, wert)
    else:
        try:
            kr.delete_password(DIENST, name)
        except Exception:
            pass


def vorhanden(name: str) -> bool:
    return bool(lesen(name))
