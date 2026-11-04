"""A4-Ausgabe als PDF (reportlab): Lieferschein, Rechnung und Kassenbeleg.

Gedruckt wird auf einem frei wählbaren installierten Windows-Drucker
(siehe :func:`drucke_pdf`).
"""

from __future__ import annotations

import os
import shutil
import sqlite3
import subprocess
import sys
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

from ..db import einstellung
from ..geld import anzeige, netto_aus_brutto
from ..rksv.krypto import maschinenlesbarer_code
from .bon import BELEG_TITEL


@dataclass
class A4Daten:
    titel: str
    kopfzeilen: list[str]
    empfaenger: list[str] | None
    # (Pos, Bezeichnung, Menge, Einheit, USt-Satz, Einzelpreis Cent, Summe Cent)
    positionen: list[tuple[int, str, str, str, str, int, int]]
    mit_preisen: bool = True
    zahlungstext: str | None = None
    beleg_qr: tuple[str, str] | None = None  # (Inhalt, Beschriftung)
    epc_qr: str | None = None
    unterschrift: bool = False
    hinweise: list[str] = field(default_factory=list)


def _summe(menge: str, einzel: int) -> int:
    return int((Decimal(menge) * einzel).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def epc_qr_inhalt(name: str, iban: str, bic: str, betrag_cent: int, verwendungszweck: str) -> str:
    """EPC-/GiroCode für SEPA-Überweisungen (Banking-App scannt → Überweisung vorausgefüllt)."""
    return "\n".join([
        "BCD", "002", "1", "SCT", bic.replace(" ", ""), name[:70], iban.replace(" ", ""),
        f"EUR{betrag_cent // 100}.{betrag_cent % 100:02d}", "", "", verwendungszweck[:140],
    ])


def _render(con: sqlite3.Connection, daten: A4Daten, ziel: Path | str) -> Path:
    from reportlab.graphics.barcode.qr import QrCodeWidget
    from reportlab.graphics.shapes import Drawing
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    e = lambda s: (einstellung(con, s, "") or "")  # noqa: E731
    st = getSampleStyleSheet()
    klein = st["Normal"].clone("klein", fontSize=8, leading=10)

    def qr(inhalt: str, groesse=30 * mm) -> Drawing:
        w = QrCodeWidget(inhalt)
        x1, y1, x2, y2 = w.getBounds()
        d = Drawing(groesse, groesse, transform=[groesse / (x2 - x1), 0, 0, groesse / (y2 - y1), 0, 0])
        d.add(w)
        return d

    el = []
    absender = " · ".join(filter(None, [e("firma_name"), *e("firma_adresse").splitlines()]))
    el.append(Paragraph(absender, klein))
    el.append(Spacer(1, 4 * mm))
    if daten.empfaenger:
        el.append(Paragraph("<br/>".join(daten.empfaenger), st["Normal"]))
    el.append(Spacer(1, 10 * mm))
    el.append(Paragraph(daten.titel, st["Heading1"]))
    el.append(Paragraph(" &nbsp;&nbsp; ".join(daten.kopfzeilen), st["Normal"]))
    el.append(Spacer(1, 6 * mm))

    kopf = ["Pos", "Bezeichnung", "Menge", "Einh.", "USt"]
    if daten.mit_preisen:
        kopf += ["Einzel €", "Gesamt €"]
        breiten = [12 * mm, 72 * mm, 18 * mm, 14 * mm, 14 * mm, 22 * mm, 24 * mm]
    else:
        breiten = [12 * mm, 100 * mm, 20 * mm, 15 * mm, 15 * mm]
    zeilen = [kopf]
    steuern: dict[str, int] = {}
    gesamt = 0
    for pos, bez, menge, einheit, satz, einzel, summe in daten.positionen:
        gesamt += summe
        steuern[satz] = steuern.get(satz, 0) + summe
        z = [str(pos), Paragraph(bez, klein), menge, einheit, f"{satz} %"]
        if daten.mit_preisen:
            z += [anzeige(einzel), anzeige(summe)]
        zeilen.append(z)
    t = Table(zeilen, colWidths=breiten, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eef2f7")),
        ("LINEBELOW", (0, 0), (-1, 0), 0.5, colors.grey),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    el.append(t)

    if daten.mit_preisen:
        el.append(Spacer(1, 4 * mm))
        summen = []
        for satz, brutto in sorted(steuern.items(), key=lambda kv: -float(kv[0])):
            netto = netto_aus_brutto(brutto, satz)
            summen.append([f"Netto {satz} %", anzeige(netto)])
            summen.append([f"USt {satz} %", anzeige(brutto - netto)])
        summen.append(["Gesamtbetrag EUR", anzeige(gesamt)])
        s = Table(summen, colWidths=[50 * mm, 30 * mm], hAlign="RIGHT")
        s.setStyle(TableStyle([
            ("ALIGN", (1, 0), (1, -1), "RIGHT"),
            ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
            ("LINEABOVE", (0, -1), (-1, -1), 0.5, colors.black),
        ]))
        el.append(s)
        el.append(Spacer(1, 6 * mm))

    if daten.zahlungstext:
        el.append(Paragraph(daten.zahlungstext, st["Normal"]))
    for h in daten.hinweise:
        el.append(Paragraph(h, klein))

    qrs = []
    if daten.epc_qr:
        qrs.append((qr(daten.epc_qr), "Mit Banking-App scannen und bezahlen"))
    if daten.beleg_qr:
        qrs.append((qr(daten.beleg_qr[0]), daten.beleg_qr[1]))
    if qrs:
        el.append(Spacer(1, 4 * mm))
        q = Table([[x[0] for x in qrs], [Paragraph(x[1], klein) for x in qrs]], colWidths=[60 * mm] * len(qrs), hAlign="LEFT")
        el.append(q)

    if daten.unterschrift:
        el.append(Spacer(1, 20 * mm))
        el.append(Paragraph("Ware erhalten: ______________________________", st["Normal"]))

    logo = _logo_bild(e("firma_logo"))

    def fuss(canvas, doc):
        canvas.saveState()
        if logo is not None and doc.page == 1:
            from reportlab.lib.utils import ImageReader

            img = ImageReader(logo)
            b, h = img.getSize()
            max_b, max_h = 50 * mm, 22 * mm
            f = min(max_b / b, max_h / h)
            canvas.drawImage(img, A4[0] - 20 * mm - b * f, A4[1] - 12 * mm - h * f, b * f, h * f, mask="auto")
        canvas.setFont("Helvetica", 7)
        teile = [e("firma_name"), e("firma_uid") and f"UID {e('firma_uid')}", e("firma_fn") and f"FN {e('firma_fn')}",
                 e("firma_iban") and f"IBAN {e('firma_iban')}"]
        canvas.drawCentredString(A4[0] / 2, 12 * mm, " · ".join(filter(None, teile)))
        canvas.restoreState()

    ziel = Path(ziel)
    SimpleDocTemplate(str(ziel), pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm,
                      topMargin=20 * mm, bottomMargin=20 * mm, title=daten.titel).build(
        el, onFirstPage=fuss, onLaterPages=fuss)
    return ziel


def _logo_bild(data_url: str | None):
    """Logo aus den Einstellungen (data:image/…;base64,…) als Datei-ähnliches Objekt."""
    import base64
    import io

    if not data_url or "," not in data_url:
        return None
    try:
        return io.BytesIO(base64.b64decode(data_url.split(",", 1)[1]))
    except ValueError:
        return None


def _empfaenger(k) -> list[str]:
    z = [k["name"], *(k["adresse"] or "").splitlines()]
    if k["uid"]:
        z.append(f"UID: {k['uid']}")
    return z


def dokument_pdf(con: sqlite3.Connection, dok_id: int, ziel: Path | str) -> Path:
    """Lieferschein oder Rechnung."""
    e = lambda s: (einstellung(con, s, "") or "")  # noqa: E731
    d = con.execute("SELECT * FROM dokumente WHERE id = ?", (dok_id,)).fetchone()
    k = con.execute("SELECT * FROM kunden WHERE id = ?", (d["kunde_id"],)).fetchone()
    ist_rechnung = d["typ"] == "Rechnung"

    pos = [(r["pos"], r["bezeichnung"], r["menge"], r["einheit"], r["steuer_prozent"], r["einzelpreis_cent"],
            _summe(r["menge"], r["einzelpreis_cent"]))
           for r in con.execute("SELECT * FROM dokumentpositionen WHERE dokument_id = ? ORDER BY pos", (dok_id,))]
    gesamt = sum(p[6] for p in pos)

    kopf = [f"Datum: {d['datum']}"]
    if k["kundennummer"]:
        kopf.append(f"Kundennummer: {k['kundennummer']}")
    if ist_rechnung:
        kopf.append(f"Leistungsdatum: {d['datum']}")

    daten = A4Daten(f"{d['typ']} {d['nummer']}", kopf, _empfaenger(k), pos, mit_preisen=ist_rechnung,
                    unterschrift=not ist_rechnung)
    if ist_rechnung:
        if d["zahlungsart"] in ("Überweisung", None):
            text = f"Zahlbar innerhalb von {k['zahlungsziel_tage']} Tagen ohne Abzug."
            if e("firma_iban"):
                text += f" IBAN: {e('firma_iban')}" + (f", BIC: {e('firma_bic')}" if e("firma_bic") else "")
                text += f", Verwendungszweck: {d['nummer']}"
                daten.epc_qr = epc_qr_inhalt(e("firma_name"), e("firma_iban"), e("firma_bic"), gesamt, d["nummer"])
            daten.zahlungstext = text
        else:
            daten.zahlungstext = f"Betrag dankend erhalten ({d['zahlungsart']})."
        if gesamt > 1_000_000 and not k["uid"]:
            daten.hinweise.append("<b>Hinweis:</b> Bei Beträgen über 10.000 € ist die UID des Empfängers anzugeben.")
        if d["beleg_id"]:
            b = con.execute("SELECT belegnummer, jws FROM belege WHERE id = ?", (d["beleg_id"],)).fetchone()
            daten.beleg_qr = (maschinenlesbarer_code(b["jws"]), f"Kassenbeleg Nr. {b['belegnummer']} (Kasse {e('kassen_id')})")
    return _render(con, daten, ziel)


def beleg_pdf(con: sqlite3.Connection, beleg_id: int, ziel: Path | str) -> Path:
    """Kassenbeleg (Bon) im A4-Format."""
    e = lambda s: (einstellung(con, s, "") or "")  # noqa: E731
    b = con.execute("SELECT * FROM belege WHERE id = ?", (beleg_id,)).fetchone()
    pos = [(r["pos"], r["bezeichnung"], r["menge"], "Stk", r["steuer_prozent"], r["einzelpreis_cent"], r["summe_cent"])
           for r in con.execute("SELECT * FROM belegpositionen WHERE beleg_id = ? ORDER BY pos", (beleg_id,))]
    empf = None
    if b["kunde_id"]:
        k = con.execute("SELECT * FROM kunden WHERE id = ?", (b["kunde_id"],)).fetchone()
        empf = _empfaenger(k)
    titel = f"{BELEG_TITEL.get(b['art'], b['art']).capitalize()} Nr. {b['belegnummer']}"
    daten = A4Daten(
        titel,
        [f"Datum: {b['zeitpunkt'].replace('T', ' ')}", f"Kasse: {e('kassen_id')}"],
        empf, pos,
        zahlungstext=f"Bezahlt: {b['zahlungsart']}" if b["zahlungsart"] else None,
        beleg_qr=(maschinenlesbarer_code(b["jws"]), "Signierter Kassenbeleg (RKSV)"),
    )
    if b["ausfall"]:
        daten.hinweise.append("Sicherheitseinrichtung ausgefallen")
    if b["art"] == "Training":
        daten.hinweise.append("<b>TRAININGSBUCHUNG – KEIN UMSATZ</b>")
    return _render(con, daten, ziel)


# --------------------------------------------------------------------------- Drucken


def _sumatra() -> str | None:
    """SumatraPDF (kostenlos) ermöglicht stilles Drucken auf einen bestimmten Drucker."""
    kandidaten = [
        os.environ.get("KASSE_SUMATRA"),
        shutil.which("SumatraPDF"),
        str(Path(os.environ.get("LOCALAPPDATA", "")) / "SumatraPDF" / "SumatraPDF.exe"),
        r"C:\Program Files\SumatraPDF\SumatraPDF.exe",
        str(Path(sys.executable).parent / "SumatraPDF.exe"),
    ]
    return next((k for k in kandidaten if k and Path(k).is_file()), None)


def drucke_pdf(pfad: Path | str, drucker: str | None = None) -> None:
    """Druckt ein PDF auf dem gewählten (oder Standard-)Drucker unter Windows."""
    if sys.platform != "win32":
        raise OSError("Direktdruck nur unter Windows – PDF bitte manuell drucken")
    pfad = str(pfad)
    if sumatra := _sumatra():
        befehl = [sumatra, "-silent", "-exit-when-done"]
        befehl += ["-print-to", drucker] if drucker else ["-print-to-default"]
        subprocess.run([*befehl, pfad], check=True, timeout=60)
        return
    if drucker:
        import win32api  # type: ignore[import-not-found]

        # "printto" wird von den meisten PDF-Programmen (z. B. Adobe Reader) unterstützt
        win32api.ShellExecute(0, "printto", pfad, f'"{drucker}"', ".", 0)
        return
    os.startfile(pfad, "print")  # type: ignore[attr-defined]
