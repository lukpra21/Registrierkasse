"""Signaturerstellungseinheiten.

- ATrustOnlineSigner: A-Trust a.sign RK Online (digitale Lizenz, HSM bei A-Trust)
- LokalerTestSigner: lokaler ES256-Schlüssel – NUR für Entwicklung und Tests,
  nicht für den Echtbetrieb zulässig (Zertifikat stammt von keinem ZDA).
"""

from __future__ import annotations

import base64
import datetime as dt
import hashlib
import json
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Protocol

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import (
    decode_dss_signature,
    encode_dss_signature,
)
from cryptography.x509.oid import NameOID

from .krypto import b64url, b64url_decode, jws_signing_input


class SignaturFehler(RuntimeError):
    """Signaturerstellungseinheit nicht erreichbar oder Antwort ungültig."""


@dataclass
class ZertifikatInfo:
    seriennummer: str  # so wie sie im Beleg erscheint
    zertifikat_b64: str  # DER, Base64
    zertifizierungsstellen: list[str] = field(default_factory=list)


class Signer(Protocol):
    zda_id: str  # "AT1" = A-Trust, "AT0" = Test/ohne ZDA

    def zertifikat(self) -> ZertifikatInfo: ...

    def signiere_jws(self, payload: str) -> str:
        """Liefert den kompakten JWS (header.payload.signatur)."""
        ...


# --------------------------------------------------------------------------- A-Trust


ATRUST_PRODUKTIV = "https://www.a-trust.at/asignrkonline/v2"
ATRUST_TEST = "https://hs-abnahme.a-trust.at/asignrkonline/v2"


class ATrustOnlineSigner:
    """Anbindung an die A-Trust a.sign RK Online REST-Schnittstelle.

    Endpunkte (v2):
      GET  {basis}/{benutzer}/Certificate
      POST {basis}/{benutzer}/Sign/JWS   {"password": ..., "jws_payload": ...}

    Benutzername/Passwort stammen aus der A-Trust-Lizenz. Endpunkte und
    Feldnamen vor dem Echtbetrieb gegen die aktuelle A-Trust-Dokumentation
    prüfen – zuerst mit der Testumgebung (ATRUST_TEST) arbeiten.
    """

    zda_id = "AT1"

    def __init__(self, benutzer: str, passwort: str, basis_url: str = ATRUST_PRODUKTIV, timeout: float = 10.0):
        self.benutzer = benutzer
        self._passwort = passwort
        self.basis_url = basis_url.rstrip("/")
        self.timeout = timeout
        self._zert: ZertifikatInfo | None = None

    def _anfrage(self, methode: str, pfad: str, daten: dict | None = None) -> dict:
        url = f"{self.basis_url}/{self.benutzer}/{pfad}"
        body = json.dumps(daten).encode() if daten is not None else None
        req = urllib.request.Request(url, data=body, method=methode)
        req.add_header("Accept", "application/json")
        if body is not None:
            req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read().decode())
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as e:
            raise SignaturFehler(f"A-Trust nicht erreichbar: {e}") from e

    def zertifikat(self) -> ZertifikatInfo:
        if self._zert is None:
            d = self._anfrage("GET", "Certificate")
            try:
                serie = d.get("ZertifikatsseriennummerHex") or d["Zertifikatsseriennummer"]
                self._zert = ZertifikatInfo(
                    seriennummer=str(serie),
                    zertifikat_b64=d["Signaturzertifikat"],
                    zertifizierungsstellen=list(d.get("Zertifizierungsstellen", [])),
                )
            except KeyError as e:
                raise SignaturFehler(f"Unerwartete Zertifikatsantwort von A-Trust: {d}") from e
        return self._zert

    def signiere_jws(self, payload: str) -> str:
        d = self._anfrage("POST", "Sign/JWS", {"password": self._passwort, "jws_payload": payload})
        jws = d.get("result")
        if not jws or jws.count(".") != 2:
            raise SignaturFehler(f"Ungültige Signaturantwort von A-Trust: {d}")
        return jws


# --------------------------------------------------------------------------- Test


