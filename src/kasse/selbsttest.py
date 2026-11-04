"""Selbsttest des installierten Programms (``kasse-cli selbsttest``).

Spielt alle Ausgabewege mit einer temporären Testkasse durch – die echte
Kassendatenbank wird dabei nicht berührt. Gedacht für die Kontrolle nach der
Installation bzw. nach einem Update und für den automatischen Build-Test.
"""

from __future__ import annotations

import base64
import io
import tempfile
import traceback
import zipfile
from decimal import Decimal
from pathlib import Path


def _logo() -> str:
    from PIL import Image

    puffer = io.BytesIO()
    Image.new("RGB", (120, 40), (59, 91, 253)).save(puffer, "PNG")
    return "data:image/png;base64," + base64.b64encode(puffer.getvalue()).decode()


def ausfuehren(ausgabe=print) -> bool:
    from . import __version__, db, dokumente, ebinterface, export, sicherung
    from .rksv import Kasse, LokalerTestSigner, Position
    from .rksv.dep import dep_export

    ergebnisse: list[tuple[str, bool, str]] = []

    def schritt(name, f):
        try:
            info = f()
            ergebnisse.append((name, True, info or ""))
        except Exception as e:  # jeden Fehler melden, nicht abbrechen
            ergebnisse.append((name, False, f"{type(e).__name__}: {e}"))
            traceback.print_exc()

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        con = db.verbinden(tmp / "selbsttest.db")
        Kasse.einrichten(con, "SELBSTTEST")
        for k, v in {"firma_name": "Selbsttest GmbH", "firma_adresse": "Teststraße 1\n1010 Wien",
                     "firma_uid": "ATU00000000", "firma_iban": "AT611904300234573201", "firma_bic": "BKAUATWW",
                     "firma_logo": _logo(), "bon_logo": "1"}.items():
            db.setze_einstellung(con, k, v)
        con.commit()
        kasse = Kasse(con, LokalerTestSigner())
        kunde = con.execute("INSERT INTO kunden (name, adresse, uid) VALUES ('Kunde', 'Weg 2\n4020 Linz', 'ATU1')").lastrowid
        beleg = {}

        def belege():
            kasse.startbeleg()
            beleg["id"] = kasse.verkauf([Position("Kaffee", Decimal(2), 300, "20", rabatt_cent=30),
                                         Position("Kuchen", Decimal(1), 420, "10")],
                                        zahlungen=[("Bar", 300, None), ("Karte", 690, None)])
            return "Startbeleg + Verkauf signiert"

        def bon():
            from escpos.printer import Dummy

            from .printing.bon import drucke_bon

            d = Dummy()
            drucke_bon(con, beleg["id"], d)
            return f"{len(d.output)} Byte ESC/POS inkl. QR-Code und Logo"

        def pdf_beleg():
            from .printing.a4 import beleg_pdf

            p = beleg_pdf(con, beleg["id"], tmp / "beleg.pdf")
            assert p.read_bytes().startswith(b"%PDF")
            return f"{p.stat().st_size} Byte"

        def pdf_rechnung():
            from .printing.a4 import dokument_pdf

            pos = [dokumente.DokPosition("Ware", Decimal(3), 1990, "20")]
            ls = dokumente.lieferschein(con, kunde, pos)
            re_ = dokumente.rechnung_aus_lieferscheinen(con, [ls])
            for i in (ls, re_):
                assert dokument_pdf(con, i, tmp / f"dok{i}.pdf").read_bytes().startswith(b"%PDF")
            beleg["rechnung"] = re_
            return "Lieferschein + Rechnung mit Zahlungs-QR"

        def briefpapier():
            from reportlab.lib.pagesizes import A4
            from reportlab.pdfgen import canvas

            from .printing.a4 import muster_pdf

            puffer = io.BytesIO()
            c = canvas.Canvas(puffer, pagesize=A4)
            c.drawString(40, 800, "Briefpapier-Test")
            c.save()
            db.setze_einstellung(con, "a4_briefpapier_erste",
                                 "data:application/pdf;base64," + base64.b64encode(puffer.getvalue()).decode())
            p = muster_pdf(con, "Rechnung", tmp / "muster.pdf")
            db.setze_einstellung(con, "a4_briefpapier_erste", "")
            con.commit()
            return f"PDF-Briefpapier hinterlegt ({p.stat().st_size} Byte)"

        def erechnung():
            p = ebinterface.erzeugen(con, beleg["rechnung"], tmp / "re.xml")
            return f"{p.stat().st_size} Byte"

        def steuerberater():
            p = export.paket(con, "2000-01-01", "2999-12-31", tmp / "export.zip")
            with zipfile.ZipFile(p) as z:
                return ", ".join(z.namelist())

        def sicherung_():
            ziel = tmp / "sich"
            ziel.mkdir()
            a = sicherung.sichern(con, ziel, passwort="selbsttest")
            sicherung.wiederherstellen(a, tmp / "wieder.db", "selbsttest")
            return "verschlüsselt gesichert und wiederhergestellt"

        def belegkette():
            from .rksv import krypto

            jws = dep_export(con)["Belege-Gruppe"][0]["Belege-kompakt"]
            vorher = "SELBSTTEST"
            for j in jws:
                assert j.split(".")[1] and krypto.jws_teile(j)[1].split("_")[-1] == krypto.kettenwert(vorher)
                vorher = j
            return f"{len(jws)} Belege lückenlos verkettet"

        def passwortspeicher():
            from . import geheim

            return "verfügbar" if geheim._keyring() is not None else "NICHT verfügbar (Passwörter nur über Umgebungsvariablen)"

        for name, f in [("Belege signieren", belege), ("Bon (ESC/POS)", bon), ("A4-Beleg als PDF", pdf_beleg),
                        ("Lieferschein/Rechnung als PDF", pdf_rechnung), ("Briefpapier", briefpapier),
                        ("E-Rechnung ebInterface", erechnung),
                        ("Export Steuerberater", steuerberater), ("Sicherung", sicherung_),
                        ("Belegkette", belegkette), ("Passwortspeicher", passwortspeicher)]:
            schritt(name, f)
        con.close()

    ausgabe(f"Selbsttest Registrierkasse {__version__}")
    for name, ok, info in ergebnisse:
        ausgabe(f"  {'OK    ' if ok else 'FEHLER'} {name}: {info}")
    gut = all(ok for _, ok, _ in ergebnisse)
    ausgabe("Ergebnis: " + ("alles in Ordnung" if gut else "FEHLER – siehe oben"))
    return gut


if __name__ == "__main__":
    raise SystemExit(0 if ausfuehren() else 1)
