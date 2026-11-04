import datetime as dt

import pytest

from kasse import db
from kasse.rksv import Kasse, LokalerTestSigner, SignaturFehler


class Uhr:
    def __init__(self):
        self.t = dt.datetime(2026, 11, 4, 9, 0, 0)

    def __call__(self):
        self.t += dt.timedelta(seconds=1)
        return self.t


class AusfallSigner(LokalerTestSigner):
    """Test-Signer, dessen Verfügbarkeit sich umschalten lässt."""

    def __init__(self):
        super().__init__()
        self.verfuegbar = True

    def signiere_jws(self, payload):
        if not self.verfuegbar:
            raise SignaturFehler("simulierter Ausfall")
        return super().signiere_jws(payload)


@pytest.fixture
def con(tmp_path):
    c = db.verbinden(tmp_path / "kasse.db")
    yield c
    c.close()


@pytest.fixture
def signer():
    return AusfallSigner()


@pytest.fixture
def kasse(con, signer):
    Kasse.einrichten(con, "KASSE-01")
    db.setze_einstellung(con, "firma_name", "Muster GmbH")
    db.setze_einstellung(con, "firma_adresse", "Hauptstraße 1\n1010 Wien")
    db.setze_einstellung(con, "firma_uid", "ATU12345678")
    con.commit()
    return Kasse(con, signer, uhr=Uhr())
