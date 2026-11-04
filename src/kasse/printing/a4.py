"""A4-Ausgabe als PDF (reportlab): Lieferschein, Rechnung und Kassenbeleg.

Gedruckt wird auf einem frei wählbaren installierten Windows-Drucker
(siehe :func:`drucke_pdf`).
"""

from __future__ import annotations

import io
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
    einleitung: str = ""
    schluss: str = ""


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
    from reportlab.lib.utils import ImageReader
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    from .layout import a4_layout

    e = lambda s: (einstellung(con, s, "") or "")  # noqa: E731
    L = a4_layout(con)
    gr = L.schriftgroesse
    st = getSampleStyleSheet()
    normal = st["Normal"].clone("normal", fontName=L.schrift, fontSize=gr, leading=gr * 1.3)
    klein = normal.clone("klein", fontSize=gr - 2, leading=(gr - 2) * 1.25)
    titel_stil = st["Heading1"].clone("titel", fontName=L.schrift_fett, fontSize=gr + 8, leading=(gr + 8) * 1.2,
                                      spaceBefore=0)
    breite_nutz = A4[0] - (L.rand_links + L.rand_rechts) * mm

    def qr(inhalt: str, groesse=30 * mm) -> Drawing:
        w = QrCodeWidget(inhalt)
        x1, y1, x2, y2 = w.getBounds()
        d = Drawing(groesse, groesse, transform=[groesse / (x2 - x1), 0, 0, groesse / (y2 - y1), 0, 0])
        d.add(w)
        return d

    el = []
    # Seite 1: Anschrift wird absolut gezeichnet (Fensterkuvert); der Inhalt beginnt bei "inhalt_oben"
    el.append(Spacer(1, max(0.0, (L.inhalt_oben - L.rand_oben)) * mm))
    el.append(Paragraph(daten.titel, titel_stil))
    el.append(Paragraph(" &nbsp;&nbsp; ".join(daten.kopfzeilen), normal))
    el.append(Spacer(1, 5 * mm))
    if daten.einleitung:
        el.append(Paragraph(daten.einleitung.replace("\n", "<br/>"), normal))
        el.append(Spacer(1, 4 * mm))

    kopf = ["Pos", "Bezeichnung", "Menge", "Einh.", "USt"]
    if daten.mit_preisen:
        kopf += ["Einzel €", "Gesamt €"]
        feste = [12, 18, 14, 14, 22, 24]
    else:
        feste = [12, 20, 15, 15]
    bez_breite = max(40 * mm, breite_nutz - sum(feste) * mm)
    breiten = [feste[0] * mm, bez_breite] + [f * mm for f in feste[1:]]
    zeilen = [kopf]
    steuern: dict[str, int] = {}
    gesamt = 0
    for pos, bez, menge, einheit, satz, einzel, summe in daten.positionen:
        gesamt += summe
        steuern[satz] = steuern.get(satz, 0) + summe
        z = [str(pos), Paragraph(bez, klein), str(menge).replace(".", ","), einheit, f"{satz} %"]
        if daten.mit_preisen:
            z += [anzeige(einzel), anzeige(summe)]
        zeilen.append(z)
    t = Table(zeilen, colWidths=breiten, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(L.tabellenfarbe)),
        ("LINEBELOW", (0, 0), (-1, 0), 0.5, colors.grey),
        ("FONTNAME", (0, 0), (-1, -1), L.schrift),
        ("FONTNAME", (0, 0), (-1, 0), L.schrift_fett),
        ("FONTSIZE", (0, 0), (-1, -1), gr - 1),
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
            ("FONTNAME", (0, 0), (-1, -1), L.schrift),
            ("FONTSIZE", (0, 0), (-1, -1), gr),
            ("ALIGN", (1, 0), (1, -1), "RIGHT"),
            ("FONTNAME", (0, -1), (-1, -1), L.schrift_fett),
            ("LINEABOVE", (0, -1), (-1, -1), 0.5, colors.black),
        ]))
        el.append(s)
        el.append(Spacer(1, 6 * mm))

    if daten.zahlungstext:
        el.append(Paragraph(daten.zahlungstext, normal))
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

    if daten.schluss:
        el.append(Spacer(1, 6 * mm))
        el.append(Paragraph(daten.schluss.replace("\n", "<br/>"), normal))

    if daten.unterschrift:
        el.append(Spacer(1, 20 * mm))
        el.append(Paragraph("Ware erhalten: ______________________________", normal))

    logo = _logo_bild(e("firma_logo")) if L.logo_position != "aus" else None
    from ..hersteller import WERBUNG_A4, werbung_aktiv

    werbung = WERBUNG_A4 if werbung_aktiv(con, "a4") else ""
    hintergrund = {1: (L.briefpapier_erste, L.briefpapier_erste_typ),
                   2: (L.briefpapier_folge or L.briefpapier_erste, L.briefpapier_folge_typ or L.briefpapier_erste_typ)}

    def seite(canvas, doc):
        canvas.saveState()
        erste = doc.page == 1
        bild, typ = hintergrund[1 if erste else 2]
        if bild and typ in ("png", "jpeg"):  # Briefpapier als Bild: ganzseitig hinterlegen
            canvas.drawImage(ImageReader(io.BytesIO(bild)), 0, 0, A4[0], A4[1], preserveAspectRatio=False, mask="auto")
        if erste and logo is not None:
            img = ImageReader(logo)
            b, h = img.getSize()
            f = min(L.logo_breite * mm / b, 30 * mm / h)
            x = {"links": L.rand_links * mm, "mitte": (A4[0] - b * f) / 2}.get(L.logo_position, A4[0] - L.rand_rechts * mm - b * f)
            canvas.drawImage(img, x, A4[1] - L.logo_oben * mm - h * f, b * f, h * f, mask="auto")
        if erste:
            y = A4[1] - L.adresse_oben * mm
            x = L.adresse_links * mm
            if L.absender_zeile:
                absender = " · ".join(filter(None, [e("firma_name"), *e("firma_adresse").splitlines()]))
                canvas.setFont(L.schrift, 7)
                canvas.drawString(x, y, absender[:110])
                y -= 5 * mm
            canvas.setFont(L.schrift, gr)
            for zeile in daten.empfaenger or []:
                y -= gr * 1.3
                canvas.drawString(x, y, zeile)
        if L.fusszeile_anzeigen:
            canvas.setFont(L.schrift, 7)
            if L.fusszeile.strip():
                zeilen_fuss = L.fusszeile.strip().splitlines()
            else:
                teile = [e("firma_name"), e("firma_uid") and f"UID {e('firma_uid')}", e("firma_fn") and f"FN {e('firma_fn')}",
                         e("firma_iban") and f"IBAN {e('firma_iban')}"]
                zeilen_fuss = [" · ".join(filter(None, teile))]
            y = max(6 * mm, L.rand_unten * mm - 8 * mm) + (len(zeilen_fuss) - 1) * 9
            for zeile in zeilen_fuss:
                canvas.drawCentredString(A4[0] / 2, y, zeile)
                y -= 9
        canvas.setFont(L.schrift, 7)
        unten = max(6 * mm, L.rand_unten * mm - 14 * mm)
        canvas.drawRightString(A4[0] - L.rand_rechts * mm, unten, f"Seite {doc.page}")
        if werbung:
            canvas.setFont(L.schrift, 6)
            canvas.setFillGray(0.45)
            canvas.drawString(L.rand_links * mm, unten, werbung)
        canvas.restoreState()

    ziel = Path(ziel)
    SimpleDocTemplate(str(ziel), pagesize=A4, leftMargin=L.rand_links * mm, rightMargin=L.rand_rechts * mm,
                      topMargin=L.rand_oben * mm, bottomMargin=L.rand_unten * mm, title=daten.titel).build(
        el, onFirstPage=seite, onLaterPages=seite)
    if (L.briefpapier_erste_typ == "pdf") or (L.briefpapier_folge_typ == "pdf"):
        _pdf_hinterlegen(ziel, L)
    return ziel


