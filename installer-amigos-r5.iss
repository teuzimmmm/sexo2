#define MyAppName "Rose dos Amigos"
#define MyAppVersion "1.4.7.5"
#define MyAppExeName "Rose.exe"
[Setup]
AppId={{B876AA51-DB38-448E-BD13-716F1C9DE750}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName=Rose dos Amigos r5 (base 1.4.7)
AppPublisher=Rose - versao personalizada
DefaultDirName={localappdata}\Rose Teste 0.3
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=..\rose-amigos-r5
OutputBaseFilename=Rose Amigos r5 - Instalador
SetupIconFile=assets\icon.ico
Compression=lzma2/fast
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\Rose.exe
AppMutex=Local\RoseSingleInstance
VersionInfoVersion=1.4.7.5
[Languages]
Name: "brazilian"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"
[Tasks]
Name: "desktopicon"; Description: "Criar atalhos na area de trabalho"; GroupDescription: "Atalhos:"
[Files]
Source: "..\rose-amigos-r5\Rose\*"; DestDir: "{app}"; Excludes: "hashes.game.txt"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\rose-amigos-r5\Rose\_internal\injection\tools\hashes.game.txt"; DestDir: "{app}\_internal\injection\tools"; Flags: onlyifdoesntexist
[Icons]
Name: "{group}\Rose dos Amigos"; Filename: "{app}\Rose.exe"
Name: "{group}\Rose Sala - hospedar ou entrar"; Filename: "{app}\Sala\Rose Sala.exe"
Name: "{autodesktop}\Rose dos Amigos"; Filename: "{app}\Rose.exe"; Tasks: desktopicon
Name: "{autodesktop}\Rose Sala"; Filename: "{app}\Sala\Rose Sala.exe"; Tasks: desktopicon
[Run]
Filename: "{app}\Rose.exe"; Description: "Abrir Rose dos Amigos"; Flags: nowait postinstall skipifsilent shellexec unchecked; Verb: runas
; User skins, Swiftplay choices, config and logs in LocalAppData\Rose are preserved.
[UninstallRun]
Filename: "{app}\_internal\Pengu Loader\Pengu Loader.exe"; Parameters: "--uninstall --silent"; Flags: runhidden waituntilterminated skipifdoesntexist; RunOnceId: "PenguLoader"
