"""Unabhängige Prüfung eines DEP-Exports (Datenerfassungsprotokoll) nach RKSV.

Prüft – ähnlich der BMF-Belegcheck-App, aber für das ganze Protokoll:
  * Signatur jedes Belegs gegen das Signaturzertifikat (ES256)
  * Verkettung (Sig-Voriger-Beleg) lückenlos ab dem Startbeleg
  * Belegnummern eindeutig
  * Umsatzzähler: entschlüsselt (AES-256-ICM) und mit der laufenden Summe verglichen
  * Kennzeichnung von Training (TRA), Storno (STO) und Ausfall

Aufruf:
    python tools/dep_pruefen.py dep-export.json --aes <AES-Schlüssel Base64>
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from kasse.rksv import krypto  # noqa: E402
from kasse.rksv.signatur import pruefe_jws  # noqa: E402


def _cent(t: str) -> int:
    neg = t.startswith("-")
    e, c = t.lstrip("-").split(",")
    return (-1 if neg else 1) * (int(e) * 100 + int(c))


def pruefen(dep: dict, aes: str | None = None) -> tuple[list[str], dict]:
    fehler: list[str] = []
    stat = {"belege": 0, "signiert": 0, "ausfall": 0, "training": 0, "storno": 0}
    vorher: str | None = None
    kassen_id: str | None = None
    summe = 0
    nummern: set[str] = set()
    for gruppe in dep.get("Belege-Gruppe", []):
        zert = gruppe.get("Signaturzertifikat")
        for jws in gruppe.get("Belege-kompakt", []):
            stat["belege"] += 1
            try:
                _, payload, signatur = krypto.jws_teile(jws)
            except Exception:
                fehler.append(f"Beleg {stat['belege']}: JWS nicht lesbar")
                continue
            t = payload.split("_")
            if len(t) != 13 or t[0] != "" or not t[1].startswith("R1-"):
                fehler.append(f"Beleg {stat['belege']}: Belegformat ungültig ({len(t)} Felder)")
                continue
            kid, nr, zeit, betraege, zaehler, serie, kette = t[2], t[3], t[4], t[5:10], t[10], t[11], t[12]
            if kassen_id is None:
                kassen_id = kid
            if kid != kassen_id:
                fehler.append(f"Beleg {nr}: andere Kassen-ID {kid}")
            if nr in nummern:
                fehler.append(f"Beleg {nr}: Belegnummer doppelt")
            nummern.add(nr)
            soll_kette = krypto.kettenwert(vorher if vorher else kid)
            if kette != soll_kette:
                fehler.append(f"Beleg {nr}: Verkettung falsch ({kette} statt {soll_kette})")
            if signatur == krypto.AUSFALL_TEXT.encode():
                stat["ausfall"] += 1
            elif zert and pruefe_jws(jws, zert):
                stat["signiert"] += 1
            else:
                fehler.append(f"Beleg {nr}: Signatur ungültig")
            betrag = sum(_cent(b) for b in betraege)
            if zaehler == krypto.TRAINING_MARKER:
                stat["training"] += 1
            else:
                summe += betrag
                if zaehler == krypto.STORNO_MARKER:
                    stat["storno"] += 1
                elif aes:
                    wert = krypto.umsatzzaehler_entschluesseln(zaehler, kid, nr, aes)
                    if wert != summe:
                        fehler.append(f"Beleg {nr}: Umsatzzähler {wert} ≠ laufende Summe {summe}")
            vorher = jws
    stat["umsatz_cent"] = summe
    return fehler, stat


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("datei")
    ap.add_argument("--aes", help="AES-Schlüssel (Base64) für die Prüfung des Umsatzzählers")
    a = ap.parse_args()
    dep = json.loads(pathlib.Path(a.datei).read_text(encoding="utf-8"))
    fehler, stat = pruefen(dep, a.aes)
    print(f"Belege: {stat['belege']}  signiert: {stat['signiert']}  Ausfall: {stat['ausfall']}  "
          f"Training: {stat['training']}  Storno: {stat['storno']}  Umsatzzähler: {stat['umsatz_cent'] / 100:.2f} €")
    for f in fehler:
        print("FEHLER:", f)
    print("Ergebnis:", "OK – Belegkette vollständig und gültig" if not fehler else f"{len(fehler)} Fehler")
    return 1 if fehler else 0


if __name__ == "__main__":
    sys.exit(main())
