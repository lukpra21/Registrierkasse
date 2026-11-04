"""Bondruck (ESC/POS) über USB – Papierbreite, Zeichen pro Zeile, Schrift, Druckerprofil,
QR-Größe, Vorschub und Abschnitt sind einstellbar (siehe ``layout.bon_layout``).

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

BREITE = 42  # Standard: Zeichen bei Font A auf 80-mm-Papier (einstellbar: bon_zeichen)

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

    from .layout import bon_layout

    L = bon_layout(con)
    profil = None if L.profil in ("", "default") else L.profil
    art = "windows" if name else einstellung(con, "bondrucker_art", "windows")
    if art == "windows":
        name = name or einstellung(con, "bondrucker_name")
        if not name:
            raise OSError("Kein Bondrucker eingestellt")
        p = printer.Win32Raw(name, profile=profil)
    elif art == "usb":
        p = printer.Usb(
            int(einstellung(con, "bondrucker_vendor", "0"), 16),
            int(einstellung(con, "bondrucker_product", "0"), 16),
            profile=profil,
        )
    elif art == "datei":
        p = printer.File(einstellung(con, "bondrucker_datei", "bon.bin"), profile=profil)
    else:
        raise ValueError(f"Unbekannte Bondrucker-Art: {art}")
    _breite_setzen(p, L.breite_px)
    return p


def _breite_setzen(p, pixel: int) -> None:
    """Bedruckbare Breite im Druckerprofil setzen (für Zentrierung von Logo und QR-Code)."""
    try:
        p.profile.profile_data.setdefault("media", {}).setdefault("width", {})["pixels"] = pixel
    except Exception:
        pass


def _zeile(links: str, rechts: str, breite: int = BREITE) -> str:
    platz = breite - len(rechts) - 1
    return f"{links[:platz]:<{platz}} {rechts}\n"


def _umbrechen(text: str, breite: int) -> list[str]:
    import textwrap

    zeilen = []
    for absatz in text.splitlines() or [""]:
        zeilen += textwrap.wrap(absatz, breite) or [""]
    return zeilen


def bon_kopf(con: sqlite3.Connection, breite: int) -> list[str]:
    """Kopfbereich (Firma, Adresse, UID, Kopftext) – wird zentriert gedruckt, wenn eingestellt."""
    e = lambda k: einstellung(con, k, "") or ""  # noqa: E731
    z = []
    for k in ("firma_name", "firma_adresse"):
        z += [zeile for zeile in e(k).splitlines() if zeile]
    if e("firma_uid"):
        z.append(f"UID: {e('firma_uid')}")
    if e("bon_kopftext"):
        z += _umbrechen(e("bon_kopftext"), breite)
    return [zeile[:breite] + "\n" for zeile in z]


def bon_text(con: sqlite3.Connection, beleg_id: int, breite: int | None = None, mit_kopf: bool = True) -> list[str]:
    """Textzeilen des Bons (ohne QR-Code) – auch für Vorschau/Tests nutzbar."""
    from .layout import bon_layout

    BREITE = breite or bon_layout(con).zeichen  # noqa: N806 – lokale Zeilenbreite
    _z = _zeile

    def _zeile_(links, rechts):  # noqa: E306
        return _z(links, rechts, BREITE)

    b = con.execute("SELECT * FROM belege WHERE id = ?", (beleg_id,)).fetchone()
    e = lambda k: einstellung(con, k, "") or ""  # noqa: E731
    z: list[str] = bon_kopf(con, BREITE) if mit_kopf else []
    z.append("-" * BREITE + "\n")
    z.append(f"{BELEG_TITEL.get(b['art'], b['art'])}\n")
    z.append(_zeile_(f"Beleg-Nr. {b['belegnummer']}", b["zeitpunkt"].replace("T", " ")))
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
        z.append(_zeile_(p["bezeichnung"], anzeige(p["summe_cent"] + p["rabatt_cent"])))
        if p["menge"] not in ("1", "-1"):
            z.append(f"  {p['menge']} x {anzeige(p['einzelpreis_cent'])}\n")
        if p["rabatt_cent"]:
            z.append(_zeile_("  Rabatt", anzeige(-p["rabatt_cent"])))
        summen.append(p["summe_cent"])
        if _ist_gutschein(p["bezeichnung"]):
            gutschein = True
            continue  # Gutscheine sind kein steuerbarer Umsatz – nicht in der USt-Aufstellung
        steuern[p["steuer_prozent"]] = steuern.get(p["steuer_prozent"], 0) + p["summe_cent"]

    summe = sum(summen)
    z.append("=" * BREITE + "\n")
    z.append(_zeile_("SUMME EUR", anzeige(summe)))
    zahlungen = con.execute("SELECT art, betrag_cent FROM zahlungen WHERE beleg_id = ?", (beleg_id,)).fetchall()
    for zl in zahlungen:
        z.append(_zeile_(f"Bezahlt: {zl['art']}", anzeige(zl["betrag_cent"])))
    if not zahlungen and b["zahlungsart"] and summe:
        z.append(_zeile_(f"Bezahlt: {b['zahlungsart']}", anzeige(summe)))
    if steuern:
        z.append("\n")
        from ..geld import netto_aus_brutto

        # Spaltenbreiten an die Zeilenbreite anpassen (58 mm: 32 Zeichen, 80 mm: 42/48)
        sp = max(7, (BREITE - 6) // 3)
        rest = BREITE - 6 - 3 * sp
        z.append(f"{'Satz':<6}{'Netto':>{sp}}{'USt':>{sp}}{'Brutto':>{sp + rest}}\n")
        for satz, brutto in sorted(steuern.items(), key=lambda kv: -float(kv[0])):
            netto = netto_aus_brutto(brutto, satz)
            z.append(f"{satz + ' %':<6}{anzeige(netto):>{sp}}{anzeige(brutto - netto):>{sp}}{anzeige(brutto):>{sp + rest}}\n")
    if gutschein:
        z.append("Wertgutschein: keine USt (Mehrzweckgutschein)\n")
    if b["ausfall"]:
        z.append("\nSicherheitseinrichtung ausgefallen\n")
    if b["art"] == "Training":
        z.append("\n*** TRAININGSBUCHUNG – KEIN UMSATZ ***\n")
    if e("bon_fusszeile"):
        z.append("\n" + "\n".join(_umbrechen(e("bon_fusszeile"), BREITE)) + "\n")
    return z


def drucke_bon(con: sqlite3.Connection, beleg_id: int, drucker=None, drucker_name: str | None = None) -> None:
    from .layout import bon_layout

    L = bon_layout(con)
    p = drucker or drucker_aus_einstellungen(con, drucker_name)
    if drucker is not None:
        _breite_setzen(p, L.breite_px)
    jws = con.execute("SELECT jws FROM belege WHERE id = ?", (beleg_id,)).fetchone()["jws"]
    logo = einstellung(con, "firma_logo")
    if logo and einstellung(con, "bon_logo") == "1":
        try:
            import base64
            import io

            from PIL import Image

            bild = Image.open(io.BytesIO(base64.b64decode(logo.split(",", 1)[1]))).convert("L")
            bild.thumbnail((min(384, L.breite_px), 160))
            p.set(align="center")
            p.image(bild, center=True)
        except Exception:
            pass  # Logo ist optional
    p.set(align="center" if L.kopf_zentriert else "left", font=L.schrift)
    for zeile in bon_kopf(con, L.zeichen):
        p.text(zeile)
    p.set(align="left", font=L.schrift)
    for zeile in bon_text(con, beleg_id, L.zeichen, mit_kopf=False):
        p.text(zeile)
    p.set(align="center")
    p.qr(maschinenlesbarer_code(jws), size=L.qr_groesse, native=False, center=True)
    if werbung := bon_werbung(con):
        p.set(align="center", font="b")
        p.text(werbung + "\n")
    p.set(align="left")
    if L.vorschub:
        p.text("\n" * L.vorschub)
    if L.schnitt != "kein":
        p.cut(mode="PART" if L.schnitt == "teil" else "FULL", feed=False)


def bon_werbung(con: sqlite3.Connection) -> str:
    """Herstellerhinweis unter dem QR-Code (abschaltbar: Einstellungen → Über)."""
    from ..hersteller import WERBUNG_BON, werbung_aktiv

    return WERBUNG_BON if werbung_aktiv(con, "bon") else ""


def kassenlade_oeffnen(con: sqlite3.Connection, drucker=None) -> None:
    """Öffnet die am Bondrucker angeschlossene Kassenlade (ESC/POS-Impuls an Pin 2, notfalls Pin 5)."""
    p = drucker or drucker_aus_einstellungen(con)
    pin = int(einstellung(con, "kassenlade_pin", "2") or 2)
    p.cashdraw(pin)
