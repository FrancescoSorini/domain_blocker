[Setup]
AppId={{9E6F2B3F-8B4E-4A1C-9A61-6B2E9A8A2C31}
AppName=DNSDomainBlocker
AppVersion=1.0.0
AppPublisher=DNSDomainBlocker
DefaultDirName={pf}\DNSDomainBlocker
DefaultGroupName=DNSDomainBlocker
OutputDir=.\installer\output
OutputBaseFilename=DNSDomainBlocker-Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
SetupIconFile=..\assets\app.ico
PrivilegesRequired=admin

[Files]
Source: "..\dist\DNSDomainBlocker\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\DNSDomainBlocker"; Filename: "{app}\DNSDomainBlocker.exe"; IconFilename: "{app}\DNSDomainBlocker.exe"
Name: "{commondesktop}\DNSDomainBlocker"; Filename: "{app}\DNSDomainBlocker.exe"; IconFilename: "{app}\DNSDomainBlocker.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Crea un'icona sul Desktop"; GroupDescription: "Icone:"; Flags: unchecked

[Run]
Filename: "{app}\DNSDomainBlocker.exe"; Description: "Avvia DNSDomainBlocker"; Flags: nowait postinstall skipifsilent
