"""Einstellbare Druckvorlagen: Briefpapier (A4) und Bondrucker-Papier.

Alle Werte liegen als Einstellungen in der Kassendatenbank; fehlende Werte
werden durch die Standardwerte ersetzt. Die Oberfläche (Einstellungen →
Briefpapier / Bondrucker-Papier) schreibt genau diese Schlüssel.
"""

from __future__ import annotations

import base64
import re
import sqlite3
from dataclasses import dataclass

from ..db import einstellung

# --------------------------------------------------------------------------- A4 / Briefpapier

A4_STANDARD = {
    "a4_rand_oben": "20",
    "a4_rand_unten": "22",
    "a4_rand_links": "20",
    "a4_rand_rechts": "20",
    "a4_adresse_oben": "45",     # mm vom oberen Blattrand (Fensterkuvert DIN 5008 Form B: 45)
    "a4_adresse_links": "20",    # mm vom linken Blattrand
    "a4_inhalt_oben": "95",      # mm vom oberen Blattrand: Beginn von Titel/Positionen auf Seite 1
    "a4_logo_position": "rechts",  # rechts | links | mitte | aus
    "a4_logo_breite": "50",      # mm (maximal)
    "a4_logo_oben": "12",        # mm vom oberen Blattrand
    "a4_absender_zeile": "1",    # kleine Absenderzeile über der Anschrift
    "a4_fusszeile_anzeigen": "1",
    "a4_fusszeile": "",          # leer = automatisch aus Firmendaten
    "a4_schrift": "Helvetica",   # Helvetica | Times-Roman | Courier
    "a4_schriftgroesse": "10",
    "a4_tabellenfarbe": "#eef2f7",
    "a4_text_rechnung_einleitung": "",
    "a4_text_rechnung_schluss": "Vielen Dank für Ihren Auftrag!",
    "a4_text_lieferschein_einleitung": "",
    "a4_text_lieferschein_schluss": "",
}

A4_GRENZEN = {  # (min, max) für Zahlenwerte
    "a4_rand_oben": (0, 80), "a4_rand_unten": (0, 80), "a4_rand_links": (0, 60), "a4_rand_rechts": (0, 60),
    "a4_adresse_oben": (10, 120), "a4_adresse_links": (5, 120), "a4_inhalt_oben": (20, 200),
    "a4_logo_breite": (10, 120), "a4_logo_oben": (0, 80), "a4_schriftgroesse": (7, 14),
}

SCHRIFTEN = {"Helvetica": ("Helvetica", "Helvetica-Bold"), "Times-Roman": ("Times-Roman", "Times-Bold"),
             "Courier": ("Courier", "Courier-Bold")}

# Briefpapier-Hintergründe (data:-URLs) – getrennt gespeichert, da groß
BRIEFPAPIER_SCHLUESSEL = ("a4_briefpapier_erste", "a4_briefpapier_folge")
BRIEFPAPIER_MAX_BYTES = 5_000_000


@dataclass
class A4Layout:
    rand_oben: float
    rand_unten: float
    rand_links: float
    rand_rechts: float
    adresse_oben: float
    adresse_links: float
    inhalt_oben: float
    logo_position: str
    logo_breite: float
    logo_oben: float
    absender_zeile: bool
    fusszeile_anzeigen: bool
    fusszeile: str
    schrift: str
    schrift_fett: str
    schriftgroesse: float
    tabellenfarbe: str
    texte: dict[str, str]
    briefpapier_erste: bytes | None
    briefpapier_erste_typ: str | None
    briefpapier_folge: bytes | None
    briefpapier_folge_typ: str | None


def _zahl(con, k: str, standard: dict, grenzen: dict) -> float:
    try:
        v = float(str(einstellung(con, k, "") or standard[k]).replace(",", "."))
    except ValueError:
        v = float(standard[k])
    lo, hi = grenzen.get(k, (float("-inf"), float("inf")))
    return min(max(v, lo), hi)


def data_url_lesen(data_url: str | None) -> tuple[bytes | None, str | None]:
    """data:<typ>;base64,<daten> → (Bytes, 'pdf' | 'png' | 'jpeg')"""
    if not data_url:
        return None, None
    m = re.fullmatch(r"data:(application/pdf|image/png|image/jpeg);base64,([A-Za-z0-9+/=\s]+)", data_url)
    if not m:
        return None, None
    return base64.b64decode(m.group(2)), m.group(1).split("/")[1]


