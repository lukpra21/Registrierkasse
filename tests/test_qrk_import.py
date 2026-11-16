"""Import-Test mit einer künstlich erzeugten QRK-ähnlichen Datenbank (keine echten Kundendaten)."""

import sqlite3
import zipfile

from kasse.importer import qrk


def _qrk_db(pfad):
    c = sqlite3.connect(pfad)
    c.executescript("""
        CREATE TABLE globals (id INTEGER PRIMARY KEY, name TEXT, value INTEGER, strValue TEXT);
        INSERT INTO globals (name, strValue) VALUES ('shopName', 'Beispiel KG'), ('shopAddress', 'Weg 2\n8010 Graz'),
            ('shopUid', 'ATU00000000'), ('shopCashRegisterId', 'ALT-1'), ('irrelevant', 'x');
        CREATE TABLE taxTypes (id INTEGER PRIMARY KEY, tax REAL, comment TEXT, taxlocation TEXT);
        INSERT INTO taxTypes (tax, comment, taxlocation) VALUES (20.0,'',"AT"),(10.0,'','AT'),(19.0,'','DE');
        CREATE TABLE groups (id INTEGER PRIMARY KEY, name TEXT, visible INTEGER);
        INSERT INTO groups VALUES (1,'auto',0),(2,'Getränke',1),(3,'Speisen',1);
        CREATE TABLE products (id INTEGER PRIMARY KEY, itemnum TEXT, barcode TEXT, name TEXT, net REAL,
            gross REAL, "group" INTEGER, visible INTEGER, tax REAL, description TEXT);
        INSERT INTO products (itemnum, barcode, name, net, gross, "group", visible, tax) VALUES
            ('1', '900100', 'Mineral 0,5', 2.5, 3.0, 2, 1, 20.0),
            ('2', NULL, 'Toast', 4.09, 4.5, 3, 1, 10.0),
            ('3', NULL, 'Alt', 1.0, 1.2, 2, 0, 20.0),
            (NULL, NULL, 'Startbeleg', 0, 0, 1, 0, 20.0);
    """)
    c.commit()
    c.close()


def test_import_aus_zip(tmp_path, con):
    _qrk_db(tmp_path / "qrk.db")
    archiv = tmp_path / "qrk_20261028-1.zip"
    with zipfile.ZipFile(archiv, "w") as z:
        z.write(tmp_path / "qrk.db", "data/qrk.db")

    probe = qrk.importiere(archiv, con, probelauf=True)
    assert probe.artikel == 3 and con.execute("SELECT COUNT(*) FROM artikel").fetchone()[0] == 0

    b = qrk.importiere(archiv, con)
    assert b.firmendaten["firma_name"] == "Beispiel KG"
    assert b.firmendaten["qrk_kassen_id"] == "ALT-1"
    assert sorted(b.steuersaetze) == ["10", "20"]
    assert b.warengruppen == 2
    rows = {r["name"]: r for r in con.execute("SELECT * FROM artikel")}
    assert set(rows) == {"Mineral 0,5", "Toast", "Alt"}
    assert rows["Mineral 0,5"]["brutto_cent"] == 300 and rows["Toast"]["steuer_prozent"] == "10"
    assert rows["Alt"]["sichtbar"] == 0

    # erneuter Import aktualisiert statt zu duplizieren
    qrk.importiere(archiv, con)
    assert con.execute("SELECT COUNT(*) FROM artikel").fetchone()[0] == 3


def test_import_verzeichnis_nur_sichtbare(tmp_path, con):
    (tmp_path / "qrk_20261028-1").mkdir()
    _qrk_db(tmp_path / "qrk_20261028-1" / "qrk.db")
    b = qrk.importiere(tmp_path / "qrk_20261028-1", con, nur_sichtbare=True)
    assert b.artikel == 2


def test_inspiziere(tmp_path):
    _qrk_db(tmp_path / "q.db")
    text = qrk.inspiziere(tmp_path / "q.db")
    assert "products (4 Zeilen)" in text and "Mineral" not in text


def _jws(kassen_id):
    import base64

    teil = base64.urlsafe_b64encode(f"_R1-AT1_{kassen_id}_1_2020-01-01T08:00:00_0,00".encode()).decode().rstrip("=")
    return f"eyJhbGciOiJFUzI1NiJ9.{teil}.sig"


