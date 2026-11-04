"""Kommandozeile – für Einrichtung, Import, Sicherung und Tests (die Kassenoberfläche folgt separat)."""

from __future__ import annotations

import argparse
import sys
from decimal import Decimal
from pathlib import Path

from . import config, db, sicherung
from .geld import anzeige
from .rksv import Kasse, KassenFehler, Position, SignaturFehler
from .rksv.dep import dep_export_datei
from .rksv.krypto import pruefwert
from .rksv.signatur import signer_aus_einstellungen


def _con(args):
    return db.verbinden(args.datenbank or config.datenbankpfad())


def cmd_init(args):
    con = _con(args)
    schluessel = Kasse.einrichten(con, args.kassen_id)
    db.setze_einstellung(con, "signer", args.signer)
    if args.signer == "atrust":
        db.setze_einstellung(con, "atrust_benutzer", args.atrust_benutzer or "")
        db.setze_einstellung(con, "atrust_umgebung", args.atrust_umgebung)
    con.commit()
    if args.signer == "atrust":
        print("A-Trust-Passwort danach mit 'kasse passwort atrust' speichern.")
    print(f"Kasse '{args.kassen_id}' eingerichtet.")
    print("Für die Registrierung in FinanzOnline:")
    print(f"  AES-Schlüssel: {schluessel}")
    print(f"  Prüfwert:      {pruefwert(schluessel)}")


def cmd_info(args):
    con = _con(args)
    for k in ("kassen_id", "signer", "atrust_benutzer", "atrust_umgebung", "zertifikat_serie",
              "firma_name", "firma_uid", "sicherung_ziel", "sicherung_zuletzt", "ausfall_seit"):
        print(f"{k:18} {db.einstellung(con, k, '-')}")
    if s := db.einstellung(con, "aes_schluessel"):
        print(f"{'aes_pruefwert':18} {pruefwert(s)}")
    print(f"{'artikel':18} {con.execute('SELECT COUNT(*) FROM artikel').fetchone()[0]}")
    print(f"{'belege':18} {con.execute('SELECT COUNT(*) FROM belege').fetchone()[0]}")


def cmd_set(args):
    con = _con(args)
    db.setze_einstellung(con, args.schluessel, args.wert.replace("\\n", "\n"))
    con.commit()


def cmd_import_qrk(args):
    from .importer import qrk

    if args.inspizieren:
        print(qrk.inspiziere(args.quelle))
        return
    con = _con(args)
    bericht = qrk.importiere(args.quelle, con, probelauf=args.probelauf, nur_sichtbare=args.nur_sichtbare)
    print(("PROBELAUF – nichts geschrieben\n" if args.probelauf else "") + bericht.text())


def _kasse(args) -> Kasse:
    con = _con(args)
    return Kasse(con, signer_aus_einstellungen(con))


def _drucken(args, kasse: Kasse, beleg_id: int):
    from .printing.bon import bon_text, drucke_bon

    if args.drucken:
        drucke_bon(kasse.con, beleg_id)
    else:
        print("".join(bon_text(kasse.con, beleg_id)))
        print("QR:", kasse.qr_inhalt(beleg_id))


def cmd_startbeleg(args):
    k = _kasse(args)
    _drucken(args, k, k.startbeleg())


def cmd_nullbeleg(args):
    k = _kasse(args)
    beleg = k.nullbeleg(args.art)
    _drucken(args, k, beleg)
    if args.art in ("Monatsbeleg", "Jahresbeleg"):
        print("Sicherung:", sicherung.sichern(k.con))


def cmd_verkauf(args):
    k = _kasse(args)
    pos = []
    for eintrag in args.artikel:
        nr, _, menge = eintrag.partition(":")
        a = k.con.execute("SELECT * FROM artikel WHERE artikelnummer = ? OR barcode = ?", (nr, nr)).fetchone()
        if not a:
            raise KassenFehler(f"Artikel {nr} nicht gefunden")
        pos.append(Position(a["name"], Decimal(menge or "1"), a["brutto_cent"], a["steuer_prozent"], a["id"]))
    _drucken(args, k, k.verkauf(pos, args.zahlungsart, training=args.training))


