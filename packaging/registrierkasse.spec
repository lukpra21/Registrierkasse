# PyInstaller-Spezifikation: erzeugt dist/Registrierkasse/ mit
#   Registrierkasse.exe  – Kassenoberfläche (ohne Konsolenfenster)
#   kasse-cli.exe        – Kommandozeile (Import, Sicherung, Aufgabenplanung)
# Aufruf (im Repository-Hauptordner):  pyinstaller packaging/registrierkasse.spec

import os

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

P = lambda *t: os.path.join(SPECPATH, *t)  # noqa: E731 – Pfade relativ zu dieser Datei
daten = [(P("..", "src", "kasse", "ui", "web"), os.path.join("kasse", "ui", "web"))]
daten += collect_data_files("escpos")
daten += collect_data_files("reportlab")
daten += collect_data_files("barcode")
# reportlab und python-escpos laden Teile (Barcodes, QR, Druckerprofile) dynamisch nach –
# deshalb vollständig einbinden, sonst schlägt die PDF-/Bon-Ausgabe im installierten Programm fehl
versteckt = (collect_submodules("keyring.backends") + collect_submodules("kasse")
             + collect_submodules("reportlab.graphics") + collect_submodules("reportlab.pdfbase")
             + collect_submodules("escpos") + collect_submodules("qrcode") + collect_submodules("barcode")
             + ["win32timezone", "win32print", "win32api", "win32cred", "PIL.Image"])

def analyse(skript):
    return Analysis([P(skript)], pathex=[P("..", "src")], datas=daten, hiddenimports=versteckt,
                    excludes=["tkinter", "pytest"])

a_ui = analyse("start_kasse.py")
a_cli = analyse("start_cli.py")

exe_ui = EXE(PYZ(a_ui.pure), a_ui.scripts, [], exclude_binaries=True,
             name="Registrierkasse", icon=P("kasse.ico"), console=False, version=P("version.txt"))
exe_cli = EXE(PYZ(a_cli.pure), a_cli.scripts, [], exclude_binaries=True,
              name="kasse-cli", icon=P("kasse.ico"), console=True)

COLLECT(exe_ui, a_ui.binaries, a_ui.zipfiles, a_ui.datas,
        exe_cli, a_cli.binaries, a_cli.zipfiles, a_cli.datas,
        name="Registrierkasse")
