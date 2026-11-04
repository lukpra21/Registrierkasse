"""E-Rechnung im österreichischen Standard ebInterface 6.1.

Vor dem produktiven Einsatz eine erzeugte Datei mit dem offiziellen
Validator (www.ebinterface.at) prüfen. Für Rechnungen an den Bund ist
zusätzlich die Einbringung über das USP (e-rechnung.gv.at) nötig.
"""

from __future__ import annotations

import re
import sqlite3
import xml.etree.ElementTree as ET
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

from .db import einstellung
from .geld import netto_aus_brutto

NS = "http://www.ebinterface.at/schema/6p1/"


def _betrag(cent: int) -> str:
    return f"{Decimal(cent) / 100:.2f}"


def _adresse(eltern: ET.Element, name: str, adresse: str, email: str | None = None) -> None:
    a = ET.SubElement(eltern, f"{{{NS}}}Address")
    ET.SubElement(a, f"{{{NS}}}Name").text = name
    zeilen = [z.strip() for z in (adresse or "").splitlines() if z.strip()]
    strasse, plz, ort = (zeilen[0] if zeilen else ""), "", ""
    for z in zeilen[1:]:
        if m := re.match(r"^(?:A-)?(\d{4,5})\s+(.+)$", z):
            plz, ort = m.group(1), m.group(2)
    ET.SubElement(a, f"{{{NS}}}Street").text = strasse or "-"
    ET.SubElement(a, f"{{{NS}}}Town").text = ort or "-"
    ET.SubElement(a, f"{{{NS}}}ZIP").text = plz or "0000"
    land = ET.SubElement(a, f"{{{NS}}}Country", CountryCode="AT")
    land.text = "Österreich"
    if email:
        ET.SubElement(a, f"{{{NS}}}Email").text = email