def cmd_dep(args):
    print(dep_export_datei(_con(args), args.ziel))


def cmd_sicherung(args):
    con = _con(args)
    print(sicherung.sichern(con, Path(args.ziel) if args.ziel else None))


def cmd_sicherung_planen(args):
    print("Geplant:", sicherung.windows_aufgabe_planen(args.uhrzeit))


def cmd_artikel(args):
    con = _con(args)
    for r in con.execute(
        "SELECT a.artikelnummer, a.name, a.brutto_cent, a.steuer_prozent, g.name AS gruppe FROM artikel a"
        " LEFT JOIN warengruppen g ON g.id = a.warengruppe_id ORDER BY g.name, a.name"
    ):
        print(f"{r['artikelnummer'] or '-':>8}  {r['name'][:40]:40} {anzeige(r['brutto_cent']):>10}  {r['steuer_prozent']:>3} %  {r['gruppe'] or ''}")


def cmd_atrust_test(args):
    from .rksv.signatur import signer_testen

    con = _con(args)
    r = signer_testen(signer_aus_einstellungen(con))
    print(f"Zertifikat-Seriennummer: {r['seriennummer']}")
    print(f"Signatur gültig:         {'ja' if r['signatur_gueltig'] else 'NEIN'}")
    return 0 if r["signatur_gueltig"] else 1


def cmd_passwort(args):
    import getpass

    from . import geheim

    geheim.schreiben(args.name, getpass.getpass(f"{args.name}-Passwort: "))
    print("Gespeichert (Windows-Anmeldeinformationsverwaltung).")


def cmd_export(args):
    from . import export

    print(export.paket(_con(args), args.von, args.bis, args.ziel))


def cmd_wiederherstellen(args):
    import getpass

    from . import geheim, sicherung

    pfad = Path(args.datenbank or config.datenbankpfad())
    daten = Path(args.datei).read_bytes()
    pw = args.passwort or geheim.lesen("sicherung")
    if daten.startswith(sicherung.MAGIC) and not pw:
        pw = getpass.getpass("Sicherungspasswort: ")
    inhalt = sicherung.archiv_lesen(daten, pw)
    info = sicherung.datenbank_info(inhalt)
    aktuell = {}
    if pfad.exists():
        c = db.verbinden(pfad)
        aktuell = sicherung.aktuelle_info(c)
        c.close()  # unter Windows muss die Datei frei sein, bevor sie ersetzt wird
    print(f"Sicherung: Kasse {info['kassen_id']} · {info['firma'] or '-'} · {info['belege']} Belege "
          f"(letzter Nr. {info['letzte_belegnummer']}, {info['letzter_beleg'] or '-'})")
    for w in sicherung.vergleich_warnungen(aktuell, info):
        print("WARNUNG:", w)
    if not args.ja and input("Jetzt wiederherstellen? [j/N] ").strip().lower() not in ("j", "ja"):
        print("Abgebrochen.")
        return 1
    alt = sicherung.datenbank_ersetzen(inhalt, pfad)
    db.verbinden(pfad).close()
    print("Wiederhergestellt." + (f" Bisherige Datenbank aufgehoben: {alt}" if alt else ""))
    return 0


def cmd_selbsttest(args):
    from .selbsttest import ausfuehren

    return 0 if ausfuehren() else 1


