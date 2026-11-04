"""Schnittstelle zwischen Oberfläche (HTML/JS) und Kassenkern.

Jede öffentliche Methode liefert ``{"ok": True, "daten": ...}`` bzw.
``{"ok": False, "fehler": "..."}``. Aufrufe werden per Lock serialisiert.

Rechte: Sind Benutzer angelegt, ist eine Anmeldung per PIN nötig. Methoden mit
``recht="chef"`` sind dem Chef vorbehalten.
"""

from __future__ import annotations

import base64
import datetime as dt
import functools
import os
import re
import sqlite3
import subprocess
import sys
import threading
from decimal import Decimal
from pathlib import Path

from .. import (__version__, benutzer, db, dokumente, ebinterface, export, geheim, gutscheine, kassenbuch,
                lizenz, mail, sicherung, terminal, update)
from ..config import datenverzeichnis
from ..geld import anzeige, euro_zu_cent, netto_aus_brutto
from ..rksv import Kasse, KassenFehler, Position, SignaturFehler
from ..rksv.dep import dep_export_datei
from ..rksv.signatur import signer_aus_einstellungen, signer_testen

ZAHLUNGSARTEN = ("Bar", "Karte")
GEHEIMNISSE = ("atrust", "sicherung", "smtp", "viva")

# Einstellungen, die die Oberfläche lesen/schreiben darf
EINSTELLUNGEN = (
    "firma_name", "firma_adresse", "firma_uid", "firma_fn", "firma_iban", "firma_bic",
    "bon_fusszeile", "bon_logo", "bondrucker_art", "bondrucker_name", "a4_drucker_name", "nach_verkauf",
    "kassenlade", "kassenlade_pin", "auto_abmelden_min",
    "sicherung_ziel", "sicherung_intervall_stunden", "sicherung_behalten",
    "atrust_benutzer", "atrust_umgebung",
    "karten_terminal", "viva_client_id", "viva_terminal_id", "viva_umgebung",
    "smtp_host", "smtp_port", "smtp_sicherheit", "smtp_benutzer", "smtp_absender", "mail_text",
    *export.STANDARD_KONTEN.keys(),
    "update_url", "akzentfarbe",
)

FEHLERTYPEN = (KassenFehler, SignaturFehler, ValueError, OSError, sqlite3.Error, terminal.TerminalFehler,
               geheim.GeheimFehler, update.UpdateFehler, RuntimeError)


def _api(recht: str | None = None, frei: bool = False):
    """Dekorator: Lock, Rechteprüfung und einheitliche Rückgabe."""

    def deko(f):
        @functools.wraps(f)
        def wrapper(self, *args, **kwargs):
            with self._lock:
                try:
                    if not frei:
                        self._pruefe_recht(recht)
                    return {"ok": True, "daten": f(self, *args, **kwargs)}
                except FEHLERTYPEN as e:
                    self.con.rollback()
                    return {"ok": False, "fehler": str(e)}

        wrapper.oeffentlich = True  # type: ignore[attr-defined]
        return wrapper

    return deko


def _row(r) -> dict | None:
    return dict(r) if r is not None else None


def _datum(t: str | None, standard: dt.date | None = None) -> str:
    if not t:
        return (standard or dt.date.today()).isoformat()
    return dt.date.fromisoformat(t).isoformat()


