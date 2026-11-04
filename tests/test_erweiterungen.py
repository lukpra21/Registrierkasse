"""Tests für Benutzer, Rabatte, Mischzahlung, Gutscheine, Kassenbuch, Lager, Sicherung,
Export, E-Rechnung, E-Mail, Kartenterminal, Lizenz und Updates."""

import csv
import io
import json
import sqlite3
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

from kasse import (db, ebinterface, export, geheim, kassenbuch, lizenz, mail, sicherung, terminal,
                   update)
from kasse.ui.api import KassenApi


@pytest.fixture
def api(kasse, signer, tmp_path, monkeypatch):
    monkeypatch.setenv("KASSE_DATENVERZEICHNIS", str(tmp_path / "daten"))
    for v in ("DISPLAY", "WAYLAND_DISPLAY"):
        monkeypatch.delenv(v, raising=False)
    monkeypatch.setattr(geheim, "_keyring", lambda: None)
    kasse.startbeleg()
    a = KassenApi(kasse.con, signer, db_pfad=tmp_path / "kasse.db")
    a.artikel_speichern({"name": "Melange", "preis": "4,20", "steuer_prozent": "20", "gruppe": "Kaffee",
                         "artikelnummer": "1", "lagerstand": "10", "mindestbestand": "9"})
    a.artikel_speichern({"name": "Torte", "preis": "5,00", "steuer_prozent": "10", "artikelnummer": "2"})
    return a


def _art(api, nr):
    return next(a for a in api.artikel()["daten"] if a["artikelnummer"] == nr)


def _p(api, nr, menge=1, rabatt=0):
    a = _art(api, nr)
    return {"artikel_id": a["id"], "name": a["name"], "preis_cent": a["brutto_cent"],
            "steuer_prozent": a["steuer_prozent"], "menge": menge, "rabatt_cent": rabatt}


def ok(r):
    assert r["ok"], r.get("fehler")
    return r["daten"]


# ------------------------------------------------------------------ Migration


def test_migration_alter_datenbank(tmp_path):
    pfad = tmp_path / "alt.db"
    c = sqlite3.connect(pfad)
    c.executescript(db.SCHEMA)
    c.execute("INSERT INTO belege (belegnummer, art, zeitpunkt, zahlungsart, betrag_normal, umsatzzaehler,"
              " zertifikat_serie, jws) VALUES (1, 'Barumsatz', '2026-01-01T10:00:00', 'Bar', 500, 500, 'x', 'a.b.c')")
    c.commit()
    c.close()
    con = db.verbinden(pfad)
    assert con.execute("PRAGMA user_version").fetchone()[0] == len(db.MIGRATIONEN)
    assert tuple(con.execute("SELECT art, betrag_cent FROM zahlungen").fetchone()) == ("Bar", 500)


# ------------------------------------------------------------------ Benutzer & Rechte


def test_benutzer_und_rechte(api):
    assert ok(api.status())["benutzer_pflicht"] is False
    assert not api.benutzer_speichern({"name": "Anna", "rolle": "kassier", "pin": "1111"})["ok"]  # erster = Chef
    ok(api.benutzer_speichern({"name": "Chefin", "rolle": "chef", "pin": "1234"}))
    ok(api.benutzer_speichern({"name": "Max", "rolle": "kassier", "pin": "5678"}))
    ok(api.abmelden())
    assert api.artikel()["fehler"] == "Bitte anmelden"
    assert not api.anmelden("0000")["ok"]
    assert ok(api.anmelden("5678"))["rolle"] == "kassier"
    b = ok(api.verkaufen([_p(api, "2")], "Bar"))
    assert b["benutzer_id"] == api.benutzer["id"]
    assert "Chef" in api.storno(b["id"])["fehler"]
    ok(api.anmelden("1234"))
    ok(api.storno(b["id"]))
    arten = [e["art"] for e in ok(api.ereignisse())]
    assert "Storno" in arten and "Anmeldung fehlgeschlagen" in arten


# ------------------------------------------------------------------ Rabatt, Mischzahlung


