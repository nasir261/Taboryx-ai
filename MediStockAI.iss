[Setup]
AppName=MediStock AI
AppVersion=0.1.0
AppPublisher=MediStock Development Team
AppPublisherURL=https://example.com
AppSupportURL=https://example.com
AppUpdatesURL=https://example.com
DefaultDirName={autopf}\MediStock AI
DefaultGroupName=MediStock AI
OutputBaseFilename=MediStockAI-Setup
Compression=lzma2
SolidCompression=yes
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
PrivilegesRequired=admin
OutputDir=.

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
Source: ".\dist\MediStockAI.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\MediStock AI"; Filename: "{app}\MediStockAI.exe"
Name: "{commondesktop}\MediStock AI"; Filename: "{app}\MediStockAI.exe"

[Run]
Filename: "{app}\MediStockAI.exe"; Description: "Launch MediStock AI"; Flags: nowait postinstall skipifsilent