def _pdf_hinterlegen(ziel: Path, L) -> None:
    """Briefpapier als PDF: jede Seite auf die erste bzw. Folge-Seite des Briefpapiers legen."""
    from pypdf import PdfReader, PdfWriter

    inhalt = PdfReader(str(ziel))
    vorlagen = {}
    for name, daten_, typ in (("erste", L.briefpapier_erste, L.briefpapier_erste_typ),
                              ("folge", L.briefpapier_folge, L.briefpapier_folge_typ)):
        if daten_ and typ == "pdf":
            vorlagen[name] = PdfReader(io.BytesIO(daten_)).pages[0]
    writer = PdfWriter()
    for i, seite_ in enumerate(inhalt.pages):
        # Folgeseiten: eigenes Folge-Briefpapier, sonst das der ersten Seite
        vorlage = vorlagen.get("erste") if i == 0 else (vorlagen.get("folge") if L.briefpapier_folge else vorlagen.get("erste"))
        if vorlage is None:
            writer.add_page(seite_)
            continue
        neu = writer.add_blank_page(width=seite_.mediabox.width, height=seite_.mediabox.height)
        neu.merge_page(vorlage)
        neu.merge_page(seite_)
    with open(ziel, "wb") as f:
        writer.write(f)


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

    titel = f"{d['typ']} {d['nummer']}" + (" – STORNIERT" if d["storniert_am"] else "")
    from .layout import a4_layout

    texte = a4_layout(con).texte
    art = "rechnung" if ist_rechnung else "lieferschein"
    daten = A4Daten(titel, kopf, _empfaenger(k), pos, mit_preisen=ist_rechnung,
                    unterschrift=not ist_rechnung, einleitung=texte[f"a4_text_{art}_einleitung"],
                    schluss=texte[f"a4_text_{art}_schluss"])
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
        if d["storniert_am"]:
            daten.hinweise.append(f"<b>Diese Rechnung wurde am {d['storniert_am']} storniert.</b>")
        if gesamt > 1_000_000 and not k["uid"]:
            daten.hinweise.append("<b>Hinweis:</b> Bei Beträgen über 10.000 € ist die UID des Empfängers anzugeben.")
        if d["beleg_id"]:
            b = con.execute("SELECT belegnummer, jws FROM belege WHERE id = ?", (d["beleg_id"],)).fetchone()
            daten.beleg_qr = (maschinenlesbarer_code(b["jws"]), f"Kassenbeleg Nr. {b['belegnummer']} (Kasse {e('kassen_id')})")
    return _render(con, daten, ziel)