class LokalerTestSigner:
    """Lokaler Signierschlüssel für Entwicklung/Tests (ZDA-ID AT0)."""

    zda_id = "AT0"

    def __init__(self, privat_pem: bytes | None = None):
        if privat_pem:
            self._key = serialization.load_pem_private_key(privat_pem, password=None)
        else:
            self._key = ec.generate_private_key(ec.SECP256R1())
        self._zert: ZertifikatInfo | None = None

    def privat_pem(self) -> bytes:
        return self._key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )

    def zertifikat(self) -> ZertifikatInfo:
        if self._zert is None:
            pub = self._key.public_key()
            serie = int.from_bytes(
                hashlib.sha256(
                    pub.public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
                ).digest()[:8],
                "big",
            )
            name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Registrierkasse TEST – nicht gültig")])
            jetzt = dt.datetime.now(dt.timezone.utc)
            cert = (
                x509.CertificateBuilder()
                .subject_name(name)
                .issuer_name(name)
                .public_key(pub)
                .serial_number(serie or 1)
                .not_valid_before(jetzt - dt.timedelta(days=1))
                .not_valid_after(jetzt + dt.timedelta(days=3650))
                .sign(self._key, hashes.SHA256())
            )
            self._zert = ZertifikatInfo(
                seriennummer=format(cert.serial_number, "x"),
                zertifikat_b64=base64.b64encode(cert.public_bytes(serialization.Encoding.DER)).decode(),
            )
        return self._zert

    def signiere_jws(self, payload: str) -> str:
        eingabe = jws_signing_input(payload)
        der = self._key.sign(eingabe.encode(), ec.ECDSA(hashes.SHA256()))
        r, s = decode_dss_signature(der)
        roh = r.to_bytes(32, "big") + s.to_bytes(32, "big")
        return f"{eingabe}.{b64url(roh)}"


def pruefe_jws(jws: str, zertifikat_b64: str) -> bool:
    """Prüft eine ES256-JWS-Signatur gegen ein Zertifikat (DER, Base64)."""
    from cryptography.exceptions import InvalidSignature

    cert = x509.load_der_x509_certificate(base64.b64decode(zertifikat_b64))
    kopf, nutz, sig = jws.split(".")
    roh = b64url_decode(sig)
    if len(roh) != 64:
        return False
    der = encode_dss_signature(int.from_bytes(roh[:32], "big"), int.from_bytes(roh[32:], "big"))
    try:
        cert.public_key().verify(der, f"{kopf}.{nutz}".encode(), ec.ECDSA(hashes.SHA256()))
        return True
    except InvalidSignature:
        return False


def signer_aus_einstellungen(con) -> Signer:
    """Baut den Signer anhand der gespeicherten Einstellungen.

    Das A-Trust-Passwort wird NICHT in der Datenbank gespeichert, sondern in der
    Windows-Anmeldeinformationsverwaltung (bzw. Umgebungsvariable KASSE_ATRUST_PASSWORT).
    """
    from .. import geheim
    from ..db import einstellung

    art = einstellung(con, "signer", "test")
    if art == "atrust":
        benutzer = einstellung(con, "atrust_benutzer")
        passwort = geheim.lesen("atrust")
        if not benutzer or not passwort:
            raise SignaturFehler("A-Trust-Benutzer oder -Passwort fehlt (Einstellungen → A-Trust)")
        basis = ATRUST_TEST if einstellung(con, "atrust_umgebung", "produktiv") == "test" else ATRUST_PRODUKTIV
        return ATrustOnlineSigner(benutzer, passwort, basis)
    pem = einstellung(con, "test_signer_pem")
    signer = LokalerTestSigner(pem.encode() if pem else None)
    if not pem:
        from ..db import setze_einstellung

        setze_einstellung(con, "test_signer_pem", signer.privat_pem().decode())
        con.commit()
    return signer


def signer_testen(signer: Signer) -> dict:
    """Verbindungstest: Zertifikat abrufen, Testdaten signieren, Signatur prüfen."""
    z = signer.zertifikat()
    jws = signer.signiere_jws("_R1-TEST_Verbindungstest")
    return {"seriennummer": z.seriennummer, "signatur_gueltig": pruefe_jws(jws, z.zertifikat_b64),
            "zertifizierungsstellen": len(z.zertifizierungsstellen)}
