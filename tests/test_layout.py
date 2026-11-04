"""Briefpapier (A4) und Bondrucker-Papier: einstellbare Layouts."""

import base64
import io
from decimal import Decimal

import pytest
from escpos.printer import Dummy
from pypdf import PdfReader

from kasse import db, dokumente, geheim
from kasse.printing.a4 import dokument_pdf, muster_pdf
from kasse.printing.bon import bon_text, drucke_bon
from kasse.printing.layout import a4_layout, bon_layout
from kasse.rksv import Position
from kasse.ui.api import KassenApi


def _text(pfad) -> str:
    quelle = pfad if isinstance(pfad, io.BytesIO) else str(pfad)
    return "\n".join(s.extract_text() for s in PdfReader(quelle).pages)


def _setze(con, **werte):
    for k, v in werte.items():
        db.setze_einstellung(con, k, str(v))
    con.commit()


@pytest.fixture
def api(kasse, signer, tmp_path, monkeypatch):
    monkeypatch.setenv("KASSE_DATENVERZEICHNIS", str(tmp_path / "daten"))
    monkeypatch.setattr(geheim, "_keyring", lambda: None)
    kasse.startbeleg()
    return KassenApi(kasse.con, signer, db_pfad=tmp_path / "kasse.db")


def _briefpapier_pdf(text: str) -> str:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    puffer = io.BytesIO()
    c = canvas.Canvas(puffer, pagesize=A4)
    c.drawString(40, 800, text)
    c.save()
    return "data:application/pdf;base64," + base64.b64encode(puffer.getvalue()).decode()


def test_standardwerte(con):
    a = a4_layout(con)
    assert (a.rand_links, a.adresse_oben, a.logo_position, a.schrift) == (20, 45, "rechts", "Helvetica")
    b = bon_layout(con)
    assert (b.zeichen, b.breite_px, b.schnitt) == (42, 512, "teil")


def test_a4_texte_fusszeile_und_grenzen(kasse, tmp_path):
    con = kasse.con
    _setze(con, a4_text_rechnung_einleitung="Wir danken für Ihre Bestellung:",
           a4_text_rechnung_schluss="Mit freundlichen Grüßen", a4_fusszeile="Eigene Fußzeile 123",
           a4_rand_links="999", a4_schrift="Times-Roman", a4_logo_position="aus")
    assert a4_layout(con).rand_links == 60  # auf Maximum begrenzt
    kid = con.execute("INSERT INTO kunden (name, adresse) VALUES ('Kunde X', 'Weg 1\n1010 Wien')").lastrowid
    re_ = dokumente.rechnung(con, kid, [dokumente.DokPosition("Ware", Decimal(1), 1000, "20")])
    text = _text(dokument_pdf(con, re_, tmp_path / "r.pdf"))
    for erwartet in ("Wir danken für Ihre Bestellung:", "Mit freundlichen Grüßen", "Eigene Fußzeile 123", "Kunde X"):
        assert erwartet in text


def test_briefpapier_pdf_hinterlegt(kasse, tmp_path):
    con = kasse.con
    _setze(con, a4_briefpapier_erste=_briefpapier_pdf("BRIEFKOPF SEITE EINS"),
           a4_absender_zeile="0", a4_fusszeile_anzeigen="0")
    text = _text(muster_pdf(con, "Rechnung", tmp_path / "m.pdf"))
    assert "BRIEFKOPF SEITE EINS" in text and "RE-MUSTER" in text


def test_briefpapier_bild_hinterlegt(kasse, tmp_path):
    from PIL import Image

    puffer = io.BytesIO()
    Image.new("RGB", (60, 85), (250, 240, 220)).save(puffer, "PNG")
    _setze(kasse.con, a4_briefpapier_erste="data:image/png;base64," + base64.b64encode(puffer.getvalue()).decode())
    pfad = muster_pdf(kasse.con, "Lieferschein", tmp_path / "l.pdf")
    assert PdfReader(str(pfad)).pages[0].images  # Hintergrundbild eingebettet


def test_bon_58mm(kasse):
    con = kasse.con
    _setze(con, bon_zeichen="32", bon_kopftext="Mo–Fr 7–18 Uhr · Tel. 0732 123456", bon_qr_groesse="6",
           bon_schnitt="voll", bon_vorschub="2", firma_name="Bäckerei")
    kasse.startbeleg()
    b = kasse.verkauf([Position("Sehr langer Artikelname, der abgeschnitten wird", Decimal(1), 450, "10")])
    zeilen = "".join(bon_text(con, b)).splitlines()
    assert max(len(z) for z in zeilen) <= 32
    assert any("Mo–Fr" in z for z in zeilen)
    d = Dummy()
    drucke_bon(con, b, d)
    assert b"\x1dV\x00" in d.output or b"\x1dVA" in d.output or b"\x1dV" in d.output  # Schnittbefehl


def test_api_vorschau_und_validierung(api):
    r = api.vorschau_a4("Rechnung", {"a4_text_rechnung_schluss": "VORSCHAUTEXT", "a4_rand_oben": "30"})
    assert r["ok"], r
    pdf = base64.b64decode(r["daten"]["pdf"])
    assert pdf.startswith(b"%PDF") and "VORSCHAUTEXT" in _text(io.BytesIO(pdf))
    # Vorschauwerte werden nicht gespeichert
    assert api.einstellungen()["daten"]["a4_text_rechnung_schluss"] != "VORSCHAUTEXT"
    v = api.vorschau_bon({"bon_zeichen": "32"})["daten"]
    assert v["zeichen"] == 32
    f = api.einstellungen_speichern({"a4_rand_oben": "500"})
    assert not f["ok"] and "erlaubt" in f["fehler"]
    assert api.einstellungen_speichern({"a4_rand_oben": "25", "bon_schnitt": "kein"})["ok"]
    assert a4_layout(api.con).rand_oben == 25 and bon_layout(api.con).schnitt == "kein"
    assert not api.briefpapier_setzen("erste", "data:text/plain;base64,QUJD")["ok"]
    assert api.briefpapier_setzen("folge", _briefpapier_pdf("FOLGE"))["ok"]
    assert api.einstellungen()["daten"]["_briefpapier"]["a4_briefpapier_folge"] is True