def test_rabatt_und_mischzahlung(api):
    posten = [_p(api, "1", 2, rabatt=40), _p(api, "2")]  # 8,40 − 0,40 + 5,00 = 13,00
    assert not api.verkaufen(posten, [{"art": "Bar", "betrag_cent": 1000}])["ok"]  # Summe passt nicht
    b = ok(api.verkaufen(posten, [{"art": "Bar", "betrag_cent": 300}, {"art": "Karte", "betrag_cent": 1000}]))
    assert b["zahlungsart"] == "Bar+Karte" and b["betrag_normal"] == 800 and b["betrag_ermaessigt1"] == 500
    from kasse.printing.bon import bon_text

    text = "".join(bon_text(api.con, b["id"]))
    assert "Rabatt" in text and "Bezahlt: Karte" in text
    s = ok(api.storno(b["id"]))
    zahl = api.con.execute("SELECT art, betrag_cent FROM zahlungen WHERE beleg_id = ? ORDER BY art", (s["id"],)).fetchall()
    assert [tuple(z) for z in zahl] == [("Bar", -300), ("Karte", -1000)]


# ------------------------------------------------------------------ Gutscheine


def test_gutschein_verkauf_und_einloesung(api):
    v = ok(api.verkaufen([{"typ": "gutschein_verkauf", "preis_cent": 2000}], "Bar"))
    code = v["gutscheine"][0]
    assert v["betrag_null"] == 2000
    assert ok(api.gutschein_pruefen(code.replace("-", "").lower()))["rest_cent"] == 2000
    # Einlösung 5,00 von 20,00 → Beleg 0,00 (Torte 10 % + Gutschein −5,00 0 %)
    e = ok(api.verkaufen([_p(api, "2"), {"typ": "gutschein_einloesung", "code": code, "preis_cent": 500}], []))
    assert e["betrag_ermaessigt1"] == 500 and e["betrag_null"] == -500 and e["zahlungsart"] == "Gutschein"
    assert ok(api.gutschein_pruefen(code))["rest_cent"] == 1500
    assert not api.storno(v["id"])["ok"]  # Verkaufsbeleg nicht mehr stornierbar
    ok(api.storno(e["id"]))
    assert ok(api.gutschein_pruefen(code))["rest_cent"] == 2000
    assert not api.verkaufen([{"typ": "gutschein_einloesung", "code": code, "preis_cent": 5000}], [])["ok"]


# ------------------------------------------------------------------ Kassenbuch


def test_kassenbuch_und_zaehlprotokoll(api):
    ok(api.kassenbuch_buchen("Anfangsbestand", "100,00", "Wechselgeld"))
    ok(api.verkaufen([_p(api, "2")], "Bar"))
    ok(api.verkaufen([_p(api, "2")], "Karte"))
    ok(api.kassenbuch_buchen("Entnahme", "50,00", "Bank"))
    assert not api.kassenbuch_buchen("Entnahme", "500,00")["ok"]
    kb = ok(api.kassenbuch())
    assert kb["kassastand"] == 10000 + 500 - 5000
    z = ok(api.zaehlprotokoll({"5000": 1, "200": 2, "50": 1}))  # 54,50 statt 55,00
    assert z == {"id": z["id"], "soll": 5500, "ist": 5450, "differenz": -50}
    assert kassenbuch.kassastand(api.con) == 5450


# ------------------------------------------------------------------ Lager


def test_lager(api):
    ok(api.verkaufen([_p(api, "1", 2)], "Bar"))
    assert _art(api, "1")["lagerstand"] == "8"
    assert ok(api.status())["lager_warnungen"] == 1
    ok(api.lager_zugang(_art(api, "1")["id"], "12"))
    assert _art(api, "1")["lagerstand"] == "20"
    ok(api.verkaufen([_p(api, "1", 1)], "Bar", None, True))  # Training bucht kein Lager
    assert _art(api, "1")["lagerstand"] == "20"


# ------------------------------------------------------------------ Sicherung


def test_verschluesselte_sicherung_und_wiederherstellung(api, tmp_path):
    ziel = tmp_path / "sich"
    ziel.mkdir()
    a = sicherung.sichern(api.con, ziel, passwort="geheim123")
    assert a.suffix == ".rksich" and b"SQLite" not in a.read_bytes()
    with pytest.raises(ValueError):
        sicherung.wiederherstellen(a, tmp_path / "x.db", "falsch")
    db_pfad = tmp_path / "live.db"
    db_pfad.write_bytes(b"alt")
    sicherung.wiederherstellung_vormerken(a, db_pfad, "geheim123")
    alt = sicherung.vorgemerkte_wiederherstellung_anwenden(db_pfad)
    assert alt and alt.read_bytes() == b"alt"
    assert sqlite3.connect(db_pfad).execute("SELECT COUNT(*) FROM belege").fetchone()[0] >= 1


# ------------------------------------------------------------------ Export, E-Rechnung, E-Mail


def _rechnung(api):
    kid = ok(api.kunde_speichern({"name": "Hotel Alm GmbH", "adresse": "Almweg 3\n8970 Schladming",
                                  "uid": "ATU87654321", "email": "buchhaltung@example.at"}))
    return ok(api.dokument_erstellen("Rechnung", kid, [_p(api, "1", 3), _p(api, "2")]))


