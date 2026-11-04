# Registrierkasse für KMU

Hersteller und Support: **[www.kiber.at](https://www.kiber.at)** – dort ist auch die für den Echtbetrieb
nötige **A-Trust-Registrierkassenlizenz (a.sign RK Online)** erhältlich.

RKSV-konforme Registrierkasse für Windows-Notebooks mit moderner Glas-Oberfläche:
A-Trust-Onlinesignatur, Bondrucker und A4-Rechnungen, Kartenzahlung per Smartphone,
Kassenbuch, Benutzer mit PIN, verschlüsselte Datensicherung und Export für den Steuerberater.

> Das Programm enthält keine Kunden- oder Kassendaten. Diese liegen ausschließlich
> lokal unter `%APPDATA%\Registrierkasse`; Passwörter in der Windows-Anmeldeinformationsverwaltung.

## Funktionen

| Bereich | Inhalt |
|---|---|
| **RKSV** | Belegkette, Umsatzzähler (AES-256-ICM), JWS/ES256, Start-/Null-/Monats-/Jahres-/Schlussbeleg, Storno, Training, Ausfall mit Sammelbeleg, Hinweis bei Ausfall > 48 h, DEP7-Export |
| **Signatur** | A-Trust a.sign RK Online (Passwort im Windows-Tresor), Verbindungstest; lokaler Test-Signer für Entwicklung |
| **Kassa** | Artikelkacheln, Barcode, Rabatt je Position oder auf den Einkauf, Bar mit Rückgeld, Karte, geteilte Zahlung (Bar + Karte), Wertgutscheine (Verkauf/Einlösung), Trainingsmodus, Kassenlade |
| **Kartenzahlung** | manuell bestätigt (jede App / jedes Terminal) oder automatisch über Viva.com Tap to Pay (Cloud-Terminal-API) |
| **Ausgabe** | nach jedem Verkauf Bon / A4 (Druckerwahl) / PDF / E-Mail; Logo auf A4 und optional am Bon |
| **Geschäftskunden** | Kunden, Lieferscheine, Rechnungen, Sammelrechnung, offene/überfällige Rechnungen, Zahlungseingang, EPC-QR-Code, E-Rechnung ebInterface 6.1, E-Mail-Versand |
| **Benutzer** | PIN-Anmeldung, Rollen Chef/Kassier, automatisches Abmelden, Ereignisprotokoll |
| **Kassenbuch** | Anfangsbestand, Einlagen/Entnahmen, Kassastand, Kassasturz (Zählprotokoll) mit Differenzbuchung |
| **Lager** | Lagerstand, Mindestbestand, Wareneingang, Hinweis „nachbestellen“ |
| **Auswertung** | Tagesbericht, Statistik (Umsatz je Tag/Monat, Top-Artikel, Warengruppen, Uhrzeit) |
| **Steuerberater** | ZIP mit Belegen (CSV), Rechnungen (CSV), BMD-Buchungen (Tageslosungen) und DEP |
| **Sicherung** | automatisch (Start, alle 30 min geprüft, Monatsbeleg, Windows-Aufgabe), AES-256-verschlüsselt, Rotation, Wiederherstellung |
| **Betrieb** | Windows-Installer, automatische Updates aus den GitHub-Releases (mit Prüfsumme), eigenes Logo/Akzentfarbe |
| **Import** | einmalig aus QRK: Firmendaten, Steuersätze, Warengruppen, Artikel |

## Installation

**Für Anwender:** Den Installer der neuesten Version herunterladen und ausführen:

**➜ [Registrierkasse – Download (neueste Version)](https://github.com/lukpra21/Registrierkasse/releases/latest)**

Optional: Desktop-Symbol, Autostart, tägliche Sicherung um 21:00. Spätere Versionen erkennt die
Kasse selbst und installiert sie auf Knopfdruck (*Einstellungen → Updates*).

**Für Entwicklung:**

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e .[alles,dev]
pytest
kasse-ui              # Programmfenster (Edge WebView2)
kasse-ui --browser    # im Browser (nur 127.0.0.1)
```

## Erste Schritte

> Für den Echtbetrieb wird eine A-Trust-Registrierkassenlizenz benötigt – erhältlich über
> [www.kiber.at](https://www.kiber.at). Ohne Lizenz lässt sich die Kasse im Modus „Lokaler Test“ ausprobieren.

1. **QRK abschließen:** DEP-Export sichern (7 Jahre aufbewahren), Schlussbeleg, alte Kasse in FinanzOnline außer Betrieb nehmen.
2. **Kasse einrichten** (Assistent beim ersten Start): Kassen-ID, A-Trust-Zugang (zuerst *Testumgebung*).
   AES-Schlüssel und Prüfwert in FinanzOnline registrieren.
3. **Daten aus QRK übernehmen:**
   ```bash
   kasse-cli import-qrk D:\Downloads\qrk_20261028-1 --inspizieren
   kasse-cli import-qrk D:\Downloads\qrk_20261028-1 --probelauf
   kasse-cli import-qrk D:\Downloads\qrk_20261028-1
   ```
4. **Startbeleg** erstellen und mit der **BMF-Belegcheck-App** prüfen.
5. **Einstellungen:** Firmendaten, Logo, Bondrucker + Testdruck, Kassenlade, A4-Drucker, Sicherungsordner
   und Sicherungspasswort, Benutzer (der erste ist Chef), E-Mail, Kartenzahlung.
6. **Einstellungen → A-Trust → Verbindung testen**, danach auf *Produktiv* umstellen.

## Drucken

**Briefpapier (A4)** – *Einstellungen → Briefpapier*: eigenes Briefpapier als PDF/PNG/JPG (Seite 1 und
Folgeseiten getrennt), Seitenränder, Position der Anschrift für Fensterkuverts (DIN 5008), Logo-Position und
-Größe, Schriftart/-größe, Farbe des Tabellenkopfs, Absender- und Fußzeile, Einleitungs- und Schlusstexte
für Rechnung und Lieferschein. Die Vorschau zeigt eine Musterrechnung mit den aktuellen (auch noch nicht
gespeicherten) Eingaben.

**Bondrucker-Papier** – *Einstellungen → Bondrucker-Papier*: 80 oder 58 mm, Zeichen pro Zeile,
Druckbreite, Schrift A/B, Druckerprofil (für korrekte Umlaute und €), Kopftext, QR-Code-Größe, Vorschub
und Abschnitt (Teil-/Vollschnitt/kein). Die Vorschau zeigt den letzten Beleg in der eingestellten Breite.

- **Bondrucker** mit Windows-Treiber (z. B. „POS-80“) auswählen; die Kasse sendet ESC/POS über den Treiber.
  Kassenlade am Bondrucker: *Einstellungen → Drucker & Kassenlade*.
- **A4** auf jedem installierten Drucker; der Installer legt SumatraPDF für stilles Drucken bei.
- **PDF** landet unter `%APPDATA%\Registrierkasse\dokumente`.

## Kartenzahlung

- **Manuell:** Betrag in einer beliebigen Tap-to-Pay-App bzw. am Terminal kassieren, in der Kasse bestätigen.
- **Viva.com (automatisch):** In der Viva-Terminal-App am Smartphone anmelden; im Viva-Händlerportal
  API-Zugang (Client-ID/Secret) und Terminal-ID erzeugen und unter *Einstellungen → Kartenzahlung* eintragen.
  Zuerst mit einem **Demo-Konto** testen – Endpunkte siehe `src/kasse/terminal.py`.

## Updates

- Neue Version veröffentlichen: Version in `src/kasse/__init__.py` und `pyproject.toml` erhöhen, committen und
  pushen. Dann auf GitHub unter *Actions → Windows-Installer → Run workflow* mit Häkchen
  **„Als GitHub-Release veröffentlichen“** starten (alternativ Tag `v0.4.0` pushen). Der Workflow testet,
  baut den Installer und veröffentlicht ihn samt `update.json` als GitHub-Release.
- Jede Kasse prüft beim Start `https://github.com/lukpra21/Registrierkasse/releases/latest/download/update.json`,
  zeigt verfügbare Updates in der Kopfzeile an und installiert sie auf Knopfdruck (vorher automatische Sicherung,
  Prüfsumme wird kontrolliert, nur Installer aus diesem Repository werden akzeptiert).

## Kommandozeile (`kasse-cli`)

```text
init, info, set, import-qrk, artikel, startbeleg, nullbeleg, verkauf, dep-export,
sicherung, sicherung-planen, wiederherstellen, atrust-test, passwort, export, selbsttest
```

## Daten wiederherstellen

*Abschluss → Wiederherstellen* (oder *Einstellungen → Datensicherung*), bei einem neuen Notebook direkt im
Einrichtungsassistenten (*Aus Sicherung wiederherstellen*):

1. Sicherung wählen – aus dem Sicherungsordner oder als Datei (USB-Stick, anderer PC).
2. Bei verschlüsselten Sicherungen das Sicherungspasswort eingeben.
3. Vergleich prüfen: Firma, Kassen-ID, Belege, letzter Beleg, Artikel, Kunden, Rechnungen, Benutzer.
   Gehen neuere Belege verloren oder passt die Kassen-ID nicht, warnt die Kasse und verlangt eine Bestätigung.
4. *Jetzt wiederherstellen* – ohne Neustart. Der aktuelle Stand wird vorher automatisch gesichert, die bisherige
   Datenbank bleibt als `kasse-vor-wiederherstellung-….db` erhalten. Danach ist eine neue Anmeldung nötig.

Notfall über die Kommandozeile (Kasse vorher beenden):

```bash
kasse-cli wiederherstellen E:\Kassensicherung\kasse-sicherung-….rksich
```

Nach einer Wiederherstellung empfiehlt sich ein Nullbeleg mit Prüfung durch die BMF-Belegcheck-App.

## Belegkette prüfen

```bash
python tools/dep_pruefen.py dep-export.json --aes <AES-Schlüssel>
```

Prüft jede Signatur, die lückenlose Verkettung und den verschlüsselten Umsatzzähler – z. B. vor der
Übergabe an den Steuerberater oder nach einer Wiederherstellung.

## RKSV-Pflichten im Betrieb

- **Monatsbeleg** am Monatsende (Hinweis in der Kopfzeile), **Jahresbeleg** im Dezember mit Belegcheck prüfen
- Ausfall der Signatureinheit > 48 h → Meldung in FinanzOnline (die Kasse weist darauf hin)
- DEP und Belege 7 Jahre aufbewahren (Sicherungen extern verwahren)

## Architektur

```
src/kasse/
  rksv/           Belegkern, Krypto, Signatur (A-Trust/Test), DEP
  benutzer.py     PIN/Rollen          kassenbuch.py   Kassastand, Zählprotokoll
  gutscheine.py   Wertgutscheine      dokumente.py    Lieferscheine, Rechnungen
  terminal.py     Kartenterminal      mail.py         E-Mail-Versand
  ebinterface.py  E-Rechnung          export.py       Steuerberater/BMD
  sicherung.py    Sicherung           geheim.py       Windows-Anmeldeinformationsverwaltung
  update.py       Updates (GitHub-Releases)
  printing/       Bon (ESC/POS), A4 (PDF)
  importer/qrk.py QRK-Import          ui/             Oberfläche (pywebview + HTML/CSS/JS)
packaging/        PyInstaller, Inno Setup, Programmsymbol
tools/dep_pruefen.py  unabhängige Prüfung eines DEP-Exports (Signaturen, Verkettung, Umsatzzähler)
.github/workflows Tests (Windows + Linux), Installer-Build
```

## Vor dem Echtbetrieb prüfen

Diese Punkte lassen sich nur mit echten Zugängen bzw. Geräten testen:

- A-Trust-Anbindung gegen die Testumgebung, danach alle Belegtypen mit der BMF-Belegcheck-App
- Viva.com Cloud-Terminal mit Demo-Konto
- Bondrucker, Kassenlade und A4-Druck am Notebook
- ebInterface-Datei mit dem offiziellen Validator; BMD-Feldbelegung und Konten mit dem Steuerberater
- umsatzsteuerliche Behandlung von Gutscheinen mit dem Steuerberater
