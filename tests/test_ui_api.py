"""Tests der Oberflächen-Schnittstelle (ohne Fenster/Drucker)."""

from pathlib import Path

import pytest

from kasse.printing.a4 import epc_qr_inhalt
from kasse.ui.api import KassenApi, oeffentliche_methoden


@pytest.fixture
def api(kasse, signer, tmp_path, monkeypatch):
    monkeypatch.setenv("KASSE_DATENVERZEICHNIS", str(tmp_path / "daten"))
    monkeypatch.delenv("DISPLAY", raising=False)
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
    kasse.startbeleg()
    a = KassenApi(kasse.con, signer)
    assert a.artikel_speichern({"name": "Melange", "preis": "4,20", "steuer_prozent": "20", "gruppe": "Kaffee"})["ok"]
    return a


def _posten(api):
    a = api.artikel()["daten"][0]
    return [{"artikel_id": a["id"], "name": a["name"], "preis_cent": a["brutto_cent"], "steuer_prozent": a["steuer_prozent"], "menge": 2}]


def test_verkauf_und_ausgabe_pdf(api):
    r = api.verkaufen(_posten(api), "Karte")
    assert r["ok"] and r["daten"]["zahlungsart"] == "Karte" and r["daten"]["druck"] is None
    pdf = api.ausgabe("beleg", r["daten"]["id"], "pdf")
    assert pdf["ok"] and Path(pdf["daten"]).read_bytes().startswith(b"%PDF")
    bericht = api.tagesbericht(r["daten"]["zeitpunkt"][:10])["daten"]
    assert bericht["gesamt"] == 840


def test_unbekannte_zahlungsart(api):
    r = api.verkaufen(_posten(api), "Gutschein")
    assert not r["ok"] and "Zahlungsart" in r["fehler"]


def test_bon_ohne_drucker_meldet_fehler(api):
    b = api.verkaufen(_posten(api), "Bar")["daten"]
    r = api.ausgabe("beleg", b["id"], "bon")
    assert not r["ok"]


def test_lieferschein_rechnung(api):
    kid = api.kunde_speichern({"name": "Firma X", "adresse": "Weg 1", "uid": "ATU1"})["daten"]
    ls = api.dokument_erstellen("Lieferschein", kid, _posten(api))["daten"]
    assert not api.ausgabe("dokument", ls["id"], "bon")["ok"]  # Lieferschein hat keinen Bon
    assert api.ausgabe("dokument", ls["id"], "pdf")["ok"]
    re = api.rechnung_aus_lieferscheinen([ls["id"]], "Überweisung")["daten"]
    assert re["nummer"].startswith("RE-")
    assert not api.rechnung_aus_lieferscheinen([ls["id"]])["ok"]  # nicht doppelt verrechnen
    docs = {d["nummer"]: d for d in api.dokumente()["daten"]}
    assert docs[ls["nummer"]]["verrechnet"] == 1


def test_nur_freigegebene_methoden(api):
    m = oeffentliche_methoden(api)
    assert "verkaufen" in m and "ausgabe" in m and "con" not in m and "kasse" not in m


def test_epc_qr():
    t = epc_qr_inhalt("Muster GmbH", "AT61 1904 3002 3457 3201", "BKAUATWW", 12345, "RE-2026-00001").split("\n")
    assert t[:4] == ["BCD", "002", "1", "SCT"] and t[6] == "AT611904300234573201" and t[7] == "EUR123.45"
