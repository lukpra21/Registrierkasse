"""Lizenzwerkzeug für den Hersteller (NICHT an Kunden ausliefern).

    python tools/lizenz.py init  --privat C:\\Sicher\\lizenz_privat.pem
        erzeugt ein Schlüsselpaar; der öffentliche Schlüssel wird nach
        src/kasse/lizenz_public.pem geschrieben (wird mit ausgeliefert),
        der private bleibt beim Hersteller.

    python tools/lizenz.py ausstellen --privat C:\\Sicher\\lizenz_privat.pem \\
        --kunde "Café Muster GmbH" --uid ATU12345678 --bis 2027-12-31
        gibt den Lizenzschlüssel aus (in der Kasse unter Einstellungen eintragen).
"""

import argparse
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from cryptography.hazmat.primitives import serialization  # noqa: E402
from cryptography.hazmat.primitives.asymmetric import ed25519  # noqa: E402

from kasse import lizenz  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="befehl", required=True)
    p = sub.add_parser("init")
    p.add_argument("--privat", required=True)
    p = sub.add_parser("ausstellen")
    p.add_argument("--privat", required=True)
    p.add_argument("--kunde", required=True)
    p.add_argument("--uid", default="")
    p.add_argument("--bis", required=True, help="JJJJ-MM-TT")
    a = ap.parse_args()

    if a.befehl == "init":
        privat = pathlib.Path(a.privat)
        if privat.exists():
            print(f"{privat} existiert bereits – nicht überschrieben", file=sys.stderr)
            return 1
        key = ed25519.Ed25519PrivateKey.generate()
        privat.write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                             serialization.NoEncryption()))
        lizenz.PUBLIC_PEM.write_bytes(key.public_key().public_bytes(serialization.Encoding.PEM,
                                                                    serialization.PublicFormat.SubjectPublicKeyInfo))
        print(f"Privater Schlüssel: {privat} (sicher verwahren!)\nÖffentlicher Schlüssel: {lizenz.PUBLIC_PEM}")
    else:
        print(lizenz.ausstellen(pathlib.Path(a.privat).read_bytes(), a.kunde, a.uid, a.bis))
    return 0


if __name__ == "__main__":
    sys.exit(main())
