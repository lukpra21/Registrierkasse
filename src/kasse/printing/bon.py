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


def _ist_gutschein(bezeichnung: str) -> bool:
    return bezeichnung.startswith("Wertgutschein ") or (
        bezeichnung.startswith("Gutschein ") and bezeichnung.endswith(" eingelöst"))

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


def drucker_aus_einstellungen(con: sqlite3.Connection, name: str | None = None):
    """Bondrucker laut Einstellungen; ``name`` wählt einen anderen installierten Windows-Drucker."""
    from escpos import printer

    art = "windows" if name else einstellung(con, "bondrucker_art", "windows")
    if art == "windows":
        name = name or einstellung(con, "bondrucker_name")
        if not name:
            raise OSError("Kein Bondrucker eingestellt")
        return printer.Win32Raw(name)
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
    if b["benutzer_id"]:
        name = con.execute("SELECT name FROM benutzer WHERE id = ?", (b["benutzer_id"],)).fetchone()
        if name:
            z.append(f"Es bediente Sie: {name[0]}\n")
    z.append("-" * BREITE + "\n")

    steuern: dict[str, int] = {}
    summen: list[int] = []
    gutschein = False
    for p in con.execute("SELECT * FROM belegpositionen WHERE beleg_id = ? ORDER BY pos", (beleg_id,)):
        z.append(_zeile(p["bezeichnung"], anzeige(p["summe_cent"] + p["rabatt_cent"])))
        if p["menge"] not in ("1", "-1"):
            z.append(f"  {p['menge']} x {anzeige(p['einzelpreis_cent'])}\n")
        if p["rabatt_cent"]:
            z.append(_zeile("  Rabatt", anzeige(-p["rabatt_cent"])))
        summen.append(p["summe_cent"])
        if _ist_gutschein(p["bezeichnung"]):
            gutschein = True
            continue  # Gutscheine sind kein steuerbarer Umsatz – nicht in der USt-Aufstellung
        steuern[p["steuer_prozent"]] = steuern.get(p["steuer_prozent"], 0) + p["summe_cent"]

    summe = sum(summen)
    z.append("=" * BREITE + "\n")
    z.append(_zeile("SUMME EUR", anzeige(summe)))
    zahlungen = con.execute("SELECT art, betrag_cent FROM zahlungen WHERE beleg_id = ?", (beleg_id,)).fetchall()
    for zl in zahlungen:
        z.append(_zeile(f"Bezahlt: {zl['art']}", anzeige(zl["betrag_cent"])))
    if not zahlungen and b["zahlungsart"] and summe:
        z.append(_zeile(f"Bezahlt: {b['zahlungsart']}", anzeige(summe)))
    if steuern:
        z.append("\n")
        z.append(_zeile("USt-Satz      Netto      USt", "Brutto"))
        from ..geld import netto_aus_brutto

        for satz, brutto in sorted(steuern.items(), key=lambda kv: -float(kv[0])):
            netto = netto_aus_brutto(brutto, satz)
            z.append(_zeile(f"{satz:>3} %  {anzeige(netto):>10} {anzeige(brutto - netto):>8}", anzeige(brutto)))
    if gutschein:
        z.append("Wertgutschein: keine USt (Mehrzweckgutschein)\n")
    if b["ausfall"]:
        z.append("\nSicherheitseinrichtung ausgefallen\n")
    if b["art"] == "Training":
        z.append("\n*** TRAININGSBUCHUNG – KEIN UMSATZ ***\n")
    if e("bon_fusszeile"):
        z.append("\n" + e("bon_fusszeile") + "\n")
    return z


def drucke_bon(con: sqlite3.Connection, beleg_id: int, drucker=None, drucker_name: str | None = None) -> None:
    p = drucker or drucker_aus_einstellungen(con, drucker_name)
    jws = con.execute("SELECT jws FROM belege WHERE id = ?", (beleg_id,)).fetchone()["jws"]
    logo = einstellung(con, "firma_logo")
    if logo and einstellung(con, "bon_logo") == "1":
        try:
            import base64
            import io

            from PIL import Image

            bild = Image.open(io.BytesIO(base64.b64decode(logo.split(",", 1)[1]))).convert("L")
            bild.thumbnail((384, 160))
            p.set(align="center")
            p.image(bild, center=True)
        except Exception:
            pass  # Logo ist optional
    p.set(align="left")
    for zeile in bon_text(con, beleg_id):
        p.text(zeile)
    p.set(align="center")
    p.qr(maschinenlesbarer_code(jws), size=4, native=False)
    p.cut()


def kassenlade_oeffnen(con: sqlite3.Connection, drucker=None) -> None:
    """Öffnet die am Bondrucker angeschlossene Kassenlade (ESC/POS-Impuls an Pin 2, notfalls Pin 5)."""
    p = drucker or drucker_aus_einstellungen(con)
    pin = int(einstellung(con, "kassenlade_pin", "2") or 2)
    p.cashdraw(pin)
