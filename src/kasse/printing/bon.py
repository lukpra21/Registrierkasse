"""Bondruck (80 mm, ESC/POS) über USB.

Windows: Am einfachsten über den installierten Windows-Druckertreiber
(``Win32Raw`` mit dem Druckernamen). Alternativ direkt per USB
(``Usb`` mit Vendor-/Product-ID, benötigt libusb bzw. WinUSB-Treiber).
"""

from __future__ import annotations

import sqlite3

from ..db import einstellung
from ..geld import anzeige
from ..rksv.krypto import maschinenlesbarer_code

BREITE = 42  # Zeichen bei Font A auf 80-mm-Papier

BELEG_TITEL = {
    "Barumsatz": "RECHNUNG",
    "Storno": "STORNO",
    "Training": "TRAININGSBELEG",
    "Startbeleg": "STARTBELEG",
    "Nullbeleg": "NULLBELEG",
    "Monatsbeleg": "MONATSBELEG",
    "Jahresbeleg": "JAHRESBELEG",
    "Sammelbeleg": "SAMMELBELEG",
    "Schlussbeleg": "SCHLUSSBELEG",
}


def drucker_aus_einstellungen(con: sqlite3.Connection):
    from escpos import printer

    art = einstellung(con, "bondrucker_art", "windows")
    if art == "windows":
        return printer.Win32Raw(einstellung(con, "bondrucker_name"))
    if art == "usb":
        return printer.Usb(
            int(einstellung(con, "bondrucker_vendor", "0"), 16),
            int(einstellung(con, "bondrucker_product", "0"), 16),
        )
    if art == "datei":
        return printer.File(einstellung(con, "bondrucker_datei", "bon.bin"))
    raise ValueError(f"Unbekannte Bondrucker-Art: {art}")


def _zeile(links: str, rechts: str) -> str:
    platz = BREITE - len(rechts) - 1
    return f"{links[:platz]:<{platz}} {rechts}\n"


def bon_text(con: sqlite3.Connection, beleg_id: int) -> list[str]:
    """Textzeilen des Bons (ohne QR-Code) – auch für Vorschau/Tests nutzbar."""
    b = con.execute("SELECT * FROM belege WHERE id = ?", (beleg_id,)).fetchone()
    e = lambda k: einstellung(con, k, "") or ""  # noqa: E731
    z: list[str] = []
    for k in ("firma_name", "firma_adresse"):
        z += [l + "\n" for l in e(k).splitlines() if l]
    if e("firma_uid"):
        z.append(f"UID: {e('firma_uid')}\n")
    z.append("-" * BREITE + "\n")
    z.append(f"{BELEG_TITEL.get(b['art'], b['art'])}\n")
    z.append(_zeile(f"Beleg-Nr. {b['belegnummer']}", b["zeitpunkt"].replace("T", " ")))
    z.append(f"Kasse: {e('kassen_id')}\n")
    z.append("-" * BREITE + "\n")

    steuern: dict[str, int] = {}
    for p in con.execute("SELECT * FROM belegpositionen WHERE beleg_id = ? ORDER BY pos", (beleg_id,)):
        z.append(_zeile(p["bezeichnung"], anzeige(p["summe_cent"])))
        if p["menge"] not in ("1", "-1"):
            z.append(f"  {p['menge']} x {anzeige(p['einzelpreis_cent'])}\n")
        steuern[p["steuer_prozent"]] = steuern.get(p["steuer_prozent"], 0) + p["summe_cent"]

    summe = sum(steuern.values())
    z.append("=" * BREITE + "\n")
    z.append(_zeile("SUMME EUR", anzeige(summe)))
    if b["zahlungsart"]:
        z.append(_zeile(f"Bezahlt: {b['zahlungsart']}", anzeige(summe)))
    if steuern:
        z.append("\n")
        z.append(_zeile("USt-Satz      Netto      USt", "Brutto"))
        from ..geld import netto_aus_brutto

        for satz, brutto in sorted(steuern.items(), key=lambda kv: -float(kv[0])):
            netto = netto_aus_brutto(brutto, satz)
            z.append(_zeile(f"{satz:>3} %  {anzeige(netto):>10} {anzeige(brutto - netto):>8}", anzeige(brutto)))
    if b["ausfall"]:
        z.append("\nSicherheitseinrichtung ausgefallen\n")
    if b["art"] == "Training":
        z.append("\n*** TRAININGSBUCHUNG – KEIN UMSATZ ***\n")
    if e("bon_fusszeile"):
        z.append("\n" + e("bon_fusszeile") + "\n")
    return z


def drucke_bon(con: sqlite3.Connection, beleg_id: int, drucker=None) -> None:
    p = drucker or drucker_aus_einstellungen(con)
    jws = con.execute("SELECT jws FROM belege WHERE id = ?", (beleg_id,)).fetchone()["jws"]
    p.set(align="left")
    for zeile in bon_text(con, beleg_id):
        p.text(zeile)
    p.set(align="center")
    p.qr(maschinenlesbarer_code(jws), size=4, native=False)
    p.cut()
