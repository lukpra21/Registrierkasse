; Inno-Setup-Skript für die Registrierkasse
; Aufruf: iscc /DVersion=0.2.0 packaging\registrierkasse.iss
; Erwartet die PyInstaller-Ausgabe in dist\Registrierkasse

#ifndef Version
  #define Version "0.0.0"
#endif

[Setup]
AppId={{6E2F3C1A-8B4D-4E8F-9C2A-5D7B1F0A3E91}
AppName=Registrierkasse
AppVersion={#Version}
AppVerName=Registrierkasse {#Version}
AppPublisher=Registrierkasse
DefaultDirName={autopf}\Registrierkasse
DefaultGroupName=Registrierkasse
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
OutputDir=..\dist
OutputBaseFilename=Registrierkasse-Setup-{#Version}
SetupIconFile=kasse.ico
UninstallDisplayIcon={app}\Registrierkasse.exe
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
RestartApplications=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "de"; MessagesFile: "compiler:Languages\German.isl"

[Tasks]
Name: "desktop"; Description: "Symbol auf dem Desktop anlegen"; GroupDescription: "Zusätzlich:"
Name: "autostart"; Description: "Kasse beim Anmelden automatisch starten"; GroupDescription: "Zusätzlich:"; Flags: unchecked
Name: "sicherung"; Description: "Tägliche Datensicherung um 21:00 Uhr einrichten"; GroupDescription: "Zusätzlich:"

[Files]
Source: "..\dist\Registrierkasse\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Registrierkasse"; Filename: "{app}\Registrierkasse.exe"
Name: "{group}\Registrierkasse deinstallieren"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Registrierkasse"; Filename: "{app}\Registrierkasse.exe"; Tasks: desktop
Name: "{userstartup}\Registrierkasse"; Filename: "{app}\Registrierkasse.exe"; Tasks: autostart

[Run]
Filename: "{app}\kasse-cli.exe"; Parameters: "sicherung-planen --uhrzeit 21:00"; Flags: runhidden; Tasks: sicherung
Filename: "{app}\Registrierkasse.exe"; Description: "Registrierkasse jetzt starten"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "schtasks.exe"; Parameters: "/Delete /F /TN ""Registrierkasse Sicherung"""; Flags: runhidden; RunOnceId: "SicherungEntfernen"

; Die Kassendaten in %APPDATA%\Registrierkasse bleiben bei der Deinstallation erhalten
; (RKSV: Aufbewahrungspflicht 7 Jahre).
