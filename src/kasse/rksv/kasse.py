"""RKSV-Kassenkern: Belegerstellung, Signatur, Verkettung, Umsatzzähler, Ausfallsbehandlung."""

from __future__ import annotations

import datetime as dt
import json
import sqlite3
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from ..db import einstellung, setze_einstellung
from ..geld import rksv_betrag
from . import krypto
from .signatur import Signer, SignaturFehler

RKSV_SAETZE = ("Normal", "Ermaessigt-1", "Ermaessigt-2", "Null", "Besonders")
_SPALTE = {
    "Normal": "betrag_normal",
    "Ermaessigt-1": "betrag_ermaessigt1",
    "Ermaessigt-2": "betrag_ermaessigt2",
    "Null": "betrag_null",
    "Besonders": "betrag_besonders",
}

NULLBELEG_ARTEN = ("Nullbeleg", "Monatsbeleg", "Jahresbeleg", "Sammelbeleg", "Schlussbeleg")


class KassenFehler(RuntimeError):
    pass


@dataclass
class Position:
    bezeichnung: str
    menge: Decimal
    einzelpreis_cent: int  # brutto
    steuer_prozent: str
    artikel_id: int | None = None
    rabatt_cent: int = 0  # Rabatt auf die gesamte Position (brutto, positiv)

    @property
    def brutto_vor_rabatt(self) -> int:
        return int((self.menge * self.einzelpreis_cent).quantize(Decimal("1"), rounding=ROUND_HALF_UP))

    @property
    def summe_cent(self) -> int:
        return self.brutto_vor_rabatt - self.rabatt_cent