def _qrk_mit_verkaeufen(pfad):
    """QRK-ähnliche Datenbank mit Belegen, Versionen eines Artikels, gelöschtem Artikel und Tagesabschluss."""
    c = sqlite3.connect(pfad)
    c.executescript("""
        CREATE TABLE globals (id INTEGER PRIMARY KEY, name TEXT, value INTEGER, strValue TEXT);
        CREATE TABLE taxtypes (id INTEGER PRIMARY KEY, tax REAL, comment TEXT, taxlocation TEXT);
        INSERT INTO taxtypes (tax, taxlocation) VALUES (20.0,'AT'),(10.0,'AT'),(13.0,'AT');
        CREATE TABLE groups (id INTEGER PRIMARY KEY, name TEXT, visible INTEGER);
        INSERT INTO groups VALUES (1,'auto',0),(2,'Wurstwaren',1),(3,'Öle',1);
        CREATE TABLE products (id INTEGER PRIMARY KEY, itemnum TEXT, barcode TEXT, name TEXT, net REAL, gross REAL,
            groupid INTEGER, visible INTEGER, tax REAL, description TEXT, lastchange TEXT);
        INSERT INTO products VALUES
            (1,'1',NULL,'Käswurst',10.9,12.0,2,1,10.0,NULL,'2024-01-01'),
            (2,'2',NULL,'Kernöl 1 lt',16.81,19.0,3,1,13.0,NULL,'2025-01-01'),
            (3,'2',NULL,'Kernöl 1 lt ***',15.04,17.0,3,0,13.0,NULL,'2020-01-01'),
            (4,'',NULL,'Monatsbeleg Jän 2020',0,0,1,0,0,NULL,NULL),
            (5,'9',NULL,'Kontroll NULL Beleg',0,0,1,0,0,NULL,NULL);
        CREATE TABLE receipts (id INTEGER PRIMARY KEY, timestamp TEXT, infodate TEXT, receiptNum INTEGER,
            payedBy INTEGER, gross REAL, storno INTEGER, stornoId INTEGER);
        INSERT INTO receipts VALUES
            (1,'2020-01-02T08:00:00','2020-01-02T08:00:00',1,6,0,0,0),
            (2,'2020-01-02T09:15:00','2020-01-02T09:15:00',2,0,23.0,1,4),
            (3,'2020-01-02T10:30:00','2020-01-02T10:30:00',3,1,55.0,0,0),
            (4,'2020-01-03T11:00:00','2020-01-03T11:00:00',4,0,-23.0,2,2),
            (5,'2020-01-03T18:00:00','2020-01-02T23:59:59',5,4,78.0,0,0),
            (6,'2025-06-01T09:00:00','2025-06-01T09:00:00',6,0,6.0,0,0);
        CREATE TABLE orders (id INTEGER PRIMARY KEY, receiptId INTEGER, product INTEGER, count REAL, discount REAL,
            net REAL, gross REAL, tax REAL);
        INSERT INTO orders VALUES
            (1,2,1,0.5,0,5.45,12.0,10.0),
            (2,2,3,1,0,15.04,17.0,13.0),
            (3,3,48,1,0,50.0,55.0,10.0),
            (4,4,1,-0.5,0,5.45,12.0,10.0),
            (5,4,3,-1,0,15.04,17.0,13.0),
            (6,6,1,0.5,0,5.45,12.0,10.0);
        CREATE TABLE reports (id INTEGER PRIMARY KEY, receiptNum INTEGER, timestamp TEXT, text TEXT, type INTEGER);
        INSERT INTO reports (receiptNum, text, type) VALUES
            (5,'Verkaufte Artikel oder Leistungen (Gruppiert) Gesamt 2,50',2),
            (5,'0,500: Käswurst: 12,00: 6,00: 10%',2),
            (5,'1,000: div Wurstwaren: 55,00: 55,00: 10%',2);
        CREATE TABLE dep (id INTEGER PRIMARY KEY, receiptNum INTEGER, data TEXT);
    """)
    c.execute("INSERT INTO dep (receiptNum, data) VALUES (1, ?)", (_jws("RK1"),))
    c.commit()
    c.close()


