import zipfile
from decimal import Decimal

from escpos.printer import Dummy

from kasse import dokumente, sicherung
from kasse.printing.a4 import dokument_pdf
from kasse.printing.bon import bon_text, drucke_bon
from kasse.rksv import Position


def test_bon(kasse):
    kasse.startbeleg()
    b = kasse.verkauf([Position("Kaffee", Decimal("2"), 350, "20"), Position("Kuchen", Decimal("1"), 420, "10")])
    text = "".join(bon_text(kasse.con, b))
    assert "Muster GmbH" in text and "SUMME EUR" in text and "11,20" in text
    d = Dummy()
    drucke_bon(kasse.con, b, d)
    assert b"Kaffee" in d.output


def test_lieferschein_rechnung_pdf(kasse, tmp_path):
    kasse.startbeleg()
    kid = kasse.con.execute(
        "INSERT INTO kunden (kundennummer, name, adresse, uid) VALUES ('K1','Firma B','Gasse 3\n4020 Linz','ATU99999999')"
    ).lastrowid
    pos = [dokumente.DokPosition("Palette Holz", Decimal("3"), 12000, "20")]
    ls1 = dokumente.lieferschein(kasse.con, kid, pos)
    ls2 = dokumente.lieferschein(kasse.con, kid, pos)
    re_ueb = dokumente.rechnung_aus_lieferscheinen(kasse.con, [ls1, ls2])
    re_bar = dokumente.rechnung(kasse.con, kid, pos, "Bar", kasse)

    nummern = [r[0] for r in kasse.con.execute("SELECT nummer FROM dokumente ORDER BY id")]
    assert nummern[0].startswith("LS-") and nummern[1].endswith("00002") and nummern[2].endswith("00001")
    assert kasse.con.execute("SELECT beleg_id FROM dokumente WHERE id=?", (re_ueb,)).fetchone()[0] is None
    assert kasse.con.execute("SELECT beleg_id FROM dokumente WHERE id=?", (re_bar,)).fetchone()[0] is not None

    for i in (ls1, re_ueb, re_bar):
        pdf = dokument_pdf(kasse.con, i, tmp_path / f"{i}.pdf")
        assert pdf.read_bytes().startswith(b"%PDF")


def test_sicherung_mit_rotation(kasse, tmp_path):
    kasse.startbeleg()
    ziel = tmp_path / "backup"
    ziel.mkdir()
    for _ in range(3):
        sicherung.sichern(kasse.con, ziel, behalten=2)
    assert len(list(ziel.glob("kasse-sicherung-*.zip"))) == 2
    with zipfile.ZipFile(sorted(ziel.glob("*.zip"))[-1]) as z:
        assert set(z.namelist()) == {"kasse.db", "dep-export.json"}
    assert not sicherung.sicherung_faellig(kasse.con)

    ziel_db = tmp_path / "wieder.db"
    sicherung.wiederherstellen(sorted(ziel.glob("*.zip"))[-1], ziel_db)
    assert ziel_db.read_bytes().startswith(b"SQLite format 3")


def test_sicherung_mit_offenem_schreibvorgang(kasse, tmp_path):
    """Regression: offene Transaktion auf derselben Verbindung darf die Sicherung nicht blockieren."""
    from kasse import db

    kasse.startbeleg()
    db.setze_einstellung(kasse.con, "firma_name", "Noch nicht gespeichert")
    assert kasse.con.in_transaction
    ziel = tmp_path / "s"
    ziel.mkdir()
    assert sicherung.sichern(kasse.con, ziel, passwort="").exists()
