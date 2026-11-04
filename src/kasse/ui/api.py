"""Schnittstelle zwischen Oberfläche (HTML/JS) und Kassenkern.

Jede öffentliche Methode liefert ``{"ok": True, "daten": ...}`` bzw.
``{"ok": False, "fehler": "..."}``. Aufrufe werden per Lock serialisiert.
"""

from __future__ import annotations

import datetime as dt
import functools
import os
import sqlite3
import subprocess
import sys
import threading
from decimal import Decimal
from pathlib import Path

from .. import db, dokumente, sicherung
from ..config import datenverzeichnis
from ..geld import euro_zu_cent
from ..rksv import Kasse, KassenFehler, Position, SignaturFehler
from ..rksv.dep import dep_export_datei
from ..rksv.signatur import signer_aus_einstellungen

ZAHLUNGSARTEN = ("Bar", "Karte")

# Einstellungen, die die Oberfläche lesen/schreiben darf
EINSTELLUNGEN = (
    "firma_name", "firma_adresse", "firma_uid", "firma_fn", "firma_iban", "firma_bic",
    "bon_fusszeile", "bondrucker_art", "bondrucker_name", "a4_drucker_name", "nach_verkauf",
    "sicherung_ziel", "sicherung_intervall_stunden", "sicherung_behalten",
)


def _rueckgabe(f):
    @functools.wraps(f)
    def wrapper(self, *args, **kwargs):
        with self._lock:
            try:
                return {"ok": True, "daten": f(self, *args, **kwargs)}
            except (KassenFehler, SignaturFehler, ValueError, OSError, sqlite3.Error) as e:
                self.con.rollback()
                return {"ok": False, "fehler": str(e)}
    wrapper.oeffentlich = True  # type: ignore[attr-defined]
    return wrapper


def _row(r) -> dict:
    return dict(r) if r is not None else None