class Kasse:
    def __init__(self, con: sqlite3.Connection, signer: Signer, uhr=None):
        self.con = con
        self.signer = signer
        self._uhr = uhr or (lambda: dt.datetime.now().replace(microsecond=0))

    # ------------------------------------------------------------------ Einrichtung

    @staticmethod
    def einrichten(con: sqlite3.Connection, kassen_id: str) -> str:
        """Legt Kassen-ID und AES-Schlüssel an. Liefert den AES-Schlüssel (für FinanzOnline)."""
        if einstellung(con, "kassen_id"):
            raise KassenFehler("Kasse ist bereits eingerichtet")
        if not kassen_id or "_" in kassen_id:
            raise KassenFehler("Kassen-ID darf nicht leer sein und kein '_' enthalten")
        schluessel = krypto.neuer_aes_schluessel()
        setze_einstellung(con, "kassen_id", kassen_id)
        setze_einstellung(con, "aes_schluessel", schluessel)
        con.commit()
        return schluessel

    @property
    def kassen_id(self) -> str:
        k = einstellung(self.con, "kassen_id")
        if not k:
            raise KassenFehler("Kasse ist nicht eingerichtet (kasse init)")
        return k

    @property
    def _aes(self) -> str:
        return einstellung(self.con, "aes_schluessel")  # type: ignore[return-value]

    # ------------------------------------------------------------------ Status

    def _letzter(self) -> sqlite3.Row | None:
        return self.con.execute("SELECT * FROM belege ORDER BY belegnummer DESC LIMIT 1").fetchone()

    def umsatzzaehler(self) -> int:
        row = self._letzter()
        return row["umsatzzaehler"] if row else 0

    def ist_gestartet(self) -> bool:
        return self._letzter() is not None

    def ist_geschlossen(self) -> bool:
        row = self._letzter()
        return bool(row and row["art"] == "Schlussbeleg")

    def ausfall_aktiv(self) -> bool:
        return einstellung(self.con, "ausfall_seit") is not None

    # ------------------------------------------------------------------ Zertifikat

    def _zertifikat_serie(self, pflicht: bool = False) -> str:
        try:
            z = self.signer.zertifikat()
        except SignaturFehler:
            if pflicht:
                raise
            serie = einstellung(self.con, "zertifikat_serie")
            if not serie:
                raise
            return serie
        setze_einstellung(self.con, "zertifikat_serie", z.seriennummer)
        setze_einstellung(
            self.con,
            f"zertifikat:{z.seriennummer}",
            json.dumps({"zertifikat": z.zertifikat_b64, "stellen": z.zertifizierungsstellen}),
        )
        return z.seriennummer

    # ------------------------------------------------------------------ Kern

    def _erstelle(
        self,
        art: str,
        betraege: dict[str, int],
        positionen: list[Position] | None = None,
        *,
        zahlungsart: str | None = None,
        kunde_id: int | None = None,
        storno_von: int | None = None,
        ausfall_erlaubt: bool = True,
        zahlungen: list[tuple[str, int, str | None]] | None = None,
        benutzer_id: int | None = None,
    ) -> int:
        if self.ist_geschlossen():
            raise KassenFehler("Kasse wurde mit Schlussbeleg außer Betrieb genommen")
        if art != "Startbeleg" and not self.ist_gestartet():
            raise KassenFehler("Zuerst den Startbeleg erstellen")

        letzter = self._letzter()
        belegnummer = (letzter["belegnummer"] + 1) if letzter else 1
        zeit = self._uhr().isoformat(timespec="seconds")
        kassen_id = self.kassen_id

        summe = sum(betraege.values())
        zaehler_neu = self.umsatzzaehler() + (0 if art == "Training" else summe)
        if art == "Training":
            zaehler_feld = krypto.TRAINING_MARKER
        elif art == "Storno":
            zaehler_feld = krypto.STORNO_MARKER
        else:
            zaehler_feld = krypto.umsatzzaehler_verschluesseln(zaehler_neu, kassen_id, str(belegnummer), self._aes)

        serie = self._zertifikat_serie(pflicht=art == "Startbeleg")
        kette = krypto.kettenwert(letzter["jws"] if letzter else kassen_id)

        payload = "_".join(
            [
                f"_R1-{self.signer.zda_id}",
                kassen_id,
                str(belegnummer),
                zeit,
                *(rksv_betrag(betraege.get(s, 0)) for s in RKSV_SAETZE),
                zaehler_feld,
                serie,
                kette,
            ]
        )

        ausfall = False
        try:
            jws = self.signer.signiere_jws(payload)
        except SignaturFehler:
            if not ausfall_erlaubt:
                raise
            jws = krypto.ausfall_jws(payload)
            ausfall = True

        cur = self.con.execute(
            "INSERT INTO belege (belegnummer, art, zeitpunkt, kunde_id, zahlungsart, betrag_normal,"
            " betrag_ermaessigt1, betrag_ermaessigt2, betrag_null, betrag_besonders, umsatzzaehler,"
            " zertifikat_serie, jws, ausfall, storno_von, benutzer_id) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                belegnummer, art, zeit, kunde_id, zahlungsart,
                *(betraege.get(s, 0) for s in RKSV_SAETZE),
                zaehler_neu, serie, jws, int(ausfall), storno_von, benutzer_id,
            ),
        )
        beleg_id = cur.lastrowid
        for i, p in enumerate(positionen or [], start=1):
            self.con.execute(
                "INSERT INTO belegpositionen (beleg_id, pos, artikel_id, bezeichnung, menge, einzelpreis_cent,"
                " steuer_prozent, summe_cent, rabatt_cent) VALUES (?,?,?,?,?,?,?,?,?)",
                (beleg_id, i, p.artikel_id, p.bezeichnung, str(p.menge), p.einzelpreis_cent,
                 p.steuer_prozent, p.summe_cent, p.rabatt_cent),
            )
        for art_z, betrag, referenz in zahlungen or []:
            self.con.execute("INSERT INTO zahlungen (beleg_id, art, betrag_cent, referenz) VALUES (?,?,?,?)",
                             (beleg_id, art_z, betrag, referenz))
        if ausfall and not self.ausfall_aktiv():
            setze_einstellung(self.con, "ausfall_seit", zeit)
        self.con.commit()
        return beleg_id

    def _nach_ausfall_sammelbeleg(self) -> None:
        """Nach Wiederherstellung der Signatur ist ein signierter Sammelbeleg (Nullbeleg) zu erstellen."""
        if not self.ausfall_aktiv():
            return
        try:
            self._erstelle("Sammelbeleg", {}, ausfall_erlaubt=False)
        except SignaturFehler:
            return
        self.con.execute("DELETE FROM einstellungen WHERE schluessel = 'ausfall_seit'")
        self.con.commit()

    # ------------------------------------------------------------------ öffentliche API

    def startbeleg(self) -> int:
        if self.ist_gestartet():
            raise KassenFehler("Startbeleg existiert bereits")
        return self._erstelle("Startbeleg", {}, ausfall_erlaubt=False)

    def nullbeleg(self, art: str = "Nullbeleg") -> int:
        if art not in NULLBELEG_ARTEN:
            raise KassenFehler(f"Unbekannte Nullbeleg-Art: {art}")
        self._nach_ausfall_sammelbeleg()
        # Monats-/Jahres-/Schlussbelege müssen signiert sein
        return self._erstelle(art, {}, ausfall_erlaubt=art in ("Nullbeleg",))

    def _rksv_satz(self, prozent: str) -> str:
        row = self.con.execute("SELECT rksv_satz FROM steuersaetze WHERE prozent = ?", (prozent,)).fetchone()
        if not row:
            raise KassenFehler(f"Unbekannter Steuersatz: {prozent} %")
        return row[0]

    def _betraege(self, positionen: list[Position], vorzeichen: int = 1) -> dict[str, int]:
        b: dict[str, int] = {}
        for p in positionen:
            s = self._rksv_satz(p.steuer_prozent)
            b[s] = b.get(s, 0) + vorzeichen * p.summe_cent
        return b

    def verkauf(
        self,
        positionen: list[Position],
        zahlungsart: str = "Bar",
        kunde_id: int | None = None,
        training: bool = False,
        zahlungen: list[tuple[str, int, str | None]] | None = None,
        benutzer_id: int | None = None,
    ) -> int:
        """Barumsatz. ``zahlungen`` = [(Art, Betrag in Cent, Referenz)] für Mischzahlungen."""
        if not positionen:
            raise KassenFehler("Keine Positionen")
        for p in positionen:
            if p.rabatt_cent and abs(p.rabatt_cent) > abs(p.brutto_vor_rabatt):
                raise KassenFehler(f"Rabatt höher als Positionsbetrag: {p.bezeichnung}")
        summe = sum(p.summe_cent for p in positionen)
        if zahlungen is None:
            zahlungen = [(zahlungsart, summe, None)]
        else:
            if sum(z[1] for z in zahlungen) != summe:
                raise KassenFehler("Summe der Zahlungen entspricht nicht dem Belegbetrag")
            arten = []
            for z in zahlungen:
                if z[0] not in arten:
                    arten.append(z[0])
            zahlungsart = "+".join(arten) or zahlungsart
        self._nach_ausfall_sammelbeleg()
        return self._erstelle(
            "Training" if training else "Barumsatz",
            self._betraege(positionen),
            positionen,
            zahlungsart=zahlungsart,
            kunde_id=kunde_id,
            zahlungen=[] if training else zahlungen,
            benutzer_id=benutzer_id,
        )

    def storno(self, beleg_id: int, benutzer_id: int | None = None) -> int:
        orig = self.con.execute("SELECT * FROM belege WHERE id = ?", (beleg_id,)).fetchone()
        if not orig or orig["art"] != "Barumsatz":
            raise KassenFehler("Nur Barumsatz-Belege können storniert werden")
        if self.con.execute("SELECT 1 FROM belege WHERE storno_von = ?", (beleg_id,)).fetchone():
            raise KassenFehler("Beleg wurde bereits storniert")
        positionen = [
            Position(r["bezeichnung"], -Decimal(r["menge"]), r["einzelpreis_cent"], r["steuer_prozent"], r["artikel_id"],
                     -r["rabatt_cent"])
            for r in self.con.execute("SELECT * FROM belegpositionen WHERE beleg_id = ? ORDER BY pos", (beleg_id,))
        ]
        self._nach_ausfall_sammelbeleg()
        return self._erstelle(
            "Storno", self._betraege(positionen), positionen,
            zahlungsart=orig["zahlungsart"], kunde_id=orig["kunde_id"], storno_von=beleg_id,
            zahlungen=[(z["art"], -z["betrag_cent"], z["referenz"]) for z in
                       self.con.execute("SELECT * FROM zahlungen WHERE beleg_id = ?", (beleg_id,))],
            benutzer_id=benutzer_id,
        )

    def schlussbeleg(self) -> int:
        return self.nullbeleg("Schlussbeleg")

    def qr_inhalt(self, beleg_id: int) -> str:
        row = self.con.execute("SELECT jws FROM belege WHERE id = ?", (beleg_id,)).fetchone()
        return krypto.maschinenlesbarer_code(row["jws"])