def test_import_verkaeufe(tmp_path, con):
    _qrk_mit_verkaeufen(tmp_path / "2020-QRK.db")
    probe = qrk.importiere(tmp_path, con, verkaeufe=True, probelauf=True)
    assert probe.altbelege == 4 and con.execute("SELECT COUNT(*) FROM altbelege").fetchone()[0] == 0

    b = qrk.importiere(tmp_path, con, verkaeufe=True)
    assert b.kassen_id == "RK1" and b.firmendaten["qrk_kassen_id"] == "RK1"
    assert b.artikel == 2 and b.artikel_zusammengefasst == 1 and b.artikel_uebersprungen == 2
    assert b.altbelege == 4 and b.altbelege_storno == 1 and b.altbelege_umsatz_cent == 2300 + 5500 - 2300 + 600
    art = {r["name"]: r for r in con.execute("SELECT * FROM artikel")}
    assert set(art) == {"Käswurst", "Kernöl 1 lt"}
    assert art["Käswurst"]["einheit"] == "kg" and art["Kernöl 1 lt"]["einheit"] == "Stk"
    assert art["Kernöl 1 lt"]["brutto_cent"] == 1900          # aktuelle Version gewinnt

    belege = {r["belegnummer"]: r for r in con.execute("SELECT * FROM altbelege")}
    assert set(belege) == {2, 3, 4, 6}                        # Startbeleg/Tagesabschluss nicht
    assert belege[2]["storniert"] == 1 and belege[4]["art"] == "Storno" and belege[3]["zahlungsart"] == "Karte"
    pos = {(r["altbeleg_id"], r["pos"]): r for r in con.execute("SELECT * FROM altbelegpositionen")}
    p2 = pos[(belege[2]["id"], 2)]
    assert p2["artikel_id"] == art["Kernöl 1 lt"]["id"] and p2["bezeichnung"] == "Kernöl 1 lt"  # alte Version zugeordnet
    p3 = pos[(belege[3]["id"], 1)]
    assert p3["artikel_id"] is None and p3["bezeichnung"] == "div Wurstwaren"  # aus Tagesabschluss rekonstruiert
    assert pos[(belege[2]["id"], 1)]["menge"] == "0.5" and pos[(belege[2]["id"], 1)]["summe_cent"] == 600
    # Positionen ergeben je Beleg die Belegsumme
    for bel in belege.values():
        s = con.execute("SELECT SUM(summe_cent) FROM altbelegpositionen WHERE altbeleg_id = ?", (bel["id"],)).fetchone()[0]
        assert s == bel["summe_cent"]
    # RKSV-Kette bleibt unberührt
    assert con.execute("SELECT COUNT(*) FROM belege").fetchone()[0] == 0

    # erneuter Import: keine Duplikate
    qrk.importiere(tmp_path, con, verkaeufe=True)
    assert con.execute("SELECT COUNT(*) FROM altbelege").fetchone()[0] == 4
    assert con.execute("SELECT COUNT(*) FROM altbelegpositionen").fetchone()[0] == 6
    assert con.execute("SELECT COUNT(*) FROM artikel").fetchone()[0] == 2


def test_neueste_jahresdatenbank(tmp_path):
    _qrk_mit_verkaeufen(tmp_path / "2025-QRK.db")
    _qrk_db(tmp_path / "2019-QRK.db")
    with qrk.qrk_datenbank(tmp_path) as (db, _):
        assert db.name == "2025-QRK.db"


def test_negativer_preis_ausgeblendet(tmp_path, con):
    _qrk_mit_verkaeufen(tmp_path / "q.db")
    c = sqlite3.connect(tmp_path / "q.db")
    c.execute("INSERT INTO products VALUES (9,'50',NULL,'Grillfleisch Korrektur',-30.9,-34.0,2,1,10.0,NULL,'2025-01-01')")
    c.commit()
    c.close()
    b = qrk.importiere(tmp_path / "q.db", con)
    assert any("negativen Preis" in h for h in b.hinweise)
    assert con.execute("SELECT sichtbar FROM artikel WHERE name = 'Grillfleisch Korrektur'").fetchone()[0] == 0