class KassenApi:
    def __init__(self, con: sqlite3.Connection, signer=None, db_pfad: Path | str | None = None):
        self.con = con
        self.db_pfad = Path(db_pfad) if db_pfad else None
        self._lock = threading.RLock()
        self._signer = signer
        self.benutzer: dict | None = None
        self._terminal_ok: dict[str, tuple[int, str]] = {}
        self._update_info: dict | None = None
        self._update_fehler: str | None = None
        self._beenden = None  # wird von app.py gesetzt (Fenster schließen)

    # ------------------------------------------------------------------ Hilfen

    @property
    def kasse(self) -> Kasse:
        if self._signer is None:
            self._signer = signer_aus_einstellungen(self.con)
        return Kasse(self.con, self._signer)

    @property
    def _bid(self) -> int | None:
        return self.benutzer["id"] if self.benutzer else None

    def _pruefe_recht(self, recht: str | None) -> None:
        if not benutzer.gibt_benutzer(self.con):
            return
        if self.benutzer is None:
            raise KassenFehler("Bitte anmelden")
        if recht == "chef" and self.benutzer["rolle"] != "chef":
            raise KassenFehler("Diese Funktion ist dem Chef vorbehalten")

    def _ereignis(self, art: str, text: str = "") -> None:
        db.ereignis(self.con, art, text, self._bid)
        self.con.commit()

    def _e(self, k: str, d: str | None = None) -> str | None:
        return db.einstellung(self.con, k, d)

    def _ordner(self, name: str) -> Path:
        o = datenverzeichnis() / name
        o.mkdir(exist_ok=True)
        return o

    @staticmethod
    def _oeffnen(pfad: Path) -> None:
        if os.environ.get("KASSE_NICHT_OEFFNEN"):  # Tests/Server-Betrieb
            return
        if sys.platform == "win32":
            os.startfile(str(pfad))  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(pfad)])
        elif os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"):
            subprocess.Popen(["xdg-open", str(pfad)])

    # ------------------------------------------------------------------ Status / Anmeldung

    @_api(frei=True)
    def status(self):
        e = self._e
        eingerichtet = bool(e("kassen_id"))
        k = None
        signer_fehler = None
        if eingerichtet:
            try:
                k = self.kasse
            except SignaturFehler as ex:
                signer_fehler = str(ex)
        ausfall = e("ausfall_seit")
        lager = self.con.execute(
            "SELECT COUNT(*) FROM artikel WHERE sichtbar = 1 AND lagerstand IS NOT NULL AND mindestbestand IS NOT NULL"
            " AND CAST(lagerstand AS REAL) <= CAST(mindestbestand AS REAL)").fetchone()[0]
        offen = self.con.execute(
            "SELECT COUNT(*) FROM dokumente d JOIN kunden k ON k.id = d.kunde_id WHERE d.typ = 'Rechnung'"
            " AND d.bezahlt_am IS NULL AND date(d.datum, '+' || k.zahlungsziel_tage || ' days') < date('now','localtime')"
        ).fetchone()[0]
        return {
            "version": __version__,
            "eingerichtet": eingerichtet,
            "gestartet": bool(k and k.ist_gestartet()) or (bool(eingerichtet) and self._hat_belege()),
            "geschlossen": bool(k and k.ist_geschlossen()),
            "kassen_id": e("kassen_id"),
            "firma": e("firma_name", ""),
            "akzentfarbe": e("akzentfarbe", ""),
            "signer": e("signer", "test"),
            "signer_fehler": signer_fehler,
            "ausfall_seit": ausfall,
            "ausfall_ueber_48h": bool(ausfall and dt.datetime.now() - dt.datetime.fromisoformat(ausfall)
                                      > dt.timedelta(hours=48)),
            "sicherung_zuletzt": e("sicherung_zuletzt"),
            "sicherung_faellig": sicherung.sicherung_faellig(self.con),
            "sicherung_verschluesselt": geheim.vorhanden("sicherung"),
            "drucker": e("bondrucker_name"),
            "monatsbeleg_faellig": self._monatsbeleg_faellig(),
            "benutzer_pflicht": benutzer.gibt_benutzer(self.con),
            "benutzer": self.benutzer,
            "auto_abmelden_min": int(e("auto_abmelden_min", "0") or 0),
            "lager_warnungen": lager,
            "rechnungen_ueberfaellig": offen,
            "kassastand": kassenbuch.kassastand(self.con),
            "lizenz": lizenz.pruefen(e("lizenz")),
            "update": self._update_info,
            "karten_terminal": e("karten_terminal", "manuell"),
        }

    def _hat_belege(self) -> bool:
        return self.con.execute("SELECT 1 FROM belege LIMIT 1").fetchone() is not None

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

    @_api(frei=True)
    def anmelden(self, pin: str):
        b = benutzer.anmelden(self.con, str(pin))
        if not b:
            db.ereignis(self.con, "Anmeldung fehlgeschlagen")
            self.con.commit()
            raise KassenFehler("PIN falsch")
        self.benutzer = b
        self._ereignis("Anmeldung", b["name"])
        return b

    @_api(frei=True)
    def abmelden(self):
        if self.benutzer:
            self._ereignis("Abmeldung", self.benutzer["name"])
        self.benutzer = None
        return True

    @_api(recht="chef")
    def benutzer_liste(self):
        return benutzer.liste(self.con)

    @_api(recht="chef")
    def benutzer_speichern(self, b: dict):
        erster = not benutzer.gibt_benutzer(self.con)
        bid = benutzer.speichern(self.con, b.get("name", ""), b.get("rolle", "kassier"), b.get("pin") or None,
                                 b.get("id"), bool(b.get("aktiv", True)))
        self._ereignis("Benutzer gespeichert", b.get("name", ""))
        if erster:  # wer den ersten Benutzer anlegt, ist danach als dieser angemeldet
            self.benutzer = {"id": bid, "name": b["name"], "rolle": "chef"}
        return bid

    @_api(recht="chef")
    def ereignisse(self, limit: int = 300):
        return [dict(r) for r in self.con.execute(
            "SELECT e.*, u.name AS benutzer FROM ereignisse e LEFT JOIN benutzer u ON u.id = e.benutzer_id"
            " ORDER BY e.id DESC LIMIT ?", (limit,))]

    # ------------------------------------------------------------------ Stammdaten

    @_api()
    def artikel(self, suche: str = ""):
        q = ("SELECT a.*, g.name AS gruppe FROM artikel a LEFT JOIN warengruppen g ON g.id = a.warengruppe_id"
             " WHERE a.sichtbar = 1")
        args: list = []
        if suche:
            q += " AND (a.name LIKE ? OR a.artikelnummer = ? OR a.barcode = ?)"
            args = [f"%{suche}%", suche, suche]
        return [dict(r) for r in self.con.execute(q + " ORDER BY g.name, a.name", args)]

    @_api()
    def artikel_alle(self):
        return [dict(r) for r in self.con.execute(
            "SELECT a.*, g.name AS gruppe FROM artikel a LEFT JOIN warengruppen g ON g.id = a.warengruppe_id"
            " ORDER BY a.sichtbar DESC, g.name, a.name")]

    @_api()
    def warengruppen(self):
        return [dict(r) for r in self.con.execute(
            "SELECT g.id, g.name FROM warengruppen g WHERE EXISTS"
            " (SELECT 1 FROM artikel a WHERE a.warengruppe_id = g.id AND a.sichtbar = 1) ORDER BY g.name")]

    @_api()
    def steuersaetze(self):
        return [dict(r) for r in self.con.execute(
            "SELECT prozent, bezeichnung FROM steuersaetze ORDER BY CAST(prozent AS REAL) DESC")]

    @staticmethod
    def _menge_text(v) -> str | None:
        if v in (None, ""):
            return None
        return format(Decimal(str(v).replace(",", ".")).normalize(), "f")

    @_api(recht="chef")
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
                 str(a.get("steuer_prozent") or "20"), 1 if a.get("sichtbar", True) else 0,
                 self._menge_text(a.get("mindestbestand")))
        if a.get("id"):
            self.con.execute(
                "UPDATE artikel SET artikelnummer=?, barcode=?, name=?, warengruppe_id=?, brutto_cent=?,"
                " steuer_prozent=?, sichtbar=?, mindestbestand=? WHERE id=?", (*werte, a["id"]))
            aid = a["id"]
        else:
            aid = self.con.execute(
                "INSERT INTO artikel (artikelnummer, barcode, name, warengruppe_id, brutto_cent, steuer_prozent,"
                " sichtbar, mindestbestand) VALUES (?,?,?,?,?,?,?,?)", werte).lastrowid
        lager = self._menge_text(a.get("lagerstand"))
        alt = self.con.execute("SELECT lagerstand FROM artikel WHERE id = ?", (aid,)).fetchone()[0]
        if lager != alt:
            self.con.execute("UPDATE artikel SET lagerstand = ? WHERE id = ?", (lager, aid))
            if lager is not None:
                self.con.execute("INSERT INTO lagerbewegungen (artikel_id, zeitpunkt, menge, grund) VALUES (?,?,?,?)",
                                 (aid, dt.datetime.now().isoformat(timespec="seconds"),
                                  str(Decimal(lager) - Decimal(alt or 0)), "Inventur/Korrektur"))
        self.con.commit()
        return aid

    @_api(recht="chef")
    def lager_zugang(self, artikel_id: int, menge, grund: str = "Wareneingang"):
        m = Decimal(str(menge).replace(",", "."))
        alt = self.con.execute("SELECT lagerstand FROM artikel WHERE id = ?", (artikel_id,)).fetchone()
        if alt is None:
            raise KassenFehler("Artikel nicht gefunden")
        neu = Decimal(alt[0] or 0) + m
        self.con.execute("UPDATE artikel SET lagerstand = ? WHERE id = ?", (format(neu.normalize(), "f"), artikel_id))
        self.con.execute("INSERT INTO lagerbewegungen (artikel_id, zeitpunkt, menge, grund) VALUES (?,?,?,?)",
                         (artikel_id, dt.datetime.now().isoformat(timespec="seconds"), str(m), grund))
        self.con.commit()
        return format(neu.normalize(), "f")

    def _lager_buchen(self, positionen: list[Position], faktor: int, grund: str) -> None:
        jetzt = dt.datetime.now().isoformat(timespec="seconds")
        for p in positionen:
            if not p.artikel_id:
                continue
            row = self.con.execute("SELECT lagerstand FROM artikel WHERE id = ?", (p.artikel_id,)).fetchone()
            if not row or row[0] is None:
                continue  # Artikel ohne Lagerführung
            delta = -faktor * p.menge
            neu = Decimal(row[0]) + delta
            self.con.execute("UPDATE artikel SET lagerstand = ? WHERE id = ?", (format(neu.normalize(), "f"), p.artikel_id))
            self.con.execute("INSERT INTO lagerbewegungen (artikel_id, zeitpunkt, menge, grund) VALUES (?,?,?,?)",
                             (p.artikel_id, jetzt, str(delta), grund))
        self.con.commit()

    @_api()
    def kunden(self, suche: str = ""):
        return [dict(r) for r in self.con.execute(
            "SELECT * FROM kunden WHERE name LIKE ? OR kundennummer = ? ORDER BY name", (f"%{suche}%", suche))]

    @_api()
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

    def _positionen(self, posten: list[dict], gutschein_codes: dict | None = None) -> list[Position]:
        """Wandelt Warenkorb-Einträge in Positionen. ``gutschein_codes`` sammelt Gutschein-Vorgänge."""
        pos = []
        for p in posten:
            typ = p.get("typ", "artikel")
            if typ == "gutschein_verkauf":
                wert = int(p["preis_cent"])
                if wert <= 0:
                    raise KassenFehler("Gutscheinwert muss positiv sein")
                code = gutscheine.neuer_code(self.con)
                if gutschein_codes is not None:
                    gutschein_codes.setdefault("verkauf", []).append((code, wert))
                pos.append(Position(f"Wertgutschein {code}", Decimal(1), wert, "0"))
                continue
            if typ == "gutschein_einloesung":
                betrag = abs(int(p["preis_cent"]))  # Oberfläche liefert den Abzug negativ
                g = gutscheine.pruefen(self.con, p["code"])
                if betrag == 0 or betrag > g["rest_cent"]:
                    raise KassenFehler(f"Gutschein {g['code']}: maximal {anzeige(g['rest_cent'])} € einlösbar")
                if gutschein_codes is not None:
                    gutschein_codes.setdefault("einloesung", []).append((g["code"], betrag))
                pos.append(Position(f"Gutschein {g['code']} eingelöst", Decimal(1), -betrag, "0"))
                continue
            menge = Decimal(str(p["menge"]))
            if menge == 0:
                continue
            rabatt = int(p.get("rabatt_cent") or 0)
            if menge < 0:
                rabatt = -abs(rabatt)
            pos.append(Position(p["name"], menge, int(p["preis_cent"]), str(p["steuer_prozent"]),
                                p.get("artikel_id"), rabatt))
        if not pos:
            raise KassenFehler("Warenkorb ist leer")
        return pos

    def _zahlungen(self, zahlungen, summe: int) -> list[tuple[str, int, str | None]]:
        if isinstance(zahlungen, str):
            zahlungen = [{"art": zahlungen, "betrag_cent": summe}]
        res = []
        tm = None
        for z in zahlungen:
            art = z["art"]
            if art not in ZAHLUNGSARTEN:
                raise KassenFehler(f"Unbekannte Zahlungsart {art}")
            betrag = int(z["betrag_cent"])
            ref = None
            if art == "Karte":
                if tm is None:
                    tm = terminal.terminal_aus_einstellungen(self.con)
                if tm.automatisch:
                    ok = self._terminal_ok.get(z.get("sitzung") or "")
                    if not ok or ok[0] != betrag:
                        raise KassenFehler("Kartenzahlung wurde vom Terminal nicht bestätigt")
                    ref = ok[1]
            res.append((art, betrag, ref))
        if summe and not res:
            raise KassenFehler("Zahlungsart fehlt")
        return res

    @_api()
    def verkaufen(self, posten: list[dict], zahlungen, kunde_id: int | None = None, training: bool = False):
        vorgaenge: dict = {}
        positionen = self._positionen(posten, vorgaenge)
        summe = sum(p.summe_cent for p in positionen)
        if summe < 0:
            raise KassenFehler("Belegsumme darf nicht negativ sein (Gutschein höher als Einkauf)")
        zl = self._zahlungen(zahlungen, summe)
        if training and vorgaenge:
            raise KassenFehler("Gutscheine sind im Trainingsmodus nicht möglich")
        beleg_id = self.kasse.verkauf(positionen, zl[0][0] if zl else "Gutschein", kunde_id, training,
                                      zahlungen=zl, benutzer_id=self._bid)
        if not training:
            for code, wert in vorgaenge.get("verkauf", []):
                gutscheine.anlegen(self.con, code, wert, beleg_id)
            for code, betrag in vorgaenge.get("einloesung", []):
                gutscheine.einloesen(self.con, code, betrag, beleg_id)
            self.con.commit()
            self._lager_buchen(positionen, 1, "Verkauf")
            for z in zahlungen if isinstance(zahlungen, list) else []:
                self._terminal_ok.pop(z.get("sitzung") or "", None)
        b = self._nach_beleg(beleg_id)
        b["gutscheine"] = [c for c, _ in vorgaenge.get("verkauf", [])]
        if any(z[0] == "Bar" for z in zl) and not training:
            b["lade"] = self._lade(automatisch=True)
        return b

    def _nach_beleg(self, beleg_id: int) -> dict:
        b = _row(self.con.execute("SELECT * FROM belege WHERE id = ?", (beleg_id,)).fetchone())
        b["druck"] = None
        # nach_verkauf: "dialog" (Auswahl Bon/A4/PDF), "bon" (sofort Bon drucken), "nichts"
        if self._e("nach_verkauf", "dialog") == "bon":
            try:
                self._ausgabe("beleg", beleg_id, "bon")
                b["druck"] = "gedruckt"
            except Exception as e:  # Druckfehler dürfen den Verkauf nicht verhindern
                b["druck"] = f"Druckfehler: {e}"
        return b

    def _lade(self, automatisch: bool) -> str | None:
        if self._e("kassenlade", "aus") != "bondrucker":
            return None if automatisch else "Keine Kassenlade eingerichtet"
        from ..printing.bon import kassenlade_oeffnen

        try:
            kassenlade_oeffnen(self.con)
            if not automatisch:
                self._ereignis("Kassenlade geöffnet", "ohne Verkauf")
            return "geöffnet"
        except Exception as e:
            return f"Kassenlade: {e}"

    @_api()
    def kassenlade_oeffnen(self):
        r = self._lade(automatisch=False)
        if r != "geöffnet":
            raise OSError(r or "Kassenlade nicht verfügbar")
        return r

    # ------------------------------------------------------------------ Kartenterminal

    @_api()
    def karte_starten(self, betrag_cent: int):
        tm = terminal.terminal_aus_einstellungen(self.con)
        if not tm.automatisch:
            return {"automatisch": False, "sitzung": None}
        sitzung = tm.starten(int(betrag_cent), f"Kasse {self._e('kassen_id', '')}")
        self._terminal_betrag = getattr(self, "_terminal_betrag", {})
        self._terminal_betrag[sitzung] = int(betrag_cent)
        return {"automatisch": True, "sitzung": sitzung}

    @_api()
    def karte_status(self, sitzung: str):
        tm = terminal.terminal_aus_einstellungen(self.con)
        st = tm.status(sitzung)
        if st.zustand == "erfolg":
            betrag = getattr(self, "_terminal_betrag", {}).get(sitzung)
            if betrag is not None:
                self._terminal_ok[sitzung] = (betrag, st.referenz or sitzung)
        return {"zustand": st.zustand, "referenz": st.referenz, "meldung": st.meldung}

    @_api()
    def karte_abbrechen(self, sitzung: str):
        terminal.terminal_aus_einstellungen(self.con).abbrechen(sitzung)
        return True

    # ------------------------------------------------------------------ Gutscheine

    @_api()
    def gutschein_pruefen(self, code: str):
        g = gutscheine.pruefen(self.con, code)
        return {"code": g["code"], "rest_cent": g["rest_cent"], "wert_cent": g["wert_cent"], "gueltig_bis": g["gueltig_bis"]}

    @_api()
    def gutscheine(self):
        return gutscheine.liste(self.con)

    # ------------------------------------------------------------------ Ausgabe

    def _pdf_pfad(self, name: str) -> Path:
        return self._ordner("dokumente") / f"{name}.pdf"

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
            a4.drucke_pdf(pfad, drucker or self._e("a4_drucker_name") or None)
            return f"A4 gedruckt ({pfad.name})"
        if ziel == "pdf":
            self._oeffnen(pfad)
            return str(pfad)
        raise ValueError(f"Unbekanntes Ausgabeziel {ziel}")

    @_api()
    def ausgabe(self, quelle: str, id_: int, ziel: str, drucker: str | None = None):
        """Ausgabe eines Belegs/Dokuments: ziel = 'bon' | 'a4' | 'pdf', optional mit Druckerwahl."""
        try:
            return self._ausgabe(quelle, int(id_), ziel, drucker)
        except (KassenFehler, ValueError):
            raise
        except Exception as e:  # Treiber-/Druckerfehler verständlich melden
            raise OSError(f"Ausgabe fehlgeschlagen: {e}") from e

    @_api()
    def bon_vorschau(self, beleg_id: int):
        from ..printing.bon import bon_text

        return {"text": "".join(bon_text(self.con, beleg_id)), "qr": self.kasse.qr_inhalt(beleg_id)}

    @_api(recht="chef")
    def storno(self, beleg_id: int):
        verkauft = self.con.execute("SELECT code FROM gutscheine WHERE verkauf_beleg_id = ? AND rest_cent < wert_cent",
                                    (beleg_id,)).fetchone()
        if verkauft:
            raise KassenFehler(f"Gutschein {verkauft[0]} wurde bereits (teilweise) eingelöst – Storno nicht möglich")
        sid = self.kasse.storno(beleg_id, self._bid)
        # Gutscheine: verkaufte sperren, eingelöste Beträge zurückbuchen
        self.con.execute("UPDATE gutscheine SET rest_cent = 0 WHERE verkauf_beleg_id = ?", (beleg_id,))
        for gb in self.con.execute("SELECT * FROM gutschein_buchungen WHERE beleg_id = ?", (beleg_id,)).fetchall():
            self.con.execute("UPDATE gutscheine SET rest_cent = rest_cent + ? WHERE id = ?",
                             (gb["betrag_cent"], gb["gutschein_id"]))
            self.con.execute("INSERT INTO gutschein_buchungen VALUES (?,?,?)", (gb["gutschein_id"], sid, -gb["betrag_cent"]))
        self.con.commit()
        orig = [Position(r["bezeichnung"], Decimal(r["menge"]), r["einzelpreis_cent"], r["steuer_prozent"], r["artikel_id"])
                for r in self.con.execute("SELECT * FROM belegpositionen WHERE beleg_id = ?", (beleg_id,))]
        self._lager_buchen(orig, -1, "Storno")
        self._ereignis("Storno", f"Beleg-ID {beleg_id}")
        return self._nach_beleg(sid)

    @_api()
    def belege(self, datum: str | None = None, limit: int = 200):
        q = ("SELECT b.*, u.name AS kassier, (SELECT COUNT(*) FROM belege s WHERE s.storno_von = b.id) AS storniert"
             " FROM belege b LEFT JOIN benutzer u ON u.id = b.benutzer_id")
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

    # ------------------------------------------------------------------ Einrichtung / Sonderbelege

    @_api(recht="chef")
    def einrichten(self, kassen_id: str, signer: str = "test", atrust_benutzer: str = "", atrust_umgebung: str = "test",
                   atrust_passwort: str = ""):
        schluessel = Kasse.einrichten(self.con, kassen_id)
        db.setze_einstellung(self.con, "signer", signer)
        if signer == "atrust":
            db.setze_einstellung(self.con, "atrust_benutzer", atrust_benutzer)
            db.setze_einstellung(self.con, "atrust_umgebung", atrust_umgebung)
            if atrust_passwort:
                geheim.schreiben("atrust", atrust_passwort)
        self.con.commit()
        self._signer = None
        from ..rksv.krypto import pruefwert

        self._ereignis("Kasse eingerichtet", kassen_id)
        return {"aes_schluessel": schluessel, "pruefwert": pruefwert(schluessel)}

    @_api(recht="chef")
    def startbeleg(self):
        return self._nach_beleg(self.kasse.startbeleg())

    @_api(recht="chef")
    def nullbeleg(self, art: str = "Nullbeleg"):
        b = self._nach_beleg(self.kasse.nullbeleg(art))
        if art in ("Monatsbeleg", "Jahresbeleg", "Schlussbeleg"):
            b["sicherung"] = str(sicherung.sichern(self.con))
        self._ereignis(art)
        return b

    @_api(recht="chef")
    def atrust_testen(self):
        self._signer = None
        return signer_testen(self.kasse.signer)

    # ------------------------------------------------------------------ Berichte

    @_api()
    def tagesbericht(self, datum: str | None = None):
        datum = _datum(datum)
        zahl = self.con.execute(
            "SELECT z.art, COUNT(DISTINCT b.id) AS anzahl, SUM(z.betrag_cent) AS summe FROM zahlungen z"
            " JOIN belege b ON b.id = z.beleg_id WHERE substr(b.zeitpunkt, 1, 10) = ? GROUP BY z.art", (datum,)).fetchall()
        belege_ = self.con.execute(
            "SELECT art, COUNT(*) AS anzahl,"
            " SUM(betrag_normal + betrag_ermaessigt1 + betrag_ermaessigt2 + betrag_null + betrag_besonders) AS summe"
            " FROM belege WHERE substr(zeitpunkt, 1, 10) = ? AND art IN ('Barumsatz', 'Storno') GROUP BY art",
            (datum,)).fetchall()
        steuern = self.con.execute(
            "SELECT p.steuer_prozent, SUM(p.summe_cent) AS brutto FROM belegpositionen p JOIN belege b ON b.id = p.beleg_id"
            " WHERE substr(b.zeitpunkt, 1, 10) = ? AND b.art IN ('Barumsatz', 'Storno')"
            " GROUP BY p.steuer_prozent ORDER BY CAST(p.steuer_prozent AS REAL) DESC", (datum,)).fetchall()
        rabatt = self.con.execute(
            "SELECT COALESCE(SUM(p.rabatt_cent), 0) FROM belegpositionen p JOIN belege b ON b.id = p.beleg_id"
            " WHERE substr(b.zeitpunkt, 1, 10) = ? AND b.art IN ('Barumsatz', 'Storno')", (datum,)).fetchone()[0]
        bel = {r["art"]: dict(r) for r in belege_}
        return {
            "datum": datum,
            "zahlungen": {r["art"]: r["summe"] or 0 for r in zahl},
            "anzahl": (bel.get("Barumsatz") or {}).get("anzahl", 0),
            "storno": (bel.get("Storno") or {}).get("summe", 0) or 0,
            "gesamt": sum((r["summe"] or 0) for r in belege_),
            "rabatt": rabatt,
            "steuern": [{"satz": s["steuer_prozent"], "brutto": s["brutto"],
                         "netto": netto_aus_brutto(s["brutto"], s["steuer_prozent"])} for s in steuern],
        }

    @_api()
    def statistik(self, von: str | None = None, bis: str | None = None):
        bis = _datum(bis)
        von = _datum(von, dt.date.fromisoformat(bis) - dt.timedelta(days=29))
        filt = "substr(b.zeitpunkt, 1, 10) BETWEEN ? AND ? AND b.art IN ('Barumsatz', 'Storno')"
        ohne_gs = "p.bezeichnung NOT LIKE 'Wertgutschein %' AND p.bezeichnung NOT LIKE 'Gutschein % eingelöst'"
        summe_b = "(b.betrag_normal + b.betrag_ermaessigt1 + b.betrag_ermaessigt2 + b.betrag_null + b.betrag_besonders)"
        tage = self.con.execute(f"SELECT substr(b.zeitpunkt, 1, 10) AS tag, SUM({summe_b}) AS umsatz,"
                                f" SUM(CASE WHEN b.art = 'Barumsatz' THEN 1 ELSE 0 END) AS belege FROM belege b"
                                f" WHERE {filt} GROUP BY tag ORDER BY tag", (von, bis)).fetchall()
        artikel = self.con.execute(
            f"SELECT p.bezeichnung AS name, SUM(CAST(p.menge AS REAL)) AS menge, SUM(p.summe_cent) AS umsatz"
            f" FROM belegpositionen p JOIN belege b ON b.id = p.beleg_id WHERE {filt} AND {ohne_gs}"
            f" GROUP BY p.bezeichnung ORDER BY umsatz DESC LIMIT 15", (von, bis)).fetchall()
        gruppen = self.con.execute(
            f"SELECT COALESCE(g.name, 'Ohne Gruppe') AS name, SUM(p.summe_cent) AS umsatz FROM belegpositionen p"
            f" JOIN belege b ON b.id = p.beleg_id LEFT JOIN artikel a ON a.id = p.artikel_id"
            f" LEFT JOIN warengruppen g ON g.id = a.warengruppe_id WHERE {filt} AND {ohne_gs} GROUP BY 1 ORDER BY umsatz DESC",
            (von, bis)).fetchall()
        stunden = self.con.execute(
            f"SELECT CAST(substr(b.zeitpunkt, 12, 2) AS INTEGER) AS stunde, SUM({summe_b}) AS umsatz,"
            f" COUNT(*) AS belege FROM belege b WHERE {filt} GROUP BY stunde ORDER BY stunde", (von, bis)).fetchall()
        zahl = self.con.execute(
            f"SELECT z.art, SUM(z.betrag_cent) AS umsatz FROM zahlungen z JOIN belege b ON b.id = z.beleg_id"
            f" WHERE {filt} GROUP BY z.art", (von, bis)).fetchall()
        rech = self.con.execute(
            "SELECT COALESCE(SUM(CAST(ROUND(CAST(p.menge AS REAL) * p.einzelpreis_cent) AS INTEGER)), 0)"
            " FROM dokumente d JOIN dokumentpositionen p ON p.dokument_id = d.id"
            " WHERE d.typ = 'Rechnung' AND d.beleg_id IS NULL AND d.datum BETWEEN ? AND ?", (von, bis)).fetchone()[0]
        return {"von": von, "bis": bis, "tage": [dict(r) for r in tage], "artikel": [dict(r) for r in artikel],
                "gruppen": [dict(r) for r in gruppen], "stunden": [dict(r) for r in stunden],
                "zahlungen": [dict(r) for r in zahl], "rechnungen_ueberweisung": rech}

    # ------------------------------------------------------------------ Kassenbuch

    @_api()
    def kassenbuch(self, datum: str | None = None):
        return {"kassastand": kassenbuch.kassastand(self.con), "eintraege": kassenbuch.eintraege(self.con, _datum(datum)),
                "stueckelung": kassenbuch.STUECKELUNG}

    @_api()
    def kassenbuch_buchen(self, art: str, betrag: str, text: str = ""):
        if art == "Anfangsbestand":
            self._pruefe_recht("chef")
        cent = euro_zu_cent(betrag)
        bid = kassenbuch.buchen(self.con, art, cent, text, self._bid)
        if art in ("Einlage", "Entnahme"):
            self._lade(automatisch=True)
        return bid

    @_api()
    def zaehlprotokoll(self, stueckelung: dict):
        return kassenbuch.zaehlprotokoll(self.con, stueckelung, self._bid)

    # ------------------------------------------------------------------ Sicherung

    @_api()
    def sicherung_jetzt(self):
        return str(sicherung.sichern(self.con))

    @_api(recht="chef")
    def sicherungen(self):
        return sicherung.liste(self.con)

    @_api(recht="chef")
    def sicherung_wiederherstellen(self, datei: str, passwort: str = ""):
        if not self.db_pfad:
            raise KassenFehler("Datenbankpfad unbekannt")
        erlaubt = {s["datei"] for s in sicherung.liste(self.con)}
        if datei not in erlaubt:
            raise KassenFehler("Unbekannte Sicherungsdatei")
        sicherung.wiederherstellung_vormerken(datei, self.db_pfad, passwort or geheim.lesen("sicherung"))
        self._ereignis("Wiederherstellung vorgemerkt", Path(datei).name)
        return "Wiederherstellung vorgemerkt – bitte die Kasse jetzt beenden und neu starten."

    @_api(recht="chef")
    def dep_exportieren(self):
        ziel = sicherung.sicherungsziel(self.con) / f"dep-export-{dt.datetime.now():%Y%m%d-%H%M%S}.json"
        return str(dep_export_datei(self.con, ziel))

    @_api(recht="chef")
    def export_steuerberater(self, von: str, bis: str):
        von, bis = _datum(von), _datum(bis)
        ziel = self._ordner("exporte") / f"Steuerberater-{von}-bis-{bis}.zip"
        export.paket(self.con, von, bis, ziel)
        self._ereignis("Export Steuerberater", f"{von} – {bis}")
        self._oeffnen(ziel.parent)
        return str(ziel)

    # ------------------------------------------------------------------ Lieferschein / Rechnung

    @_api()
    def dokument_erstellen(self, typ: str, kunde_id: int, posten: list[dict], zahlungsart: str = "Überweisung"):
        if not kunde_id:
            raise KassenFehler("Bitte zuerst einen Kunden wählen")
        if any(p.get("typ", "artikel") != "artikel" for p in posten):
            raise KassenFehler("Gutscheine bitte über die Kasse (Bar/Karte) abwickeln")
        positionen = self._positionen(posten)
        pos = []
        for p in positionen:
            einzel = p.einzelpreis_cent
            if p.rabatt_cent:  # Rabatt in den Einzelpreis einrechnen
                einzel = int((Decimal(p.summe_cent) / p.menge).quantize(Decimal("1")))
            pos.append(dokumente.DokPosition(p.bezeichnung, p.menge, einzel, p.steuer_prozent, "Stk", p.artikel_id))
        if typ == "Lieferschein":
            dok_id = dokumente.lieferschein(self.con, kunde_id, pos)
            beleg = None
        else:
            dok_id = dokumente.rechnung(self.con, kunde_id, pos, zahlungsart,
                                        self.kasse if zahlungsart in dokumente.BARZAHLUNGEN else None)
            beleg = self.con.execute("SELECT beleg_id FROM dokumente WHERE id = ?", (dok_id,)).fetchone()[0]
            if beleg:
                self.con.execute("UPDATE dokumente SET bezahlt_am = datum WHERE id = ?", (dok_id,))
                self.con.execute("UPDATE belege SET benutzer_id = ? WHERE id = ?", (self._bid, beleg))
                self.con.commit()
        self._lager_buchen(positionen, 1, typ)
        res = {"id": dok_id, "nummer": self.con.execute("SELECT nummer FROM dokumente WHERE id = ?", (dok_id,)).fetchone()[0]}
        if beleg:
            res["beleg"] = self._nach_beleg(beleg)
        return res

    @_api()
    def rechnung_aus_lieferscheinen(self, lieferschein_ids: list[int], zahlungsart: str = "Überweisung"):
        dok_id = dokumente.rechnung_aus_lieferscheinen(
            self.con, lieferschein_ids, zahlungsart, self.kasse if zahlungsart in dokumente.BARZAHLUNGEN else None)
        if zahlungsart in dokumente.BARZAHLUNGEN:
            self.con.execute("UPDATE dokumente SET bezahlt_am = datum WHERE id = ?", (dok_id,))
            self.con.commit()
        return {"id": dok_id, "nummer": self.con.execute("SELECT nummer FROM dokumente WHERE id = ?", (dok_id,)).fetchone()[0]}

    @_api()
    def dokumente(self, typ: str | None = None):
        q = ("SELECT d.*, k.name AS kunde, k.email, date(d.datum, '+' || k.zahlungsziel_tage || ' days') AS faellig,"
             " (SELECT COUNT(*) FROM dokument_bezug b WHERE b.lieferschein_id = d.id) AS verrechnet,"
             " (SELECT SUM(CAST(ROUND(CAST(p.menge AS REAL) * p.einzelpreis_cent) AS INTEGER))"
             "  FROM dokumentpositionen p WHERE p.dokument_id = d.id) AS summe"
             " FROM dokumente d JOIN kunden k ON k.id = d.kunde_id")
        args: list = []
        if typ == "offen":
            q += " WHERE d.typ = 'Rechnung' AND d.bezahlt_am IS NULL"
        elif typ:
            q += " WHERE d.typ = ?"
            args.append(typ)
        heute = dt.date.today().isoformat()
        res = []
        for r in self.con.execute(q + " ORDER BY d.id DESC LIMIT 300", args):
            d = dict(r)
            if d["typ"] == "Rechnung":
                d["status"] = "bezahlt" if d["bezahlt_am"] else ("ueberfaellig" if d["faellig"] < heute else "offen")
            res.append(d)
        return res

    @_api()
    def rechnung_bezahlt(self, dok_id: int, datum: str | None = None):
        self.con.execute("UPDATE dokumente SET bezahlt_am = ? WHERE id = ? AND typ = 'Rechnung'",
                         (_datum(datum) if datum is not False else None, dok_id))
        self.con.commit()
        return True

    @_api()
    def dokument_mailen(self, dok_id: int, an: str | None = None, mit_ebinterface: bool = False):
        from ..printing.a4 import dokument_pdf

        d = self.con.execute("SELECT d.*, k.email FROM dokumente d JOIN kunden k ON k.id = d.kunde_id WHERE d.id = ?",
                             (dok_id,)).fetchone()
        if not d:
            raise KassenFehler("Dokument nicht gefunden")
        an = (an or d["email"] or "").strip()
        anhaenge = [dokument_pdf(self.con, dok_id, self._pdf_pfad(d["nummer"]))]
        if mit_ebinterface and d["typ"] == "Rechnung":
            anhaenge.append(ebinterface.erzeugen(self.con, dok_id, self._ordner("dokumente") / f"{d['nummer']}.xml"))
        betreff, text = mail.dokument_text(self.con, d["typ"], d["nummer"])
        mail.senden(self.con, an, betreff, text, anhaenge)
        self.con.execute("UPDATE dokumente SET gemailt_am = ? WHERE id = ?",
                         (dt.datetime.now().isoformat(timespec="seconds"), dok_id))
        self.con.commit()
        return an

    @_api()
    def ebinterface_export(self, dok_id: int):
        d = self.con.execute("SELECT nummer FROM dokumente WHERE id = ?", (dok_id,)).fetchone()
        if not d:
            raise KassenFehler("Dokument nicht gefunden")
        pfad = ebinterface.erzeugen(self.con, dok_id, self._ordner("dokumente") / f"{d['nummer']}.xml")
        self._oeffnen(pfad.parent)
        return str(pfad)

    # ------------------------------------------------------------------ Einstellungen

    @_api()
    def einstellungen(self):
        standard = {**export.STANDARD_KONTEN, "sicherung_intervall_stunden": "24", "sicherung_behalten": "30",
                    "smtp_port": "587", "auto_abmelden_min": "0", "nach_verkauf": "dialog"}
        return {k: self._e(k, "") or standard.get(k, "") for k in EINSTELLUNGEN}

    @_api(recht="chef")
    def einstellungen_speichern(self, werte: dict):
        geaendert = []
        for k, v in werte.items():
            if k in EINSTELLUNGEN and str(v) != (self._e(k, "") or ""):
                if k == "update_url" and v and not str(v).startswith("https://"):
                    raise ValueError("Update-Adresse muss mit https:// beginnen")
                if k == "akzentfarbe" and v and not re.fullmatch(r"#[0-9a-fA-F]{6}", str(v)):
                    raise ValueError("Farbe im Format #RRGGBB angeben")
                db.setze_einstellung(self.con, k, str(v))
                geaendert.append(k)
        self.con.commit()
        if {"atrust_benutzer", "atrust_umgebung"} & set(geaendert):
            self._signer = None
        if geaendert:
            self._ereignis("Einstellungen geändert", ", ".join(geaendert))
        return True

    @_api(recht="chef")
    def geheimnisse(self):
        return {n: geheim.vorhanden(n) for n in GEHEIMNISSE}

    @_api(recht="chef")
    def geheimnis_setzen(self, name: str, wert: str):
        if name not in GEHEIMNISSE:
            raise ValueError("Unbekannter Eintrag")
        geheim.schreiben(name, wert)
        if name == "atrust":
            self._signer = None
        self._ereignis("Passwort geändert", name)
        return True

    @_api()
    def branding(self):
        return {"logo": self._e("firma_logo", ""), "farbe": self._e("akzentfarbe", "")}

    @_api(recht="chef")
    def logo_setzen(self, data_url: str | None):
        if data_url:
            m = re.fullmatch(r"data:image/(png|jpeg);base64,([A-Za-z0-9+/=]+)", data_url)
            if not m:
                raise ValueError("Logo bitte als PNG oder JPG")
            if len(base64.b64decode(m.group(2))) > 500_000:
                raise ValueError("Logo zu groß (max. 500 KB)")
        db.setze_einstellung(self.con, "firma_logo", data_url or "")
        self.con.commit()
        return True

    @_api(recht="chef")
    def lizenz_setzen(self, schluessel: str):
        info = lizenz.pruefen(schluessel)
        if info["status"] == "ungueltig":
            raise ValueError(info["text"])
        db.setze_einstellung(self.con, "lizenz", schluessel.strip())
        self.con.commit()
        return info

    @_api()
    def drucker_liste(self):
        """Installierte Windows-Drucker (für Bondrucker mit Windows-Standardtreiber)."""
        if sys.platform != "win32":
            return {"drucker": [], "standard": None}
        import win32print  # type: ignore[import-not-found]

        flags = win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
        return {"drucker": sorted(p[2] for p in win32print.EnumPrinters(flags)),
                "standard": win32print.GetDefaultPrinter()}

    @_api(recht="chef")
    def testdruck(self):
        from ..printing.bon import drucker_aus_einstellungen

        try:
            p = drucker_aus_einstellungen(self.con)
            p.set(align="center")
            p.text(f"{self._e('firma_name', '')}\nTestdruck Bondrucker\n{dt.datetime.now():%d.%m.%Y %H:%M}\n")
            p.qr("Testdruck Registrierkasse", size=4, native=False)
            p.cut()
        except Exception as e:
            raise OSError(f"Bondrucker nicht verfügbar: {e}") from e
        return True

    @_api(recht="chef")
    def mail_testen(self, an: str):
        mail.senden(self.con, an, "Testnachricht Registrierkasse", "Der E-Mail-Versand funktioniert.", [])
        return True

    # ------------------------------------------------------------------ Updates

    def update_im_hintergrund(self) -> None:
        def lauf():
            try:
                self._update_info = update.pruefen(self._e("update_url"))
            except update.UpdateFehler as e:
                self._update_fehler = str(e)

        threading.Thread(target=lauf, daemon=True).start()

    @_api(recht="chef")
    def update_pruefen(self):
        self._update_info = update.pruefen(self._e("update_url"))
        return self._update_info

    @_api(recht="chef")
    def update_installieren(self):
        if not self._update_info:
            raise KassenFehler("Kein Update verfügbar")
        sicherung.sichern(self.con)
        setup = update.herunterladen(self._update_info)
        update.installieren(setup)
        self._ereignis("Update gestartet", self._update_info["version"])
        if self._beenden:
            threading.Timer(1.0, self._beenden).start()
        return "Update wird installiert – die Kasse wird neu gestartet."


def oeffentliche_methoden(api: KassenApi) -> dict:
    return {n: getattr(api, n) for n in dir(api)
            if not n.startswith("_") and getattr(getattr(api, n), "oeffentlich", False)}


def standard_api(datenbank: Path | str | None = None) -> KassenApi:
    from ..config import datenbankpfad

    pfad = Path(datenbank or datenbankpfad())
    sicherung.vorgemerkte_wiederherstellung_anwenden(pfad)
    return KassenApi(db.verbinden(pfad), db_pfad=pfad)