def main(argv=None):
    ap = argparse.ArgumentParser(prog="kasse", description="Registrierkasse (RKSV)")
    ap.add_argument("--datenbank", help="Pfad zur Kassendatenbank (Standard: Benutzer-Datenverzeichnis)")
    sub = ap.add_subparsers(dest="befehl", required=True)

    p = sub.add_parser("init", help="Kasse einrichten")
    p.add_argument("kassen_id")
    p.add_argument("--signer", choices=["test", "atrust"], default="test")
    p.add_argument("--atrust-benutzer")
    p.add_argument("--atrust-umgebung", choices=["test", "produktiv"], default="test")
    p.set_defaults(f=cmd_init)

    sub.add_parser("info", help="Status anzeigen").set_defaults(f=cmd_info)

    p = sub.add_parser("set", help="Einstellung setzen (z. B. firma_iban, bondrucker_name, sicherung_ziel)")
    p.add_argument("schluessel")
    p.add_argument("wert")
    p.set_defaults(f=cmd_set)

    p = sub.add_parser("import-qrk", help="Firmendaten, Steuersätze und Artikel aus QRK-Sicherung übernehmen")
    p.add_argument("quelle")
    p.add_argument("--probelauf", action="store_true", help="nur anzeigen, nichts schreiben")
    p.add_argument("--inspizieren", action="store_true", help="nur Tabellen/Spalten anzeigen")
    p.add_argument("--nur-sichtbare", action="store_true", help="ausgeblendete QRK-Artikel nicht übernehmen")
    p.set_defaults(f=cmd_import_qrk)

    sub.add_parser("artikel", help="Artikelliste").set_defaults(f=cmd_artikel)

    for name, f in (("startbeleg", cmd_startbeleg),):
        p = sub.add_parser(name)
        p.add_argument("--drucken", action="store_true")
        p.set_defaults(f=f)

    p = sub.add_parser("nullbeleg")
    p.add_argument("--art", default="Nullbeleg",
                   choices=["Nullbeleg", "Monatsbeleg", "Jahresbeleg", "Schlussbeleg"])
    p.add_argument("--drucken", action="store_true")
    p.set_defaults(f=cmd_nullbeleg)

    p = sub.add_parser("verkauf", help="Testverkauf: kasse verkauf NR[:MENGE] ...")
    p.add_argument("artikel", nargs="+")
    p.add_argument("--zahlungsart", default="Bar")
    p.add_argument("--training", action="store_true")
    p.add_argument("--drucken", action="store_true")
    p.set_defaults(f=cmd_verkauf)

    p = sub.add_parser("dep-export")
    p.add_argument("ziel")
    p.set_defaults(f=cmd_dep)

    p = sub.add_parser("sicherung", help="Datensicherung jetzt erstellen")
    p.add_argument("--ziel")
    p.set_defaults(f=cmd_sicherung)

    p = sub.add_parser("sicherung-planen", help="tägliche Sicherung in der Windows-Aufgabenplanung")
    p.add_argument("--uhrzeit", default="21:00")
    p.set_defaults(f=cmd_sicherung_planen)

    sub.add_parser("atrust-test", help="Verbindung zu A-Trust prüfen (Zertifikat + Testsignatur)").set_defaults(f=cmd_atrust_test)

    p = sub.add_parser("passwort", help="Passwort sicher speichern (atrust, sicherung, smtp, viva)")
    p.add_argument("name", choices=["atrust", "sicherung", "smtp", "viva"])
    p.set_defaults(f=cmd_passwort)

    p = sub.add_parser("export", help="Export für den Steuerberater (ZIP)")
    p.add_argument("von")
    p.add_argument("bis")
    p.add_argument("ziel")
    p.set_defaults(f=cmd_export)

    p = sub.add_parser("wiederherstellen", help="Sicherung (.rksich/.zip) wiederherstellen – Kasse vorher beenden")
    p.add_argument("datei")
    p.add_argument("--passwort")
    p.add_argument("--ja", action="store_true", help="ohne Rückfrage")
    p.set_defaults(f=cmd_wiederherstellen)

    sub.add_parser("selbsttest", help="alle Ausgabewege mit einer Testkasse prüfen (PDF, Bon, Export, Sicherung)") \
        .set_defaults(f=cmd_selbsttest)

    args = ap.parse_args(argv)
    from .geheim import GeheimFehler

    try:
        return args.f(args) or 0
    except (KassenFehler, SignaturFehler, GeheimFehler, FileNotFoundError, ValueError) as e:
        print(f"Fehler: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