def test_export_steuerberater(api, tmp_path):
    ok(api.verkaufen([_p(api, "1"), _p(api, "2")], [{"art": "Bar", "betrag_cent": 420}, {"art": "Karte", "betrag_cent": 500}]))
    _rechnung(api)
    import datetime as dt

    heute = dt.date.today().isoformat()
    pfad = export.paket(api.con, heute, heute, tmp_path / "x.zip")
    with zipfile.ZipFile(pfad) as z:
        assert set(z.namelist()) == {"belege.csv", "rechnungen.csv", "bmd-buchungen.csv", "dep-export.json"}
        bmd = list(csv.reader(io.StringIO(z.read("bmd-buchungen.csv").decode("cp1252")), delimiter=";"))
        rech = z.read("rechnungen.csv").decode("utf-8-sig")
    texte = {r[-1]: r for r in bmd[1:]}
    cent = lambda t: int(t.replace(",", ""))  # noqa: E731
    assert texte["Tageslosung Bar 20%"][1] == "2700" and texte["Tageslosung Karte 10%"][1] == "2880"
    assert texte["Tageslosung Karte 10%"][2] == "4010"
    # Mischzahlung anteilig aufgeteilt, Summen stimmen exakt
    assert sum(cent(r[9]) for r in bmd[1:]) == 920
    assert sum(cent(r[9]) for r in bmd[1:] if "Bar" in r[-1]) == 420
    assert "Hotel Alm GmbH" in rech


def test_ebinterface(api, tmp_path):
    r = _rechnung(api)
    db.setze_einstellung(api.con, "firma_name", "Muster GmbH")
    db.setze_einstellung(api.con, "firma_iban", "AT611904300234573201")
    pfad = ebinterface.erzeugen(api.con, r["id"], tmp_path / "re.xml")
    root = ET.parse(pfad).getroot()
    ns = {"eb": ebinterface.NS}
    assert root.find("eb:InvoiceNumber", ns).text == r["nummer"]
    assert root.find("eb:TotalGrossAmount", ns).text == "17.60"
    assert root.find("eb:InvoiceRecipient/eb:Address/eb:ZIP", ns).text == "8970"
    assert len(root.findall("eb:Tax/eb:TaxItem", ns)) == 2

    # gegen das offizielle Schema (AUSTRIAPRO ebInterface 6.1) prüfen
    from lxml import etree

    schema = etree.XMLSchema(etree.parse(str(Path(__file__).parent / "schemas" / "ebInterface6p1.xsd")))
    assert schema.validate(etree.parse(str(pfad))), schema.error_log


def test_mail(api, monkeypatch):
    r = _rechnung(api)
    assert "nicht eingerichtet" in api.dokument_mailen(r["id"])["fehler"]
    db.setze_einstellung(api.con, "smtp_host", "smtp.example.at")
    db.setze_einstellung(api.con, "smtp_absender", "office@example.at")
    gesendet = []

    class FakeSMTP:
        def __init__(self, *a, **k): pass
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def starttls(self, **k): pass
        def login(self, *a): pass
        def send_message(self, m): gesendet.append(m)

    monkeypatch.setattr(mail.smtplib, "SMTP", FakeSMTP)
    assert ok(api.dokument_mailen(r["id"], None, True)) == "buchhaltung@example.at"
    namen = [t.get_filename() for t in gesendet[0].iter_attachments()]
    assert namen == [f"{r['nummer']}.pdf", f"{r['nummer']}.xml"]


def test_rechnung_status(api):
    r = _rechnung(api)
    d = next(x for x in ok(api.dokumente("offen")) if x["id"] == r["id"])
    assert d["status"] == "offen"
    ok(api.rechnung_bezahlt(r["id"]))
    assert all(x["id"] != r["id"] for x in ok(api.dokumente("offen")))


# ------------------------------------------------------------------ Kartenterminal (Viva, simuliert)