class KassenApi:
    def __init__(self, con: sqlite3.Connection, signer=None):
        self.con = con
        self._lock = threading.RLock()
        self._signer = signer

    @property
    def kasse(self) -> Kasse:
        if self._signer is None:
            self._signer = signer_aus_einstellungen(self.con)
        return Kasse(self.con, self._signer)

    # ------------------------------------------------------------------ Status

    @_rueckgabe
    def status(self):
        e = lambda k, d=None: db.einstellung(self.con, k, d)  # noqa: E731
        eingerichtet = bool(e("kassen_id"))
        k = self.kasse if eingerichtet else None
        return {
            "eingerichtet": eingerichtet,
            "gestartet": bool(k and k.ist_gestartet()),
            "geschlossen": bool(k and k.ist_geschlossen()),
            "kassen_id": e("kassen_id"),
            "firma": e("firma_name", ""),
            "signer": e("signer", "test"),
            "ausfall_seit": e("ausfall_seit"),
            "sicherung_zuletzt": e("sicherung_zuletzt"),
            "sicherung_faellig": sicherung.sicherung_faellig(self.con),
            "drucker": e("bondrucker_name"),
            "monatsbeleg_faellig": self._monatsbeleg_faellig(),
        }

    def _monatsbeleg_faellig(self) -> str | None:
        """Liefert den Vormonat (JJJJ-MM), falls dafür noch kein Monats-/Jahresbeleg erstellt wurde."""
        erster = self.con.execute("SELECT MIN(zeitpunkt) FROM belege").fetchone()[0]
        if not erster:
            return None
        heute = dt.date.today()
        vormonat = (heute.replace(day=1) - dt.timedelta(days=1)).strftime("%Y-%m")
        if erster[:7] > vormonat:
            return None
        da = self.con.execute(
            "SELECT 1 FROM belege WHERE art IN ('Monatsbeleg','Jahresbeleg') AND zeitpunkt >= ?",
            (vormonat + "-01",),
        ).fetchone()
        return None if da else vormonat

    # ------------------------------------------------------------------ Stammdaten

    @_rueckgabe
    def artikel(self, suche: str = ""):
        q = ("SELECT a.*, g.name AS gruppe FROM artikel a LEFT JOIN warengruppen g ON g.id = a.warengruppe_id"
             " WHERE a.sichtbar = 1")
        args: list = []
        if suche:
            q += " AND (a.name LIKE ? OR a.artikelnummer = ? OR a.barcode = ?)"
            args = [f"%{suche}%", suche, suche]
        return [dict(r) for r in self.con.execute(q + " ORDER BY g.name, a.name", args)]

    @_rueckgabe
    def artikel_alle(self):
        return [dict(r) for r in self.con.execute(
            "SELECT a.*, g.name AS gruppe FROM artikel a LEFT JOIN warengruppen g ON g.id = a.warengruppe_id"
            " ORDER BY a.sichtbar DESC, g.name, a.name")]

    @_rueckgabe
    def warengruppen(self):
        return [dict(r) for r in self.con.execute(
            "SELECT g.id, g.name FROM warengruppen g WHERE EXISTS"
            " (SELECT 1 FROM artikel a WHERE a.warengruppe_id = g.id AND a.sichtbar = 1) ORDER BY g.name")]

    @_rueckgabe
    def steuersaetze(self):
        return [dict(r) for r in self.con.execute("SELECT prozent, bezeichnung FROM steuersaetze ORDER BY CAST(prozent AS REAL) DESC")]

    @_rueckgabe
    def artikel_speichern(self, a: dict):
        name = (a.get("name") or "").strip()
        if not name:
            raise ValueError("Name fehlt")
        brutto = euro_zu_cent(str(a.get("preis", "0")))
        gruppe = (a.get("gruppe") or "").strip()
        gid = None
        if gruppe:
            self.con.execute("INSERT OR IGNORE INTO warengruppen (name) VALUES (?)", (gruppe,))
            gid = self.con.execute("SELECT id FROM warengruppen WHERE name = ?", (gruppe,)).fetchone()[0]
        werte = (a.get("artikelnummer") or None, a.get("barcode") or None, name, gid, brutto,
                 str(a.get("steuer_prozent") or "20"), 1 if a.get("sichtbar", True) else 0)
        if a.get("id"):
            self.con.execute(
                "UPDATE artikel SET artikelnummer=?, barcode=?, name=?, warengruppe_id=?, brutto_cent=?,"
                " steuer_prozent=?, sichtbar=? WHERE id=?", (*werte, a["id"]))
            aid = a["id"]
        else:
            aid = self.con.execute(
                "INSERT INTO artikel (artikelnummer, barcode, name, warengruppe_id, brutto_cent, steuer_prozent, sichtbar)"
                " VALUES (?,?,?,?,?,?,?)", werte).lastrowid
        self.con.commit()
        return aid

    @_rueckgabe
    def kunden(self, suche: str = ""):
        return [dict(r) for r in self.con.execute(
            "SELECT * FROM kunden WHERE name LIKE ? OR kundennummer = ? ORDER BY name", (f"%{suche}%", suche))]

    @_rueckgabe
    def kunde_speichern(self, k: dict):
        name = (k.get("name") or "").strip()
        if not name:
            raise ValueError("Name fehlt")
        werte = (k.get("kundennummer") or None, name, k.get("adresse") or "", k.get("uid") or None,
                 k.get("email") or None, int(k.get("zahlungsziel_tage") or 14))
        if k.get("id"):
            self.con.execute("UPDATE kunden SET kundennummer=?, name=?, adresse=?, uid=?, email=?, zahlungsziel_tage=?"
                             " WHERE id=?", (*werte, k["id"]))
            kid = k["id"]
        else:
            kid = self.con.execute("INSERT INTO kunden (kundennummer, name, adresse, uid, email, zahlungsziel_tage)"
                                   " VALUES (?,?,?,?,?,?)", werte).lastrowid
        self.con.commit()
        return kid

    # ------------------------------------------------------------------ Verkauf

    @staticmethod
    def _positionen(posten: list[dict]) -> list[Position]:
        pos = []
        for p in posten:
            menge = Decimal(str(p["menge"]))
            if menge == 0:
                continue
            pos.append(Position(p["name"], menge, int(p["preis_cent"]), str(p["steuer_prozent"]), p.get("artikel_id")))
        if not pos:
            raise KassenFehler("Warenkorb ist leer")
        return pos

    @_rueckgabe
    def verkaufen(self, posten: list[dict], zahlungsart: str, kunde_id: int | None = None, training: bool = False):
        if zahlungsart not in ZAHLUNGSARTEN:
            raise KassenFehler(f"Unbekannte Zahlungsart {zahlungsart}")
        beleg_id = self.kasse.verkauf(self._positionen(posten), zahlungsart, kunde_id, training)
        return self._nach_beleg(beleg_id)

    def _nach_beleg(self, beleg_id: int) -> dict:
        b = _row(self.con.execute("SELECT * FROM belege WHERE id = ?", (beleg_id,)).fetchone())
        b["druck"] = None
        # nach_verkauf: "dialog" (Auswahl Bon/A4/PDF), "bon" (sofort Bon drucken), "nichts"
        if db.einstellung(self.con, "nach_verkauf", "dialog") == "bon":
            try:
                self._ausgabe("beleg", beleg_id, "bon")
                b["druck"] = "gedruckt"
            except Exception as e:  # Druckfehler dürfen den Verkauf nicht verhindern
                b["druck"] = f"Druckfehler: {e}"
        return b

    def _pdf_pfad(self, name: str) -> Path:
        ordner = datenverzeichnis() / "dokumente"
        ordner.mkdir(exist_ok=True)
        return ordner / f"{name}.pdf"

    def _ausgabe(self, quelle: str, id_: int, ziel: str, drucker: str | None = None) -> str:
        from ..printing import a4
        from ..printing.bon import drucke_bon

        if quelle == "dokument":
            d = self.con.execute("SELECT typ, nummer, beleg_id FROM dokumente WHERE id = ?", (id_,)).fetchone()
            if not d:
                raise KassenFehler("Dokument nicht gefunden")
            if ziel == "bon":
                if not d["beleg_id"]:
                    raise KassenFehler("Für dieses Dokument gibt es keinen Kassenbon (nur A4/PDF)")
                return self._ausgabe("beleg", d["beleg_id"], "bon", drucker)
            pfad = a4.dokument_pdf(self.con, id_, self._pdf_pfad(d["nummer"]))
        elif quelle == "beleg":
            if ziel == "bon":
                drucke_bon(self.con, id_, drucker_name=drucker or None)
                return "Bon gedruckt"
            nr = self.con.execute("SELECT belegnummer FROM belege WHERE id = ?", (id_,)).fetchone()
            if not nr:
                raise KassenFehler("Beleg nicht gefunden")
            pfad = a4.beleg_pdf(self.con, id_, self._pdf_pfad(f"Beleg-{nr[0]:06d}"))
        else:
            raise ValueError(f"Unbekannte Quelle {quelle}")

        if ziel == "a4":
            a4.drucke_pdf(pfad, drucker or db.einstellung(self.con, "a4_drucker_name") or None)
            return f"A4 gedruckt ({pfad.name})"
        if ziel == "pdf":
            self._oeffnen(pfad)
            return str(pfad)
        raise ValueError(f"Unbekanntes Ausgabeziel {ziel}")

    @staticmethod
    def _oeffnen(pfad: Path) -> None:
        if sys.platform == "win32":
            os.startfile(str(pfad))  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(pfad)])
        elif os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"):
            subprocess.Popen(["xdg-open", str(pfad)])

    @_rueckgabe
    def ausgabe(self, quelle: str, id_: int, ziel: str, drucker: str | None = None):
        """Ausgabe eines Belegs/Dokuments: ziel = 'bon' | 'a4' | 'pdf', optional mit Druckerwahl."""
        try:
            return self._ausgabe(quelle, int(id_), ziel, drucker)
        except (KassenFehler, ValueError):
            raise
        except Exception as e:  # Treiber-/Druckerfehler verständlich melden
            raise OSError(f"Ausgabe fehlgeschlagen: {e}") from e

    @_rueckgabe
    def bon_vorschau(self, beleg_id: int):
        from ..printing.bon import bon_text

        return {"text": "".join(bon_text(self.con, beleg_id)), "qr": self.kasse.qr_inhalt(beleg_id)}

    @_rueckgabe
    def storno(self, beleg_id: int):
        return self._nach_beleg(self.kasse.storno(beleg_id))

    @_rueckgabe
    def belege(self, datum: str | None = None, limit: int = 200):
        q = "SELECT b.*, (SELECT COUNT(*) FROM belege s WHERE s.storno_von = b.id) AS storniert FROM belege b"
        args: list = []
        if datum:
            q += " WHERE substr(b.zeitpunkt, 1, 10) = ?"
            args.append(datum)
        q += " ORDER BY b.belegnummer DESC LIMIT ?"
        args.append(limit)
        res = []
        for r in self.con.execute(q, args):
            d = dict(r)
            d["summe"] = sum(d[k] for k in ("betrag_normal", "betrag_ermaessigt1", "betrag_ermaessigt2",
                                            "betrag_null", "betrag_besonders"))
            d.pop("jws")
            res.append(d)
        return res

    # ------------------------------------------------------------------ Sonderbelege / Abschluss

    @_rueckgabe
    def einrichten(self, kassen_id: str, signer: str = "test", atrust_benutzer: str = "", atrust_umgebung: str = "test"):
        schluessel = Kasse.einrichten(self.con, kassen_id)
        db.setze_einstellung(self.con, "signer", signer)
        if signer == "atrust":
            db.setze_einstellung(self.con, "atrust_benutzer", atrust_benutzer)
            db.setze_einstellung(self.con, "atrust_umgebung", atrust_umgebung)
        self.con.commit()
        self._signer = None
        from ..rksv.krypto import pruefwert

        return {"aes_schluessel": schluessel, "pruefwert": pruefwert(schluessel)}

    @_rueckgabe
    def startbeleg(self):
        return self._nach_beleg(self.kasse.startbeleg())

    @_rueckgabe
    def nullbeleg(self, art: str = "Nullbeleg"):
        b = self._nach_beleg(self.kasse.nullbeleg(art))
        if art in ("Monatsbeleg", "Jahresbeleg", "Schlussbeleg"):
            b["sicherung"] = str(sicherung.sichern(self.con))
        return b

    @_rueckgabe
    def tagesbericht(self, datum: str | None = None):
        datum = datum or dt.date.today().isoformat()
        zeilen = self.con.execute(
            "SELECT art, zahlungsart, COUNT(*) AS anzahl,"
            " SUM(betrag_normal + betrag_ermaessigt1 + betrag_ermaessigt2 + betrag_null + betrag_besonders) AS summe"
            " FROM belege WHERE substr(zeitpunkt, 1, 10) = ? AND art IN ('Barumsatz', 'Storno')"
            " GROUP BY art, zahlungsart", (datum,)).fetchall()
        steuern = self.con.execute(
            "SELECT p.steuer_prozent, SUM(p.summe_cent) AS brutto FROM belegpositionen p JOIN belege b ON b.id = p.beleg_id"
            " WHERE substr(b.zeitpunkt, 1, 10) = ? AND b.art IN ('Barumsatz', 'Storno')"
            " GROUP BY p.steuer_prozent ORDER BY CAST(p.steuer_prozent AS REAL) DESC", (datum,)).fetchall()
        from ..geld import netto_aus_brutto

        return {
            "datum": datum,
            "zahlungsarten": [dict(z) for z in zeilen],
            "gesamt": sum(z["summe"] or 0 for z in zeilen),
            "steuern": [{"satz": s["steuer_prozent"], "brutto": s["brutto"],
                         "netto": netto_aus_brutto(s["brutto"], s["steuer_prozent"])} for s in steuern],
        }

    @_rueckgabe
    def sicherung_jetzt(self):
        return str(sicherung.sichern(self.con))

    @_rueckgabe
    def dep_exportieren(self):
        ziel = sicherung.sicherungsziel(self.con) / f"dep-export-{dt.datetime.now():%Y%m%d-%H%M%S}.json"
        return str(dep_export_datei(self.con, ziel))

    # ------------------------------------------------------------------ Lieferschein / Rechnung

    @_rueckgabe
    def dokument_erstellen(self, typ: str, kunde_id: int, posten: list[dict], zahlungsart: str = "Überweisung"):
        if not kunde_id:
            raise KassenFehler("Bitte zuerst einen Kunden wählen")
        pos = [dokumente.DokPosition(p.bezeichnung, p.menge, p.einzelpreis_cent, p.steuer_prozent, "Stk", p.artikel_id)
               for p in self._positionen(posten)]
        if typ == "Lieferschein":
            dok_id = dokumente.lieferschein(self.con, kunde_id, pos)
            beleg = None
        else:
            dok_id = dokumente.rechnung(self.con, kunde_id, pos, zahlungsart,
                                        self.kasse if zahlungsart in dokumente.BARZAHLUNGEN else None)
            beleg = self.con.execute("SELECT beleg_id FROM dokumente WHERE id = ?", (dok_id,)).fetchone()[0]
        res = {"id": dok_id, "nummer": self.con.execute("SELECT nummer FROM dokumente WHERE id = ?", (dok_id,)).fetchone()[0]}
        if beleg:
            res["beleg"] = self._nach_beleg(beleg)
        return res

    @_rueckgabe
    def rechnung_aus_lieferscheinen(self, lieferschein_ids: list[int], zahlungsart: str = "Überweisung"):
        dok_id = dokumente.rechnung_aus_lieferscheinen(
            self.con, lieferschein_ids, zahlungsart, self.kasse if zahlungsart in dokumente.BARZAHLUNGEN else None)
        return {"id": dok_id, "nummer": self.con.execute("SELECT nummer FROM dokumente WHERE id = ?", (dok_id,)).fetchone()[0]}

    @_rueckgabe
    def dokumente(self, typ: str | None = None):
        q = ("SELECT d.*, k.name AS kunde,"
             " (SELECT COUNT(*) FROM dokument_bezug b WHERE b.lieferschein_id = d.id) AS verrechnet,"
             " (SELECT SUM(CAST(ROUND(CAST(p.menge AS REAL) * p.einzelpreis_cent) AS INTEGER))"
             "  FROM dokumentpositionen p WHERE p.dokument_id = d.id) AS summe"
             " FROM dokumente d JOIN kunden k ON k.id = d.kunde_id")
        args: list = []
        if typ:
            q += " WHERE d.typ = ?"
            args.append(typ)
        return [dict(r) for r in self.con.execute(q + " ORDER BY d.id DESC LIMIT 300", args)]

    # ------------------------------------------------------------------ Einstellungen

    @_rueckgabe
    def einstellungen(self):
        return {k: db.einstellung(self.con, k, "") for k in EINSTELLUNGEN}

    @_rueckgabe
    def einstellungen_speichern(self, werte: dict):
        for k, v in werte.items():
            if k in EINSTELLUNGEN:
                db.setze_einstellung(self.con, k, str(v))
        self.con.commit()
        return True

    @_rueckgabe
    def drucker_liste(self):
        """Installierte Windows-Drucker (für Bondrucker mit Windows-Standardtreiber)."""
        if sys.platform != "win32":
            return {"drucker": [], "standard": None}
        import win32print  # type: ignore[import-not-found]

        flags = win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
        return {"drucker": sorted(p[2] for p in win32print.EnumPrinters(flags)),
                "standard": win32print.GetDefaultPrinter()}

    @_rueckgabe
    def testdruck(self):
        from ..printing.bon import drucker_aus_einstellungen

        try:
            p = drucker_aus_einstellungen(self.con)
        except Exception as e:
            raise OSError(f"Bondrucker nicht verfügbar: {e}") from e
        p.set(align="center")
        p.text(f"{db.einstellung(self.con, 'firma_name', '')}\nTestdruck Bondrucker\n{dt.datetime.now():%d.%m.%Y %H:%M}\n")
        p.qr("Testdruck Registrierkasse", size=4, native=False)
        p.cut()
        return True


def oeffentliche_methoden(api: KassenApi) -> dict:
    return {n: getattr(api, n) for n in dir(api)
            if not n.startswith("_") and getattr(getattr(api, n), "oeffentlich", False)}


def standard_api(datenbank: Path | str | None = None) -> KassenApi:
    from ..config import datenbankpfad

    return KassenApi(db.verbinden(datenbank or datenbankpfad()))
