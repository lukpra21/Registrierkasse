"""Kartenterminals.

- ``ManuellesTerminal``: Betrag wird am Terminal/Handy händisch kassiert und in der Kasse bestätigt.
- ``VivaCloudTerminal``: Viva.com Cloud Terminal API – die Kasse schickt den Betrag an die
  Viva-Terminal-App am Smartphone (Tap to Pay) und fragt das Ergebnis ab.

Viva-Ablauf (ECR Cloud API):
  1. OAuth2-Token (Client Credentials) von accounts.vivapayments.com
  2. POST /ecr/v1/transactions:sale  {sessionId, terminalId, cashRegisterId, amount, currencyCode, ...}
  3. GET  /ecr/v1/sessions/{sessionId} bis ein Ergebnis vorliegt
  4. Abbruch: DELETE /ecr/v1/sessions/{sessionId}?cashRegisterId=…

Endpunkte und Felder vor dem Echtbetrieb mit einem Viva-Demo-Konto prüfen
(Umgebung "demo" in den Einstellungen).
"""

from __future__ import annotations

import base64
import json
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from dataclasses import dataclass

from . import geheim
from .db import einstellung

VIVA = {
    "demo": {"konto": "https://demo-accounts.vivapayments.com", "api": "https://demo-api.vivapayments.com"},
    "produktiv": {"konto": "https://accounts.vivapayments.com", "api": "https://api.vivapayments.com"},
}


class TerminalFehler(RuntimeError):
    pass


@dataclass
class TerminalStatus:
    zustand: str  # "laeuft" | "erfolg" | "fehler" | "abgebrochen"
    referenz: str | None = None
    meldung: str = ""


class ManuellesTerminal:
    automatisch = False

    def starten(self, betrag_cent: int, referenz: str) -> str:
        return "manuell"

    def status(self, sitzung: str) -> TerminalStatus:
        return TerminalStatus("laeuft")

    def abbrechen(self, sitzung: str) -> None:
        pass


class VivaCloudTerminal:
    automatisch = True

    def __init__(self, client_id: str, client_secret: str, terminal_id: str, kassen_id: str,
                 umgebung: str = "demo", timeout: float = 15.0):
        self.client_id = client_id
        self._secret = client_secret
        self.terminal_id = terminal_id
        self.kassen_id = kassen_id
        self.url = VIVA[umgebung]
        self.timeout = timeout
        self._token: tuple[str, float] | None = None

    def _anfrage(self, methode: str, url: str, daten: dict | None = None, token: bool = True,
                 form: dict | None = None) -> tuple[int, dict]:
        kopf = {"Accept": "application/json"}
        body = None
        if form is not None:
            body = urllib.parse.urlencode(form).encode()
            kopf["Content-Type"] = "application/x-www-form-urlencoded"
            kopf["Authorization"] = "Basic " + base64.b64encode(f"{self.client_id}:{self._secret}".encode()).decode()
        elif daten is not None:
            body = json.dumps(daten).encode()
            kopf["Content-Type"] = "application/json"
        if token:
            kopf["Authorization"] = f"Bearer {self._zugriff()}"
        req = urllib.request.Request(url, data=body, method=methode, headers=kopf)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                inhalt = r.read()
                return r.status, (json.loads(inhalt) if inhalt else {})
        except urllib.error.HTTPError as e:
            inhalt = e.read()
            try:
                return e.code, json.loads(inhalt) if inhalt else {}
            except json.JSONDecodeError:
                return e.code, {"message": inhalt.decode(errors="replace")}
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            raise TerminalFehler(f"Viva nicht erreichbar: {e}") from e

    def _zugriff(self) -> str:
        if self._token and self._token[1] > time.time() + 30:
            return self._token[0]
        code, d = self._anfrage("POST", f"{self.url['konto']}/connect/token", token=False,
                                form={"grant_type": "client_credentials"})
        if code != 200 or "access_token" not in d:
            raise TerminalFehler(f"Viva-Anmeldung fehlgeschlagen ({code}): {d}")
        self._token = (d["access_token"], time.time() + int(d.get("expires_in", 3600)))
        return self._token[0]

    def starten(self, betrag_cent: int, referenz: str) -> str:
        sitzung = str(uuid.uuid4())
        code, d = self._anfrage("POST", f"{self.url['api']}/ecr/v1/transactions:sale", {
            "sessionId": sitzung,
            "terminalId": self.terminal_id,
            "cashRegisterId": self.kassen_id,
            "amount": betrag_cent,
            "currencyCode": "978",
            "merchantReference": referenz,
            "customerTrns": referenz,
            "preauth": False,
            "maxInstalments": 0,
            "tipAmount": 0,
        })
        if code not in (200, 201, 202, 204):
            raise TerminalFehler(f"Zahlung konnte nicht gestartet werden ({code}): {d.get('message', d)}")
        return sitzung

    def status(self, sitzung: str) -> TerminalStatus:
        code, d = self._anfrage("GET", f"{self.url['api']}/ecr/v1/sessions/{sitzung}")
        if code in (202, 404) or (code == 200 and d.get("success") is None):
            return TerminalStatus("laeuft")
        if code != 200:
            return TerminalStatus("fehler", meldung=str(d.get("message", d)))
        if d.get("success"):
            return TerminalStatus("erfolg", referenz=str(d.get("transactionId") or d.get("orderCode") or sitzung),
                                  meldung=d.get("message", ""))
        meldung = d.get("message") or d.get("eventId") or "abgelehnt"
        zustand = "abgebrochen" if "abort" in str(meldung).lower() or "cancel" in str(meldung).lower() else "fehler"
        return TerminalStatus(zustand, meldung=str(meldung))

    def abbrechen(self, sitzung: str) -> None:
        self._anfrage("DELETE", f"{self.url['api']}/ecr/v1/sessions/{sitzung}?"
                      + urllib.parse.urlencode({"cashRegisterId": self.kassen_id}))


def terminal_aus_einstellungen(con):
    if einstellung(con, "karten_terminal", "manuell") != "viva":
        return ManuellesTerminal()
    client_id = einstellung(con, "viva_client_id")
    terminal_id = einstellung(con, "viva_terminal_id")
    secret = geheim.lesen("viva")
    if not (client_id and terminal_id and secret):
        raise TerminalFehler("Viva-Zugangsdaten unvollständig (Einstellungen → Kartenzahlung)")
    return VivaCloudTerminal(client_id, secret, terminal_id, einstellung(con, "kassen_id", "KASSE") or "KASSE",
                             einstellung(con, "viva_umgebung", "demo") or "demo")
