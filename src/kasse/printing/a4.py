"""A4-Lieferschein und -Rechnung als PDF (reportlab), Druck über den Windows-Standarddrucker."""

from __future__ import annotations

import os
import sqlite3
import sys
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

from ..db import einstellung
from ..geld import anzeige, netto_aus_brutto
from ..rksv.krypto import maschinenlesbarer_code


def dokument_pdf(con: sqlite3.Connection, dok_id: int, ziel: Path | str) -> Path:
    from reportlab.graphics.barcode.qr import QrCodeWidget
    from reportlab.graphics.shapes import Drawing
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    d = con.execute("SELECT * FROM dokumente WHERE id = ?", (dok_id,)).fetchone()
    k = con.execute("SELECT * FROM kunden WHERE id = ?", (d["kunde_id"],)).fetchone()
    e = lambda s: (einstellung(con, s, "") or "")  # noqa: E731
    ist_rechnung = d["typ"] == "Rechnung"
    st = getSampleStyleSheet()
    klein = st["Normal"].clone("klein", fontSize=8, leading=10)

    elemente = []
    absender = " · ".join(filter(None, [e("firma_name"), *e("firma_adresse").splitlines()]))
    elemente.append(Paragraph(absender, klein))
    elemente.append(Spacer(1, 4 * mm))
    empf = [k["name"], *(k["adresse"] or "").splitlines()]
    if k["uid"]:
        empf.append(f"UID: {k['uid']}")
    elemente.append(Paragraph("<br/>".join(empf), st["Normal"]))
    elemente.append(Spacer(1, 10 * mm))
    elemente.append(Paragraph(f"{d['typ']} {d['nummer']}", st["Heading1"]))
    kopf = [f"Datum: {d['datum']}"]
    if k["kundennummer"]:
        kopf.append(f"Kundennummer: {k['kundennummer']}")
    if ist_rechnung:
        kopf.append(f"Leistungsdatum: {d['datum']}")
    elemente.append(Paragraph(" &nbsp;&nbsp; ".join(kopf), st["Normal"]))
    elemente.append(Spacer(1, 6 * mm))

    zeilen = [["Pos", "Bezeichnung", "Menge", "Einh.", "USt", "Einzel €", "Gesamt €"]]
    steuern: dict[str, int] = {}
    gesamt = 0
    for r in con.execute("SELECT * FROM dokumentpositionen WHERE dokument_id = ? ORDER BY pos", (dok_id,)):
        summe = int((Decimal(r["menge"]) * r["einzelpreis_cent"]).quantize(Decimal("1"), ROUND_HALF_UP))
        gesamt += summe
        steuern[r["steuer_prozent"]] = steuern.get(r["steuer_prozent"], 0) + summe
        zeilen.append([
            str(r["pos"]), Paragraph(r["bezeichnung"], klein), r["menge"], r["einheit"], f"{r['steuer_prozent']} %",
            anzeige(r["einzelpreis_cent"]) if ist_rechnung else "", anzeige(summe) if ist_rechnung else "",
        ])
    if not ist_rechnung:
        zeilen = [z[:5] for z in zeilen]
        breiten = [12 * mm, 100 * mm, 20 * mm, 15 * mm, 15 * mm]
    else:
        breiten = [12 * mm, 72 * mm, 18 * mm, 14 * mm, 14 * mm, 22 * mm, 24 * mm]
    t = Table(zeilen, colWidths=breiten, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eef2f7")),
        ("LINEBELOW", (0, 0), (-1, 0), 0.5, colors.grey),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    elemente.append(t)

    if ist_rechnung:
        elemente.append(Spacer(1, 4 * mm))
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
        elemente.append(s)
        elemente.append(Spacer(1, 6 * mm))
        if d["zahlungsart"] in ("Überweisung", None):
            text = f"Zahlbar innerhalb von {k['zahlungsziel_tage']} Tagen ohne Abzug."
            if e("firma_iban"):
                text += f" IBAN: {e('firma_iban')}"
                if e("firma_bic"):
                    text += f", BIC: {e('firma_bic')}"
        else:
            text = f"Betrag dankend erhalten ({d['zahlungsart']})."
        elemente.append(Paragraph(text, st["Normal"]))
        if gesamt > 1_000_000 and not k["uid"]:
            elemente.append(Paragraph("<b>Hinweis:</b> Bei Beträgen über 10.000 € ist die UID des Empfängers anzugeben.", klein))
        if d["beleg_id"]:
            b = con.execute("SELECT belegnummer, jws FROM belege WHERE id = ?", (d["beleg_id"],)).fetchone()
            qr = QrCodeWidget(maschinenlesbarer_code(b["jws"]))
            x1, y1, x2, y2 = qr.getBounds()
            groesse = 30 * mm
            zeichnung = Drawing(groesse, groesse, transform=[groesse / (x2 - x1), 0, 0, groesse / (y2 - y1), 0, 0])
            zeichnung.add(qr)
            elemente.append(Spacer(1, 4 * mm))
            elemente.append(Paragraph(f"Kassenbeleg Nr. {b['belegnummer']} (Kasse {e('kassen_id')})", klein))
            elemente.append(zeichnung)
    else:
        elemente.append(Spacer(1, 20 * mm))
        elemente.append(Paragraph("Ware erhalten: ______________________________", st["Normal"]))

    def fuss(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 7)
        teile = [e("firma_name"), e("firma_uid") and f"UID {e('firma_uid')}", e("firma_fn") and f"FN {e('firma_fn')}",
                 e("firma_iban") and f"IBAN {e('firma_iban')}"]
        canvas.drawCentredString(A4[0] / 2, 12 * mm, " · ".join(filter(None, teile)))
        canvas.restoreState()

    ziel = Path(ziel)
    SimpleDocTemplate(str(ziel), pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm,
                      topMargin=20 * mm, bottomMargin=20 * mm, title=f"{d['typ']} {d['nummer']}").build(
        elemente, onFirstPage=fuss, onLaterPages=fuss)
    return ziel


def drucke_pdf(pfad: Path | str) -> None:
    """Druckt ein PDF auf dem Windows-Standarddrucker (A4)."""
    if sys.platform != "win32":
        raise OSError("Direktdruck nur unter Windows – PDF bitte manuell drucken")
    os.startfile(str(pfad), "print")  # type: ignore[attr-defined]
