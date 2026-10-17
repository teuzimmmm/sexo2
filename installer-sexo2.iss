; Functional test edition. The final legacy migration is deliberately separate.
#ifndef SourceDir
  #error Define SourceDir with the audited frozen SEXO2 directory.
#endif
#ifndef OutputDir
  #error Define OutputDir for the test installer.
#endif
#ifndef BuildVersion
  #define BuildVersion "2.0.0.7"
#endif
#ifndef OutputName
  #define OutputName "SEXO2-2.0.0.7-Teste"
#endif

[Setup]
AppId={{381FCB77-CA20-4E43-A3C6-755365B314A9}
AppName=SEXO2 2.0 Teste
AppVersion={#BuildVersion}
AppVerName=SEXO2 {#BuildVersion} (teste)
AppPublisher=Projeto SEXO2, baseado em Rose
DefaultDirName={localappdata}\Programs\SEXO2-2.0-Teste
DefaultGroupName=SEXO2 2.0 Teste
UsePreviousAppDir=no
UsePreviousGroup=no
DisableDirPage=yes
DisableProgramGroupPage=yes
DisableWelcomePage=no
OutputDir={#OutputDir}
OutputBaseFilename={#OutputName}
SetupIconFile=assets\sexo2.ico
Compression=lzma2/fast
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\SEXO2.exe
; Keep the existing runtime mutex: two editions must not control LoL together.
AppMutex=Local\RoseSingleInstance
SetupMutex=Local\SEXO2TestSetup
CloseApplications=no
RestartApplications=no
VersionInfoVersion={#BuildVersion}

[Languages]
Name: "brazilian"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Messages]
brazilian.WelcomeLabel2=Este pacote instala o SEXO2 2.0 para teste, sem remover versões anteriores.%n%nO aplicativo usa seus dados e preferências atuais. A migração e a limpeza das versões antigas serão feitas no instalador definitivo.%n%nFeche o SEXO2/Rose e o cliente do LoL antes de instalar. Abra-os novamente após concluir. As atualizações estáveis ficam desativadas nesta edição.

[Tasks]
Name: "desktopicon"; Description: "Criar atalho na área de trabalho"; GroupDescription: "Atalhos:"; Flags: unchecked

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Excludes: "sexo2-release.json,SEXO2 Update.exe,*\update-access.json,*\config.ini,*\datastore,*.log,*.key,*.pfx"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\SEXO2 2.0 Teste"; Filename: "{app}\SEXO2.exe"; WorkingDir: "{app}"
Name: "{autodesktop}\SEXO2 2.0 Teste"; Filename: "{app}\SEXO2.exe"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\SEXO2.exe"; Description: "Abrir SEXO2 2.0 Teste"; Flags: nowait postinstall skipifsilent unchecked shellexec; Verb: runas

[Code]
function ReadAttributes(FileName: string): LongWord;
  external 'GetFileAttributesW@kernel32.dll stdcall';

function PrepareToInstall(var NeedsRestart: Boolean): string;
var
  Target, Expected, Parent, NextParent: string;
  Contents: AnsiString;
  Found: TFindRec;
  Attributes: LongWord;
begin
  Result := '';
  Target := RemoveBackslashUnlessRoot(ExpandFileName(ExpandConstant('{app}')));
  Expected := RemoveBackslashUnlessRoot(ExpandFileName(ExpandConstant('{localappdata}\Programs\SEXO2-2.0-Teste')));
  if CompareText(Target, Expected) <> 0 then begin
    Result := 'Esta edição de teste deve usar sua pasta própria. Não escolha uma instalação antiga.';
    exit;
  end;
  Parent := Target;
  while Length(Parent) > 3 do begin
    if DirExists(Parent) then begin
      Attributes := ReadAttributes(Parent);
      if (Attributes = $FFFFFFFF) or ((Attributes and $400) <> 0) then begin
        Result := 'Não foi possível validar a pasta de teste. Links e junctions não são aceitos.';
        exit;
      end;
    end;
    NextParent := ExtractFileDir(Parent);
    if CompareText(NextParent, Parent) = 0 then break;
    Parent := NextParent;
  end;
  if DirExists(Target) then begin
    if FindFirst(AddBackslash(Target) + '*', Found) then begin
      try
        repeat
          if (Found.Name <> '.') and (Found.Name <> '..') then begin
            if not LoadStringFromFile(AddBackslash(Target) + 'sexo2-test-build.json', Contents) then begin
              Result := 'A pasta de destino já contém arquivos de outra origem. Use uma pasta de teste livre.';
              exit;
            end;
            if (Pos('"app": "SEXO2"', Contents) = 0) or (Pos('"channel": "test"', Contents) = 0) then begin
              Result := 'A identidade da pasta de teste é inválida. Preserve os arquivos e confira a instalação.';
              exit;
            end;
            break;
          end;
        until not FindNext(Found);
      finally
        FindClose(Found);
      end;
    end;
  end;
end;