def erzeugen(con: sqlite3.Connection, dok_id: int, ziel: Path | str) -> Path:
    e = lambda k: einstellung(con, k, "") or ""  # noqa: E731
    d = con.execute("SELECT * FROM dokumente WHERE id = ? AND typ = 'Rechnung'", (dok_id,)).fetchone()
    if not d:
        raise ValueError("Nur Rechnungen können als ebInterface exportiert werden")
    k = con.execute("SELECT * FROM kunden WHERE id = ?", (d["kunde_id"],)).fetchone()

    ET.register_namespace("", NS)
    root = ET.Element(f"{{{NS}}}Invoice", {
        "GeneratingSystem": "Registrierkasse", "DocumentType": "Invoice",
        "InvoiceCurrency": "EUR", "Language": "de"})
    ET.SubElement(root, f"{{{NS}}}InvoiceNumber").text = d["nummer"]
    ET.SubElement(root, f"{{{NS}}}InvoiceDate").text = d["datum"]
    lief = ET.SubElement(root, f"{{{NS}}}Delivery")
    ET.SubElement(lief, f"{{{NS}}}Date").text = d["datum"]

    biller = ET.SubElement(root, f"{{{NS}}}Biller")
    ET.SubElement(biller, f"{{{NS}}}VATIdentificationNumber").text = e("firma_uid") or "00000000"
    _adresse(biller, e("firma_name"), e("firma_adresse"), e("smtp_absender") or None)

    empf = ET.SubElement(root, f"{{{NS}}}InvoiceRecipient")
    ET.SubElement(empf, f"{{{NS}}}VATIdentificationNumber").text = k["uid"] or "00000000"
    _adresse(empf, k["name"], k["adresse"], k["email"])
    if k["kundennummer"]:  # laut Schema nach der Adresse
        ET.SubElement(empf, f"{{{NS}}}BillersInvoiceRecipientID").text = k["kundennummer"]

    details = ET.SubElement(root, f"{{{NS}}}Details")
    liste = ET.SubElement(details, f"{{{NS}}}ItemList")
    steuern: dict[str, int] = {}
    gesamt = 0
    for p in con.execute("SELECT * FROM dokumentpositionen WHERE dokument_id = ? ORDER BY pos", (dok_id,)):
        menge = Decimal(p["menge"])
        brutto = int((menge * p["einzelpreis_cent"]).quantize(Decimal("1"), ROUND_HALF_UP))
        netto = netto_aus_brutto(brutto, p["steuer_prozent"])
        einzel_netto = (Decimal(netto) / 100 / menge) if menge else Decimal(0)
        steuern[p["steuer_prozent"]] = steuern.get(p["steuer_prozent"], 0) + brutto
        gesamt += brutto
        z = ET.SubElement(liste, f"{{{NS}}}ListLineItem")
        ET.SubElement(z, f"{{{NS}}}PositionNumber").text = str(p["pos"])
        ET.SubElement(z, f"{{{NS}}}Description").text = p["bezeichnung"]
        ET.SubElement(z, f"{{{NS}}}Quantity", Unit="H87").text = format(menge, "f")
        ET.SubElement(z, f"{{{NS}}}UnitPrice").text = f"{einzel_netto:.4f}"
        ti = ET.SubElement(z, f"{{{NS}}}TaxItem")
        ET.SubElement(ti, f"{{{NS}}}TaxableAmount").text = _betrag(netto)
        ET.SubElement(ti, f"{{{NS}}}TaxPercent", TaxCategoryCode="S" if Decimal(p["steuer_prozent"]) else "Z").text = \
            format(Decimal(p["steuer_prozent"]), "f")
        ET.SubElement(ti, f"{{{NS}}}TaxAmount").text = _betrag(brutto - netto)
        ET.SubElement(z, f"{{{NS}}}LineItemAmount").text = _betrag(netto)

    tax = ET.SubElement(root, f"{{{NS}}}Tax")
    for satz, brutto in sorted(steuern.items(), key=lambda kv: -float(kv[0])):
        netto = netto_aus_brutto(brutto, satz)
        ti = ET.SubElement(tax, f"{{{NS}}}TaxItem")
        ET.SubElement(ti, f"{{{NS}}}TaxableAmount").text = _betrag(netto)
        ET.SubElement(ti, f"{{{NS}}}TaxPercent", TaxCategoryCode="S" if Decimal(satz) else "Z").text = \
            format(Decimal(satz), "f")
        ET.SubElement(ti, f"{{{NS}}}TaxAmount").text = _betrag(brutto - netto)
    ET.SubElement(root, f"{{{NS}}}TotalGrossAmount").text = _betrag(gesamt)
    ET.SubElement(root, f"{{{NS}}}PayableAmount").text = _betrag(0 if d["bezahlt_am"] else gesamt)

    zm = ET.SubElement(root, f"{{{NS}}}PaymentMethod")
    if e("firma_iban") and not d["bezahlt_am"]:
        ub = ET.SubElement(zm, f"{{{NS}}}UniversalBankTransaction")
        konto = ET.SubElement(ub, f"{{{NS}}}BeneficiaryAccount")
        if e("firma_bic"):
            ET.SubElement(konto, f"{{{NS}}}BIC").text = e("firma_bic").replace(" ", "")
        ET.SubElement(konto, f"{{{NS}}}IBAN").text = e("firma_iban").replace(" ", "")
        ET.SubElement(konto, f"{{{NS}}}BankAccountOwner").text = e("firma_name")
        ET.SubElement(ub, f"{{{NS}}}PaymentReference").text = d["nummer"]
    else:
        ET.SubElement(zm, f"{{{NS}}}NoPayment")
    if not d["bezahlt_am"]:
        bed = ET.SubElement(root, f"{{{NS}}}PaymentConditions")
        import datetime as dt

        faellig = dt.date.fromisoformat(d["datum"]) + dt.timedelta(days=k["zahlungsziel_tage"])
        ET.SubElement(bed, f"{{{NS}}}DueDate").text = faellig.isoformat()

    ET.indent(root)
    ziel = Path(ziel)
    ET.ElementTree(root).write(ziel, encoding="UTF-8", xml_declaration=True)
    return ziel
