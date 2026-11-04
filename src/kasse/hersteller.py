"""Herstellerangaben und Werbehinweise (kiber.at).

Die Hinweise auf Bon, A4-Dokumenten und in E-Mails sind standardmäßig aktiv
und können vom Betrieb unter Einstellungen → Über abgeschaltet werden.
Anmeldebildschirm, „Über“-Bereich und Installer zeigen den Hersteller immer.
"""

from __future__ import annotations

import sqlite3

from .db import einstellung

HERSTELLER = "kiber.at"
WEBSITE = "https://www.kiber.at"
WEBSITE_KURZ = "www.kiber.at"

# Werbehinweis: bewusst nur die Adresse
WERBUNG_BON = WEBSITE_KURZ
WERBUNG_A4 = WEBSITE_KURZ
WERBUNG_MAIL = WEBSITE_KURZ

ATRUST_HINWEIS = (f"Für den Echtbetrieb wird eine A-Trust-Registrierkassenlizenz (a.sign RK Online) benötigt – "
                  f"erhältlich über {WEBSITE_KURZ}.")

#: Einstellungsschlüssel → Standardwert ("1" = Hinweis anzeigen)
WERBUNG_STANDARD = {"werbung_bon": "1", "werbung_a4": "1", "werbung_mail": "1"}


def werbung_aktiv(con: sqlite3.Connection, wo: str) -> bool:
    """wo: 'bon' | 'a4' | 'mail'"""
    return (einstellung(con, f"werbung_{wo}", "1") or "1") != "0"
