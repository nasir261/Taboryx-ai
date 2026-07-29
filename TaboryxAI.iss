[Setup]
AppName=Taboryx AI
AppVersion=0.1.0
AppPublisher=Taboryx Development Team
AppPublisherURL=https://example.com
AppSupportURL=https://example.com
AppUpdatesURL=https://example.com
DefaultDirName={autopf}\Taboryx AI
DefaultGroupName=Taboryx AI
OutputBaseFilename=TaboryxAI-Setup
Compression=lzma2
SolidCompression=yes
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
PrivilegesRequired=admin
OutputDir=.

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
Source: ".\dist\TaboryxAI.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Taboryx AI"; Filename: "{app}\TaboryxAI.exe"
Name: "{commondesktop}\Taboryx AI"; Filename: "{app}\TaboryxAI.exe"

[Run]
Filename: "{app}\TaboryxAI.exe"; Description: "Launch Taboryx AI"; Flags: nowait postinstall skipifsilent