def test_viva_terminal(api, monkeypatch):
    db.setze_einstellung(api.con, "karten_terminal", "viva")
    db.setze_einstellung(api.con, "viva_client_id", "cid")
    db.setze_einstellung(api.con, "viva_terminal_id", "T1")
    api.con.commit()
    monkeypatch.setenv("KASSE_VIVA_SECRET", "sec")
    antworten = {"poll": 0}

    def fake(self, methode, url, daten=None, token=True, form=None):
        if url.endswith("/connect/token"):
            return 200, {"access_token": "tok", "expires_in": 3600}
        if url.endswith("transactions:sale"):
            assert daten["amount"] == 500 and daten["terminalId"] == "T1"
            return 200, {}
        antworten["poll"] += 1
        return (404, {}) if antworten["poll"] == 1 else (200, {"success": True, "transactionId": "TX42"})

    monkeypatch.setattr(terminal.VivaCloudTerminal, "_anfrage", fake)
    # ohne bestätigte Terminalzahlung kein Verkauf
    assert not api.verkaufen([_p(api, "2")], [{"art": "Karte", "betrag_cent": 500}])["ok"]
    s = ok(api.karte_starten(500))
    assert s["automatisch"]
    assert ok(api.karte_status(s["sitzung"]))["zustand"] == "laeuft"
    assert ok(api.karte_status(s["sitzung"]))["referenz"] == "TX42"
    b = ok(api.verkaufen([_p(api, "2")], [{"art": "Karte", "betrag_cent": 500, "sitzung": s["sitzung"]}]))
    assert api.con.execute("SELECT referenz FROM zahlungen WHERE beleg_id = ?", (b["id"],)).fetchone()[0] == "TX42"


# ------------------------------------------------------------------ Lizenz & Update


def test_lizenz():
    key = ed25519.Ed25519PrivateKey.generate()
    priv = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
    pub = key.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
    s = lizenz.ausstellen(priv, "Café Muster", "ATU1", "2099-12-31")
    assert lizenz.pruefen(s, pub)["status"] == "gueltig"
    assert lizenz.pruefen(s[:-3] + "AAA", pub)["status"] == "ungueltig"
    assert lizenz.pruefen(lizenz.ausstellen(priv, "X", "", "2000-01-01"), pub)["status"] == "abgelaufen"
    assert lizenz.pruefen(None, pub)["status"] == "fehlt"


def test_update(monkeypatch, tmp_path):
    with pytest.raises(update.UpdateFehler):
        update.pruefen("http://unsicher.example/update.json")
    inhalt = b"setup-binary"
    import hashlib

    info = {"version": "99.0.0", "url": "https://example.at/Setup.exe", "sha256": hashlib.sha256(inhalt).hexdigest()}

    class Antwort(io.BytesIO):
        def __enter__(self): return self
        def __exit__(self, *a): return False

    monkeypatch.setattr(update.urllib.request, "urlopen",
                        lambda url, timeout=0: Antwort(json.dumps(info).encode() if url.endswith(".json") else inhalt))
    assert update.pruefen("https://example.at/update.json")["version"] == "99.0.0"
    assert update.herunterladen(info, tmp_path).read_bytes() == inhalt
    with pytest.raises(update.UpdateFehler):
        update.herunterladen({**info, "sha256": "0" * 64}, tmp_path)
    info["version"] = "0.0.1"
    assert update.pruefen("https://example.at/update.json") is None


def test_bmd_gutscheine(api, tmp_path):
    import datetime as dt

    v = ok(api.verkaufen([{"typ": "gutschein_verkauf", "preis_cent": 3000}], "Bar"))
    code = v["gutscheine"][0]
    ok(api.verkaufen([_p(api, "2"), {"typ": "gutschein_einloesung", "code": code, "preis_cent": -500}], []))
    heute = dt.date.today().isoformat()
    zeilen = list(csv.reader(io.StringIO(export.bmd_buchungen(api.con, heute, heute).decode("cp1252")), delimiter=";"))[1:]
    paare = {(z[1], z[2]): z[9] for z in zeilen}
    assert paare[("2700", "3480")] == "30,00"      # Gutscheinverkauf: Kassa an Verbindlichkeit
    assert paare[("3480", "4010")] == "5,00"       # Einlösung: Verbindlichkeit an Erlös 10 %
    assert not any(z[1] == "2880" for z in zeilen)  # nichts auf das Kartenkonto


def test_storno_bar_rechnung(api):
    r = _rechnung(api)
    beleg = api.con.execute("SELECT beleg_id FROM dokumente WHERE id = ?", (r["id"],)).fetchone()[0]
    assert beleg is None  # Überweisung: kein Kassenbeleg
    kid = api.con.execute("SELECT kunde_id FROM dokumente WHERE id = ?", (r["id"],)).fetchone()[0]
    bar = ok(api.dokument_erstellen("Rechnung", kid, [_p(api, "2")], "Bar"))
    ok(api.storno(bar["beleg"]["id"]))
    d = next(x for x in ok(api.dokumente("Rechnung")) if x["id"] == bar["id"])
    assert d["status"] == "storniert"
