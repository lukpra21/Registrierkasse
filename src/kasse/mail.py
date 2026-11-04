"""Versand von Rechnungen und Lieferscheinen per E-Mail (SMTP).

SMTP-Passwort liegt in der Windows-Anmeldeinformationsverwaltung.
"""

from __future__ import annotations

import smtplib
import sqlite3
import ssl
from email.message import EmailMessage
from email.utils import formataddr, make_msgid
from pathlib import Path

from . import geheim
from .db import einstellung
from .rksv.kasse import KassenFehler


def senden(con: sqlite3.Connection, an: str, betreff: str, text: str, anhaenge: list[Path]) -> None:
    host = einstellung(con, "smtp_host")
    absender = einstellung(con, "smtp_absender")
    if not host or not absender:
        raise KassenFehler("E-Mail ist nicht eingerichtet (Einstellungen → E-Mail)")
    if not an or "@" not in an:
        raise KassenFehler("Ungültige E-Mail-Adresse")
    port = int(einstellung(con, "smtp_port", "587") or 587)
    benutzer = einstellung(con, "smtp_benutzer") or absender
    sicherheit = einstellung(con, "smtp_sicherheit", "starttls")

    msg = EmailMessage()
    msg["From"] = formataddr((einstellung(con, "firma_name", "") or "", absender))
    msg["To"] = an
    msg["Subject"] = betreff
    msg["Message-ID"] = make_msgid()
    msg.set_content(text)
    for pfad in anhaenge:
        pfad = Path(pfad)
        typ = ("application", "pdf") if pfad.suffix.lower() == ".pdf" else ("application", "xml")
        msg.add_attachment(pfad.read_bytes(), maintype=typ[0], subtype=typ[1], filename=pfad.name)

    kontext = ssl.create_default_context()
    try:
        if sicherheit == "ssl":
            server = smtplib.SMTP_SSL(host, port, context=kontext, timeout=20)
        else:
            server = smtplib.SMTP(host, port, timeout=20)
            if sicherheit == "starttls":
                server.starttls(context=kontext)
        with server:
            if passwort := geheim.lesen("smtp"):
                server.login(benutzer, passwort)
            server.send_message(msg)
    except (smtplib.SMTPException, OSError) as e:
        raise KassenFehler(f"E-Mail-Versand fehlgeschlagen: {e}") from e


def dokument_text(con: sqlite3.Connection, typ: str, nummer: str) -> tuple[str, str]:
    firma = einstellung(con, "firma_name", "") or ""
    betreff = f"{typ} {nummer}" + (f" – {firma}" if firma else "")
    vorlage = einstellung(con, "mail_text") or (
        "Sehr geehrte Damen und Herren,\n\nim Anhang erhalten Sie {typ} {nummer}.\n\n"
        "Mit freundlichen Grüßen\n{firma}")
    text = vorlage.format(typ=typ, nummer=nummer, firma=firma)
    from .hersteller import WERBUNG_MAIL, werbung_aktiv

    if werbung_aktiv(con, "mail"):
        text += f"\n\n-- \n{WERBUNG_MAIL}"
    return betreff, text