def muster_pdf(con: sqlite3.Connection, typ: str, ziel: Path | str) -> Path:
    """Muster-Rechnung bzw. -Lieferschein für die Vorschau des Briefpapiers (schreibt nichts in die Datenbank)."""
    from .layout import a4_layout

    e = lambda s: (einstellung(con, s, "") or "")  # noqa: E731
    ist_rechnung = typ != "Lieferschein"
    texte = a4_layout(con).texte
    art = "rechnung" if ist_rechnung else "lieferschein"
    pos = [(1, "Musterartikel mit längerer Bezeichnung, die bei Bedarf umbricht", "2", "Stk", "20", 1250, 2500),
           (2, "Dienstleistung", "1,5", "Std", "20", 6000, 9000),
           (3, "Lebensmittel (ermäßigter Steuersatz)", "10", "Stk", "10", 180, 1800)]
    daten = A4Daten(f"{'Rechnung RE' if ist_rechnung else 'Lieferschein LS'}-MUSTER",
                    ["Datum: 01.01.2027", "Kundennummer: K-1001"] + (["Leistungsdatum: 01.01.2027"] if ist_rechnung else []),
                    ["Musterfirma GmbH", "z. H. Frau Beispiel", "Musterstraße 12", "1010 Wien", "UID: ATU00000000"],
                    [(p[0], p[1], p[2].replace(",", "."), p[3], p[4], p[5], p[6]) for p in pos],
                    mit_preisen=ist_rechnung, unterschrift=not ist_rechnung,
                    einleitung=texte[f"a4_text_{art}_einleitung"], schluss=texte[f"a4_text_{art}_schluss"])
    if ist_rechnung:
        daten.zahlungstext = "Zahlbar innerhalb von 14 Tagen ohne Abzug." + (f" IBAN: {e('firma_iban')}" if e("firma_iban") else "")
        if e("firma_iban"):
            daten.epc_qr = epc_qr_inhalt(e("firma_name"), e("firma_iban"), e("firma_bic"), 13300, "RE-MUSTER")
    return _render(con, daten, ziel)


def beleg_pdf(con: sqlite3.Connection, beleg_id: int, ziel: Path | str) -> Path:
    """Kassenbeleg (Bon) im A4-Format."""
    e = lambda s: (einstellung(con, s, "") or "")  # noqa: E731
    b = con.execute("SELECT * FROM belege WHERE id = ?", (beleg_id,)).fetchone()
    pos = [(r["pos"], r["bezeichnung"] + (f" (Rabatt −{anzeige(r['rabatt_cent'])} €)" if r["rabatt_cent"] else ""),
            r["menge"], "Stk", r["steuer_prozent"], r["einzelpreis_cent"], r["summe_cent"])
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
