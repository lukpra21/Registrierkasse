import base64
from decimal import Decimal

import pytest

from kasse.rksv import KassenFehler, Position
from kasse.rksv import krypto
from kasse.rksv.dep import dep_export
from kasse.rksv.signatur import pruefe_jws


def _pos(preis=1250, menge="1", satz="20"):
    return Position("Artikel", Decimal(menge), preis, satz)


def test_umsatzzaehler_roundtrip():
    k = krypto.neuer_aes_schluessel()
    for wert in (0, 1, 12345, -500, 10**12):
        enc = krypto.umsatzzaehler_verschluesseln(wert, "K1", "7", k)
        assert len(base64.b64decode(enc)) == krypto.UMSATZZAEHLER_BYTES
        assert krypto.umsatzzaehler_entschluesseln(enc, "K1", "7", k) == wert


def test_kettenwert_laenge():
    assert len(base64.b64decode(krypto.kettenwert("KASSE-01"))) == 8


def test_verkauf_vor_startbeleg_verboten(kasse):
    with pytest.raises(KassenFehler):
        kasse.verkauf([_pos()])


def test_belegkette_und_signatur(kasse, signer):
    kasse.startbeleg()
    b1 = kasse.verkauf([_pos(1250, "2", "20"), _pos(330, "1", "10")])
    kasse.verkauf([_pos(100, "1", "13")])
    zert = signer.zertifikat().zertifikat_b64
    belege = kasse.con.execute("SELECT * FROM belege ORDER BY belegnummer").fetchall()
    assert [b["art"] for b in belege] == ["Startbeleg", "Barumsatz", "Barumsatz"]

    vorher = "KASSE-01"
    for b in belege:
        assert pruefe_jws(b["jws"], zert)
        _, payload, _ = krypto.jws_teile(b["jws"])
        teile = payload.split("_")
        assert teile[1] == "R1-AT0" and teile[2] == "KASSE-01" and teile[3] == str(b["belegnummer"])
        assert teile[-1] == krypto.kettenwert(vorher)
        assert krypto.umsatzzaehler_entschluesseln(teile[10], "KASSE-01", teile[3], kasse._aes) == b["umsatzzaehler"]
        vorher = b["jws"]

    _, payload, _ = krypto.jws_teile(kasse.con.execute("SELECT jws FROM belege WHERE id=?", (b1,)).fetchone()[0])
    assert payload.split("_")[5:10] == ["25,00", "3,30", "0,00", "0,00", "0,00"]
    assert kasse.umsatzzaehler() == 2500 + 330 + 100


def test_storno_und_training(kasse):
    kasse.startbeleg()
    b = kasse.verkauf([_pos(1000)])
    s = kasse.storno(b)
    t = kasse.verkauf([_pos(999)], training=True)
    assert kasse.umsatzzaehler() == 0
    row = lambda i: kasse.con.execute("SELECT jws FROM belege WHERE id=?", (i,)).fetchone()[0]  # noqa: E731
    assert krypto.jws_teile(row(s))[1].split("_")[10] == krypto.STORNO_MARKER
    assert krypto.jws_teile(row(s))[1].split("_")[5] == "-10,00"
    assert krypto.jws_teile(row(t))[1].split("_")[10] == krypto.TRAINING_MARKER
    with pytest.raises(KassenFehler):
        kasse.storno(b)


def test_ausfall_und_sammelbeleg(kasse, signer):
    kasse.startbeleg()
    signer.verfuegbar = False
    b = kasse.verkauf([_pos()])
    assert kasse.ausfall_aktiv()
    jws = kasse.con.execute("SELECT jws, ausfall FROM belege WHERE id=?", (b,)).fetchone()
    assert jws["ausfall"] == 1
    assert krypto.jws_teile(jws["jws"])[2].decode() == krypto.AUSFALL_TEXT
    with pytest.raises(Exception):
        kasse.nullbeleg("Monatsbeleg")  # muss signiert sein
    signer.verfuegbar = True
    kasse.verkauf([_pos()])
    arten = [r[0] for r in kasse.con.execute("SELECT art FROM belege ORDER BY belegnummer")]
    assert arten == ["Startbeleg", "Barumsatz", "Sammelbeleg", "Barumsatz"]
    assert not kasse.ausfall_aktiv()


def test_startbeleg_braucht_signatur(kasse, signer):
    signer.verfuegbar = False
    with pytest.raises(Exception):
        kasse.startbeleg()
    assert not kasse.ist_gestartet()


def test_schlussbeleg_beendet_kasse(kasse):
    kasse.startbeleg()
    kasse.schlussbeleg()
    with pytest.raises(KassenFehler):
        kasse.verkauf([_pos()])


def test_dep_export(kasse):
    kasse.startbeleg()
    kasse.verkauf([_pos()])
    dep = dep_export(kasse.con)
    assert len(dep["Belege-Gruppe"]) == 1
    g = dep["Belege-Gruppe"][0]
    assert g["Signaturzertifikat"] and len(g["Belege-kompakt"]) == 2


def test_qr_inhalt(kasse):
    b = kasse.startbeleg()
    qr = kasse.qr_inhalt(b)
    assert qr.startswith("_R1-AT0_KASSE-01_1_")
    assert len(base64.b64decode(qr.rsplit("_", 1)[1])) == 64
