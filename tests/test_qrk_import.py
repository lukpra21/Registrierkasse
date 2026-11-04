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
