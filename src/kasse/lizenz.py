"""Lizenzschlüssel (Ed25519-signiert) für den Vertrieb an mehrere Betriebe.

Format:  <Base64URL(JSON-Nutzdaten)>.<Base64URL(Signatur)>
Nutzdaten: {"kunde": "...", "uid": "ATU…", "gueltig_bis": "JJJJ-MM-TT", "ausgestellt": "JJJJ-MM-TT"}

Der öffentliche Schlüssel liegt in ``lizenz_public.pem`` neben diesem Modul
(erzeugt mit ``python tools/lizenz.py init``). Der private Schlüssel bleibt beim
Hersteller und gehört NIE ins Repository.

Wichtig: Eine fehlende oder abgelaufene Lizenz blockiert die Kasse nie – sonst
könnten RKSV-Pflichten (Monatsbeleg, DEP-Export) nicht erfüllt werden. Es wird
nur ein Hinweis angezeigt.
"""

from __future__ import annotations

import base64
import datetime as dt
import json
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization

PUBLIC_PEM = Path(__file__).with_name("lizenz_public.pem")


def _b64d(t: str) -> bytes:
    return base64.urlsafe_b64decode(t + "=" * (-len(t) % 4))


def _b64e(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def ausstellen(privat_pem: bytes, kunde: str, uid: str, gueltig_bis: str) -> str:
    key = serialization.load_pem_private_key(privat_pem, password=None)
    nutz = json.dumps({"kunde": kunde, "uid": uid, "gueltig_bis": gueltig_bis,
                       "ausgestellt": dt.date.today().isoformat()}, ensure_ascii=False, separators=(",", ":")).encode()
    return f"{_b64e(nutz)}.{_b64e(key.sign(nutz))}"


def pruefen(schluessel: str | None, public_pem: bytes | None = None) -> dict:
    if public_pem is None:
        if not PUBLIC_PEM.exists():
            return {"status": "ohne_pruefung", "text": "Lizenzprüfung nicht aktiviert"}
        public_pem = PUBLIC_PEM.read_bytes()
    if not schluessel:
        return {"status": "fehlt", "text": "Keine Lizenz eingetragen"}
    try:
        teil_n, teil_s = schluessel.strip().split(".")
        nutz = _b64d(teil_n)
        serialization.load_pem_public_key(public_pem).verify(_b64d(teil_s), nutz)
        daten = json.loads(nutz)
    except (ValueError, InvalidSignature, json.JSONDecodeError):
        return {"status": "ungueltig", "text": "Lizenzschlüssel ungültig"}
    if daten.get("gueltig_bis", "9999-12-31") < dt.date.today().isoformat():
        return {"status": "abgelaufen", "text": f"Lizenz abgelaufen am {daten['gueltig_bis']}", **daten}
    return {"status": "gueltig", "text": f"Lizenziert für {daten.get('kunde')} bis {daten.get('gueltig_bis')}", **daten}
