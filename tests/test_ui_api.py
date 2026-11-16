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


def test_statistik_mit_altbelegen(api):
    con = api.con
    aid = con.execute("SELECT id FROM artikel WHERE name = 'Melange'").fetchone()[0]
    bid = con.execute("INSERT INTO altbelege (quelle, kassen_id, belegnummer, zeitpunkt, art, zahlungsart, summe_cent)"
                      " VALUES ('QRK', 'RK1', 7, '2026-11-03T10:15:00', 'Barumsatz', 'Bar', 1260)").lastrowid
    con.execute("INSERT INTO altbelegpositionen VALUES (?, 1, ?, 'Melange', '3', 420, '20', 1260)", (bid, aid))
    con.commit()
    api.verkaufen(_posten(api), "Bar")
    st = api.statistik("2026-11-01", "2026-11-30")["daten"]
    assert st["altdaten"] == 1260
    assert sum(t["umsatz"] for t in st["tage"]) == 840 + 1260
    assert st["artikel"][0]["name"] == "Melange" and st["artikel"][0]["umsatz"] == 840 + 1260
    assert {z["art"]: z["umsatz"] for z in st["zahlungen"]}["Bar"] == 840 + 1260
    assert api.status()["daten"]["altbelege"] is True
    liste = api.altbelege("2026-11-03")["daten"]
    assert [b["belegnummer"] for b in liste] == [7]
    assert api.altbeleg(bid)["daten"]["positionen"][0]["bezeichnung"] == "Melange"
    # die RKSV-Belegliste bleibt getrennt
    assert len(api.belege()["daten"]) == 2  # Startbeleg + Verkauf


def test_gewichtsartikel_und_freipreis(api):
    from kasse.printing.bon import bon_text

    r = api.artikel_speichern({"name": "Speck", "preis": "18,00", "steuer_prozent": "10", "einheit": "kg"})
    assert r["ok"]
    aid = r["daten"]
    speck = next(a for a in api.artikel()["daten"] if a["id"] == aid)
    assert speck["einheit"] == "kg"
    # Speichern ohne Einheit (ältere Oberfläche) lässt kg stehen
    assert api.artikel_speichern({"id": aid, "name": "Speck", "preis": "19,00", "steuer_prozent": "10"})["ok"]
    assert api.con.execute("SELECT einheit FROM artikel WHERE id = ?", (aid,)).fetchone()[0] == "kg"
    assert not api.artikel_speichern({"name": "X", "preis": "-1", "steuer_prozent": "20"})["ok"]
    assert not api.artikel_speichern({"name": "X", "preis": "1", "steuer_prozent": "20", "einheit": "Liter"})["ok"]
    # Verkauf 0,395 kg + Freipreis-Position
    v = api.verkaufen([{"artikel_id": aid, "name": "Speck", "preis_cent": 1900, "steuer_prozent": "10", "menge": 0.395},
                       {"artikel_id": None, "name": "Geschenkskorb", "preis_cent": 4590, "steuer_prozent": "13", "menge": 1}],
                      "Bar")["daten"]
    text = "".join(bon_text(api.con, v["id"]))
    assert "0,395 kg x 19,00" in text
    assert v["betrag_ermaessigt1"] == 751 and v["betrag_ermaessigt2"] == 4590
