"""Kryptografische Bausteine laut RKSV-Detailspezifikation.

- Umsatzzähler: AES-256-ICM (= CTR), IV = erste 16 Byte von SHA-256(Kassen-ID || Belegnummer)
- Verkettung: Base64 der ersten 8 Byte von SHA-256(JWS des Vorbelegs bzw. Kassen-ID beim Startbeleg)
- JWS: Compact Serialization mit ES256
"""

from __future__ import annotations

import base64
import hashlib
import os

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

#: Länge des verschlüsselten Umsatzzählers in Byte (zulässig: 5–16)
UMSATZZAEHLER_BYTES = 8

TRAINING_MARKER = base64.b64encode(b"TRA").decode()  # "VFJB"
STORNO_MARKER = base64.b64encode(b"STO").decode()  # "U1RP"
AUSFALL_TEXT = "Sicherheitseinrichtung ausgefallen"

JWS_HEADER = '{"alg":"ES256"}'


def b64url(daten: bytes) -> str:
    return base64.urlsafe_b64encode(daten).rstrip(b"=").decode()


def b64url_decode(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def neuer_aes_schluessel() -> str:
    """Erzeugt einen AES-256-Schlüssel (Base64), der in FinanzOnline registriert wird."""
    return base64.b64encode(os.urandom(32)).decode()


def pruefwert(aes_schluessel_b64: str) -> str:
    """Prüfwert für die Registrierung des AES-Schlüssels in FinanzOnline.

    Base64 (ohne '=') der ersten 3 Byte von SHA-256 über den Base64-codierten Schlüssel.
    FinanzOnline prüft den Wert bei der Eingabe – ein Fehler fällt dort sofort auf.
    """
    h = hashlib.sha256(aes_schluessel_b64.encode()).digest()[:3]
    return base64.b64encode(h).decode().rstrip("=")


def _iv(kassen_id: str, belegnummer: str) -> bytes:
    return hashlib.sha256((kassen_id + belegnummer).encode("utf-8")).digest()[:16]


def _aes_ctr(schluessel: bytes, iv: bytes, block: bytes) -> bytes:
    cipher = Cipher(algorithms.AES(schluessel), modes.CTR(iv))
    enc = cipher.encryptor()
    return enc.update(block) + enc.finalize()


def umsatzzaehler_verschluesseln(
    umsatz_cent: int, kassen_id: str, belegnummer: str, aes_schluessel_b64: str
) -> str:
    schluessel = base64.b64decode(aes_schluessel_b64)
    if len(schluessel) != 32:
        raise ValueError("AES-Schlüssel muss 256 Bit lang sein")
    # N Byte Zweierkomplement (big-endian), rechts auf 16 Byte mit Nullen aufgefüllt
    klartext = umsatz_cent.to_bytes(UMSATZZAEHLER_BYTES, "big", signed=True) + bytes(16 - UMSATZZAEHLER_BYTES)
    chiffre = _aes_ctr(schluessel, _iv(kassen_id, belegnummer), klartext)
    return base64.b64encode(chiffre[:UMSATZZAEHLER_BYTES]).decode()


def umsatzzaehler_entschluesseln(
    wert_b64: str, kassen_id: str, belegnummer: str, aes_schluessel_b64: str
) -> int:
    schluessel = base64.b64decode(aes_schluessel_b64)
    chiffre = base64.b64decode(wert_b64)
    n = len(chiffre)
    klartext = _aes_ctr(schluessel, _iv(kassen_id, belegnummer), chiffre + bytes(16 - n))[:n]
    return int.from_bytes(klartext, "big", signed=True)


def kettenwert(vorgaenger: str) -> str:
    """vorgaenger = JWS des Vorbelegs (kompakt) bzw. Kassen-ID beim Startbeleg."""
    return base64.b64encode(hashlib.sha256(vorgaenger.encode("utf-8")).digest()[:8]).decode()


def jws_signing_input(payload: str) -> str:
    return f"{b64url(JWS_HEADER.encode())}.{b64url(payload.encode('utf-8'))}"


def ausfall_jws(payload: str) -> str:
    return f"{jws_signing_input(payload)}.{b64url(AUSFALL_TEXT.encode())}"


def jws_teile(jws: str) -> tuple[str, str, bytes]:
    header, payload, signatur = jws.split(".")
    return (
        b64url_decode(header).decode(),
        b64url_decode(payload).decode("utf-8"),
        b64url_decode(signatur),
    )


def maschinenlesbarer_code(jws: str) -> str:
    """Inhalt des QR-Codes: Belegdaten + '_' + Signatur (Base64, nicht URL-safe)."""
    _, payload, signatur = jws_teile(jws)
    return f"{payload}_{base64.b64encode(signatur).decode()}"
