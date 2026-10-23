#define MyAppName "SEXO2"
#ifndef AppSourceDir
#define AppSourceDir "..\SEXO2-r3\SEXO2"
#endif
#define MyAppVersion "1.9.2.0"
[Setup]
AppId={{B876AA51-DB38-448E-BD13-716F1C9DE750}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName=SEXO2
AppPublisher=Projeto personalizado baseado em Rose
DefaultDirName={localappdata}\Programs\SEXO2
DefaultGroupName=SEXO2
UsePreviousGroup=no
DisableProgramGroupPage=yes
OutputDir=..\SEXO2-r3
OutputBaseFilename=SEXO2 - Instalador
SetupIconFile=assets\sexo2.ico
Compression=lzma2/fast
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\SEXO2.exe
AppMutex=Local\SEXO2SingleInstance,Local\RoseSingleInstance
VersionInfoVersion={#MyAppVersion}
[Languages]
Name: "brazilian"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"
[Tasks]
Name: "desktopicon"; Description: "Criar atalho na area de trabalho"; GroupDescription: "Atalhos:"
[Files]
Source: "{#AppSourceDir}\*"; DestDir: "{app}"; Excludes: "hashes.game.txt"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#AppSourceDir}\_internal\injection\tools\hashes.game.txt"; DestDir: "{app}\_internal\injection\tools"; Flags: onlyifdoesntexist
[Icons]
Name: "{group}\SEXO2"; Filename: "{app}\SEXO2.exe"; IconFilename: "{app}\_internal\assets\sexo2-v2.ico"
Name: "{autodesktop}\SEXO2"; Filename: "{app}\SEXO2.exe"; IconFilename: "{app}\_internal\assets\sexo2-v2.ico"; Tasks: desktopicon
[InstallDelete]
Type: files; Name: "{app}\Rose.exe"
Type: files; Name: "{autodesktop}\Rose dos Amigos.lnk"
Type: files; Name: "{userprograms}\Rose dos Amigos\Rose dos Amigos.lnk"
Type: files; Name: "{group}\Rose Sala - hospedar ou entrar.lnk"
Type: files; Name: "{autodesktop}\Rose Sala.lnk"
Type: filesandordirs; Name: "{app}\_internal\Pengu Loader\plugins\ROSE-*"
[Run]
Filename: "{app}\SEXO2.exe"; Description: "Abrir SEXO2"; Flags: nowait postinstall skipifsilent shellexec unchecked; Verb: runas
[UninstallRun]
Filename: "{app}\_internal\Pengu Loader\Pengu Loader.exe"; Parameters: "--uninstall --silent"; Flags: runhidden waituntilterminated skipifdoesntexist; RunOnceId: "PenguLoader"
[Code]
var
  BackupDir: string;
  Finished: Boolean;
  BackupComplete: Boolean;

function CopyTree(SourceDir, TargetDir: string): Boolean;
var
  FindRec: TFindRec;
  SourceFile, TargetFile: string;
begin
  Result := ForceDirectories(TargetDir);
  if not Result then exit;
  if FindFirst(AddBackslash(SourceDir) + '*', FindRec) then begin
    try
      repeat
        if (FindRec.Name <> '.') and (FindRec.Name <> '..') then begin
          { Never traverse junctions or symbolic links. }
          if (FindRec.Attributes and $400) <> 0 then begin Result := False; exit; end;
          SourceFile := AddBackslash(SourceDir) + FindRec.Name;
          TargetFile := AddBackslash(TargetDir) + FindRec.Name;
          if (FindRec.Attributes and FILE_ATTRIBUTE_DIRECTORY) <> 0 then
            Result := CopyTree(SourceFile, TargetFile)
          else
            Result := FileCopy(SourceFile, TargetFile, False);
          if not Result then exit;
        end;
      until not FindNext(FindRec);
    finally
      FindClose(FindRec);
    end;
  end;
end;

function FolderSize(Path: string): Int64;
var
  FindRec: TFindRec;
begin
  Result := 0;
  if FindFirst(AddBackslash(Path) + '*', FindRec) then begin
    try
      repeat
        if (FindRec.Name <> '.') and (FindRec.Name <> '..') then begin
          if (FindRec.Attributes and $400) <> 0 then
            RaiseException('A instalacao contem um link ou juncao. Escolha uma pasta local normal.');
          if (FindRec.Attributes and FILE_ATTRIBUTE_DIRECTORY) <> 0 then
            Result := Result + FolderSize(AddBackslash(Path) + FindRec.Name)
          else
            Result := Result + Int64(FindRec.SizeHigh) * 4294967296 + FindRec.SizeLow;
        end;
      until not FindNext(FindRec);
    finally
      FindClose(FindRec);
    end;
  end;
end;

function PrepareToInstall(var NeedsRestart: Boolean): string;
var
  AppDir: string;
  FreeMB, TotalMB: Cardinal;
  NeededMB: Int64;
  Locator, Service, Processes: Variant;
begin
  Result := '';
  AppDir := RemoveBackslashUnlessRoot(ExpandConstant('{app}'));
  if (AppDir = ExtractFileDrive(AppDir) + '\') or
     (CompareText(AppDir, ExpandConstant('{localappdata}\Rose')) = 0) or
     (CompareText(AppDir, ExpandConstant('{localappdata}\SEXO2')) = 0) then begin
    Result := 'Escolha uma pasta para o programa, separada dos dados pessoais.'; exit;
  end;
  try
    Locator := CreateOleObject('WbemScripting.SWbemLocator');
    Service := Locator.ConnectServer('', 'root\CIMV2');
    Processes := Service.ExecQuery('SELECT Name FROM Win32_Process WHERE Name="SEXO2.exe" OR Name="Rose.exe" OR Name="Rose Sala.exe" OR Name="LeagueClient.exe" OR Name="League of Legends.exe"');
    if Processes.Count > 0 then begin
      Result := 'Feche o SEXO2 e o cliente LoL antes de instalar.'; exit;
    end;
    NeededMB := 400;
    if (FileExists(AddBackslash(AppDir) + 'Rose.exe') or FileExists(AddBackslash(AppDir) + 'SEXO2.exe')) then
      NeededMB := NeededMB + (FolderSize(AppDir) div 1048576) + 1;
    if not GetSpaceOnDisk(ExtractFileDrive(AppDir), True, FreeMB, TotalMB) then
      RaiseException('Nao foi possivel verificar o espaco livre.');
    if FreeMB < NeededMB then begin
      Result := 'Falta espaco para instalar e preservar a versao anterior.'; exit;
    end;
    if (FileExists(AddBackslash(AppDir) + 'Rose.exe') or FileExists(AddBackslash(AppDir) + 'SEXO2.exe')) and not BackupComplete then begin
      BackupDir := AppDir + '.backup-' + GetDateTimeString('yyyymmdd-hhnnss', '-', ':');
      if DirExists(BackupDir) then RaiseException('A pasta de backup ja existe. Tente novamente.');
      if not CopyTree(AppDir, BackupDir) then begin
        Result := 'Nao foi possivel preservar a versao anterior. A instalacao nao foi iniciada.'; exit;
      end;
      BackupComplete := True;
    end;
  except
    Result := GetExceptionMessage;
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then begin
    Finished := True;
    if BackupComplete then
      SaveStringToFile(ExpandConstant('{app}\VERSAO-ANTERIOR.txt'),
        'A versao anterior foi preservada em:' + #13#10 + BackupDir + #13#10 +
        'Suas skins e preferencias continuam em LocalAppData\SEXO2.' + #13#10, False);
  end;
end;

procedure DeinitializeSetup();
begin
  if BackupComplete and not Finished then begin
    if not CopyTree(BackupDir, ExpandConstant('{app}')) then
      MsgBox('A instalacao foi interrompida. A versao anterior esta preservada em: ' + BackupDir, mbError, MB_OK)
    else if not FileExists(BackupDir + '\_internal\Pengu Loader\plugins\SEXO2-Hub\index.js') then
      DeleteFile(ExpandConstant('{app}\_internal\Pengu Loader\plugins\SEXO2-Hub\index.js'));
  end;
end;