def a4_layout(con: sqlite3.Connection) -> A4Layout:
    z = lambda k: _zahl(con, k, A4_STANDARD, A4_GRENZEN)  # noqa: E731
    t = lambda k: (einstellung(con, k, None) if einstellung(con, k, None) is not None else A4_STANDARD[k])  # noqa: E731
    schrift = t("a4_schrift") if t("a4_schrift") in SCHRIFTEN else "Helvetica"
    farbe = t("a4_tabellenfarbe")
    erste, erste_typ = data_url_lesen(einstellung(con, "a4_briefpapier_erste"))
    folge, folge_typ = data_url_lesen(einstellung(con, "a4_briefpapier_folge"))
    return A4Layout(
        z("a4_rand_oben"), z("a4_rand_unten"), z("a4_rand_links"), z("a4_rand_rechts"),
        z("a4_adresse_oben"), z("a4_adresse_links"), z("a4_inhalt_oben"),
        t("a4_logo_position") if t("a4_logo_position") in ("rechts", "links", "mitte", "aus") else "rechts",
        z("a4_logo_breite"), z("a4_logo_oben"),
        t("a4_absender_zeile") != "0", t("a4_fusszeile_anzeigen") != "0", t("a4_fusszeile"),
        SCHRIFTEN[schrift][0], SCHRIFTEN[schrift][1], z("a4_schriftgroesse"),
        farbe if re.fullmatch(r"#[0-9a-fA-F]{6}", farbe or "") else "#eef2f7",
        {k: t(k) for k in A4_STANDARD if k.startswith("a4_text_")},
        erste, erste_typ, folge, folge_typ,
    )


# --------------------------------------------------------------------------- Bon / Bondrucker-Papier

BON_STANDARD = {
    "bon_papierbreite": "80",    # mm: 80 | 58
    "bon_zeichen": "42",         # Zeichen pro Zeile (80 mm: 42 bzw. 48, 58 mm: 32)
    "bon_breite_px": "512",      # bedruckbare Breite in Punkten (80 mm: 512/576, 58 mm: 384)
    "bon_schrift": "a",          # a (groß) | b (klein, mehr Zeichen)
    "bon_profil": "default",     # Druckerprofil (python-escpos) – wichtig für Umlaute/€
    "bon_kopftext": "",          # zusätzliche Zeilen unter der Firmenadresse
    "bon_kopf_zentriert": "1",
    "bon_qr_groesse": "4",       # 1–16
    "bon_vorschub": "3",         # Leerzeilen vor dem Abschnitt
    "bon_schnitt": "teil",       # voll | teil | kein
}

BON_GRENZEN = {"bon_zeichen": (24, 64), "bon_breite_px": (200, 640), "bon_qr_groesse": (1, 16),
               "bon_vorschub": (0, 10), "bon_papierbreite": (40, 112)}

#: gängige Druckerprofile aus python-escpos (Auswahl für die Oberfläche)
BON_PROFILE = ["default", "simple", "TM-T88II", "TM-T88III", "TM-T88IV", "TM-T88V", "TM-T20", "TM-T20II",
               "TM-U220", "TM-P80", "POS-5890", "POS-58", "NT-80-V-UL", "RP-F10-80mm", "TSP600", "TUP500"]


@dataclass
class BonLayout:
    papierbreite: int
    zeichen: int
    breite_px: int
    schrift: str
    profil: str
    kopftext: str
    kopf_zentriert: bool
    qr_groesse: int
    vorschub: int
    schnitt: str


def bon_layout(con: sqlite3.Connection) -> BonLayout:
    z = lambda k: int(_zahl(con, k, BON_STANDARD, BON_GRENZEN))  # noqa: E731
    t = lambda k: einstellung(con, k, "") or BON_STANDARD[k]  # noqa: E731
    return BonLayout(
        z("bon_papierbreite"), z("bon_zeichen"), z("bon_breite_px"),
        t("bon_schrift") if t("bon_schrift") in ("a", "b") else "a",
        t("bon_profil"), einstellung(con, "bon_kopftext", "") or "", t("bon_kopf_zentriert") != "0",
        z("bon_qr_groesse"), z("bon_vorschub"),
        t("bon_schnitt") if t("bon_schnitt") in ("voll", "teil", "kein") else "teil",
    )


ALLE_STANDARDS = {**A4_STANDARD, **BON_STANDARD}
