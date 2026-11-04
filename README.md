# Registrierkasse für KMU

RKSV-konforme Registrierkasse für Notebooks (Windows) mit
- **A-Trust a.sign RK Online** (digitale Lizenz) als Signaturerstellungseinheit,
- **Bondrucker** (80 mm, ESC/POS, USB) für das Tagesgeschäft,
- **A4-Lieferscheinen und -Rechnungen** für Geschäftskunden,
- **automatischer Datensicherung** (inkl. DEP-Export),
- einmaligem **Import aus QRK** (Firmendaten, Steuersätze, Warengruppen, Artikel).

> Das Programm enthält keine Kunden- oder Kassendaten. Diese liegen ausschließlich
> lokal im Datenverzeichnis des Benutzers (`%APPDATA%\Registrierkasse`) und werden
> per `.gitignore` aus dem Repository ferngehalten.

## Stand

| Bereich | Status |
|---|---|
| RKSV-Kern: Belegkette, Umsatzzähler (AES-256-ICM), JWS/ES256, Start-/Null-/Monats-/Jahres-/Schlussbeleg, Storno, Training | ✅ mit Tests |
| Ausfall der Signatureinheit → Kennzeichnung + automatischer Sammelbeleg | ✅ mit Tests |
| DEP7-Export | ✅ |
| A-Trust Online-Anbindung (REST) | ⚠️ implementiert, Test gegen A-Trust-Testumgebung ausständig |
| Bondruck ESC/POS inkl. QR-Code | ✅ (Test mit Dummy-Drucker) |
| A4-Lieferschein/-Rechnung (PDF), Sammelrechnung aus Lieferscheinen | ✅ |
| QRK-Import | ✅ (gegen nachgebaute QRK-DB getestet, echte Sicherung ausständig) |
| Automatische Datensicherung mit Rotation, Integritätsprüfung, Windows-Aufgabenplanung | ✅ |
| Kassenoberfläche (modernes Glas-Design) | ⏳ nächster Schritt |

## Installation (Entwicklung)

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -e .[dev]
pytest
```

## Ablauf: Umstieg von QRK

1. **QRK abschließen:** in QRK den DEP-Export erstellen und sichern (7 Jahre aufbewahren),
   Schlussbeleg erstellen, alte Kasse in FinanzOnline außer Betrieb nehmen.
2. **Neue Kasse einrichten**, zunächst gegen die A-Trust-Testumgebung:
   ```bash
   kasse init KASSE-01 --signer atrust --atrust-benutzer <BENUTZER> --atrust-umgebung test
   set KASSE_ATRUST_PASSWORT=<PASSWORT>
   ```
   AES-Schlüssel und Prüfwert werden ausgegeben → in FinanzOnline registrieren.
3. **Daten aus QRK übernehmen:**
   ```bash
   kasse import-qrk D:\Downloads\qrk_20261028-1 --inspizieren   # nur Schema anzeigen
   kasse import-qrk D:\Downloads\qrk_20261028-1 --probelauf     # anzeigen, nichts schreiben
   kasse import-qrk D:\Downloads\qrk_20261028-1                 # übernehmen
   kasse artikel
   ```
4. **Startbeleg** erstellen und mit der **BMF Belegcheck-App** prüfen:
   `kasse startbeleg --drucken`
5. Drucker und Sicherung konfigurieren (siehe unten).

## Einstellungen

```bash
kasse set firma_name "Muster GmbH"
kasse set firma_adresse "Hauptstraße 1\n1010 Wien"
kasse set firma_uid ATU12345678
kasse set firma_iban AT00...
kasse set bon_fusszeile "Danke für Ihren Einkauf!"

# Bondrucker über Windows-Treiber (empfohlen)
kasse set bondrucker_art windows
kasse set bondrucker_name "EPSON TM-T20III Receipt"
# alternativ direkt per USB (WinUSB/libusb-Treiber nötig)
kasse set bondrucker_art usb
kasse set bondrucker_vendor 04b8
kasse set bondrucker_product 0e28

# Datensicherung
kasse set sicherung_ziel "E:\Kassensicherung"     # USB-Stick/NAS/OneDrive – nicht dasselbe Laufwerk!
kasse set sicherung_behalten 30
kasse sicherung-planen --uhrzeit 21:00            # tägliche Windows-Aufgabe
kasse sicherung                                   # sofort sichern
```

Das A-Trust-Passwort wird **nicht** in der Datenbank gespeichert, sondern aus der
Umgebungsvariable `KASSE_ATRUST_PASSWORT` gelesen.

## RKSV-Pflichten im Betrieb (Erinnerung)

- **Monatsbeleg** am Monatsende: `kasse nullbeleg --art Monatsbeleg` (sichert automatisch)
- **Jahresbeleg** (= Dezember-Monatsbeleg): mit Belegcheck-App prüfen, Sicherung extern verwahren
- Ausfall der Signatureinheit > 48 h → Meldung in FinanzOnline
- DEP und Belege 7 Jahre aufbewahren

## Architektur

```
src/kasse/
  rksv/krypto.py     Umsatzzähler, Verkettung, JWS-Hilfen
  rksv/signatur.py   A-Trust Online, lokaler Test-Signer
  rksv/kasse.py      Belegerstellung, Storno, Training, Ausfall, Sonderbelege
  rksv/dep.py        DEP7-Export
  dokumente.py       Lieferscheine, Rechnungen, Sammelrechnungen
  printing/bon.py    ESC/POS-Bon mit QR-Code
  printing/a4.py     A4-PDF (reportlab)
  importer/qrk.py    QRK-Import (nur lesend)
  sicherung.py       automatische Datensicherung
  cli.py             Kommandozeile
```

Rechtlicher Hinweis: Die RKSV-Konformität ist vor dem Echtbetrieb mit der
A-Trust-Testumgebung, der BMF Belegcheck-App und dem Steuerberater zu prüfen.
