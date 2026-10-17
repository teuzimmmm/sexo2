param(
    [Parameter(Mandatory=$true)][string]$Installer,
    [Parameter(Mandatory=$true)][string]$ExpectedCommit,
    [Parameter(Mandatory=$true)][string]$ReportPath
)
$ErrorActionPreference = 'Stop'
# Intended only for a fresh, disposable Windows build runner. Never launches LoL,
# SEXO2 or Pengu and never removes an existing program/data folder.
$target = Join-Path ([Environment]::GetFolderPath('LocalApplicationData')) 'Programs\SEXO2-2.0-Teste'
$newKey = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\{381FCB77-CA20-4E43-A3C6-755365B314A9}_is1'
$oldKey = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\{B876AA51-DB38-448E-BD13-716F1C9DE750}_is1'
if ((Test-Path -LiteralPath $target) -or (Test-Path -LiteralPath $newKey) -or (Test-Path -LiteralPath $oldKey)) {
    throw 'Smoke test requires a fresh disposable account; existing installation found.'
}
if ($ExpectedCommit -notmatch '^[0-9a-f]{40}$') { throw 'Invalid expected commit.' }
$installerPath = (Resolve-Path -LiteralPath $Installer).Path
$buildReport = Get-Content -LiteralPath ([IO.Path]::ChangeExtension($installerPath, '.json')) -Raw | ConvertFrom-Json
if ($buildReport.sourceCommit -ne $ExpectedCommit -or $buildReport.overlayRendererSha256 -notmatch '^[0-9a-f]{64}$') { throw 'Renderer build receipt missing or invalid.' }
$marker = 'synthetic-installer-smoke-' + [Guid]::NewGuid().ToString('N')
$sentinels = @()
try {
    New-Item -Path $oldKey -Force | Out-Null
    New-ItemProperty -LiteralPath $oldKey -Name 'DisplayName' -Value $marker -PropertyType String | Out-Null
    foreach ($folder in @(
        (Join-Path ([Environment]::GetFolderPath('LocalApplicationData')) 'Rose'),
        (Join-Path ([Environment]::GetFolderPath('ApplicationData')) 'Rose'),
        (Join-Path ([Environment]::GetFolderPath('ApplicationData')) 'Rose Teste 3')
    )) {
        New-Item -ItemType Directory -Path $folder -Force | Out-Null
        $file = Join-Path $folder $marker
        Set-Content -LiteralPath $file -Value $marker -NoNewline
        $sentinels += $file
    }
    for ($round = 0; $round -lt 2; $round++) {
        $process = Start-Process -FilePath $installerPath -ArgumentList @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART','/SP-') -Wait -PassThru
        if ($process.ExitCode -ne 0) { throw 'Installer did not succeed.' }
        if (-not (Test-Path -LiteralPath (Join-Path $target 'SEXO2.exe'))) { throw 'Installed application missing.' }
        $identity = Get-Content -LiteralPath (Join-Path $target 'sexo2-test-build.json') -Raw | ConvertFrom-Json
        if ($identity.channel -ne 'test' -or $identity.sourceCommit -ne $ExpectedCommit) { throw 'Installed source identity mismatch.' }
        $version = (Get-Item -LiteralPath (Join-Path $target 'SEXO2.exe')).VersionInfo.ProductVersion
        if ($version -ne $identity.version) { throw 'Executable version mismatch.' }
        $plugin = 'Pengu Loader\plugins\SEXO2-Builds\index.js'
        $packaged = Join-Path $target ('_internal\' + $plugin)
        $source = Join-Path (Split-Path -Parent $PSScriptRoot) $plugin
        if ((Get-FileHash -LiteralPath $packaged).Hash -ne (Get-FileHash -LiteralPath $source).Hash) { throw 'Installed plugin differs from current source.' }
        foreach ($excluded in @('_internal\assets\update-access.json','_internal\Pengu Loader\config','_internal\Pengu Loader\datastore')) {
            if (Test-Path -LiteralPath (Join-Path $target $excluded)) { throw 'Private state leaked into installed package.' }
        }
        $renderer = Join-Path $target '_internal\sexo2\overlay\bin\sexo2-overlay-renderer.dll'
        if ((Get-FileHash -LiteralPath $renderer).Hash.ToLowerInvariant() -ne $buildReport.overlayRendererSha256) { throw 'Installed renderer digest mismatch.' }
        $record = Get-ItemProperty -LiteralPath $newKey
        if ($record.DisplayName -notlike '*Teste*') { throw 'Test uninstall registration missing.' }
    }
    # Load and exercise the actual installed DLL in this isolated Python process.
    # No SEXO2, League or Pengu executable is started.
    $probe = @'
import sys
from pathlib import Path
from sexo2.overlay.runtime import Frame
from sexo2.overlay.win32 import NativeOverlay
from sexo2.overlay.composition import Composition
sys._MEIPASS = str(Path(sys.argv[1]) / '_internal')
w = NativeOverlay(lambda: Frame())
w._api()
hwnd = w.u.CreateWindowExW(0, 'STATIC', 'synthetic installed renderer', 0x80000000,
    0, 0, 420, 100, None, None, w.k.GetModuleHandleW(None), None)
if not hwnd:
    raise RuntimeError('Synthetic HWND creation failed.')
try:
    renderer = Composition(hwnd)
    try:
        renderer.draw(420, 100, 'SEXO2', 'Installed renderer test', 'Synthetic only')
    finally:
        renderer.close()
finally:
    w.u.DestroyWindow(hwnd)
print('PASS: installed composition DLL loaded and rendered on its own synthetic HWND.')
'@
    python -c $probe $target
    if ($LASTEXITCODE -ne 0) { throw 'Installed composition DLL did not load/render.' }
    $uninstaller = Join-Path $target 'unins000.exe'
    $process = Start-Process -FilePath $uninstaller -ArgumentList @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART') -Wait -PassThru
    if ($process.ExitCode -ne 0) { throw 'Uninstaller did not succeed.' }
    for ($attempt = 0; $attempt -lt 100 -and (Test-Path -LiteralPath $target); $attempt++) {
        Start-Sleep -Milliseconds 100
    }
    if ((Test-Path -LiteralPath $target) -or (Test-Path -LiteralPath $newKey)) { throw 'Test program or uninstall registration remains.' }
    if ((Get-ItemProperty -LiteralPath $oldKey).DisplayName -ne $marker) { throw 'Legacy registration changed.' }
    foreach ($file in $sentinels) {
        if ((Get-Content -LiteralPath $file -Raw) -ne $marker) { throw 'Legacy data sentinel changed.' }
    }
    @{ installed=$true; reinstalled=$true; uninstalled=$true; legacySentinelsPreserved=$true; installedRendererLoaded=$true;
       sourceCommit=$ExpectedCommit; nativeLeagueValidation=$false } |
        ConvertTo-Json | Set-Content -LiteralPath $ReportPath -Encoding utf8
    Write-Output 'PASS: Windows install/reinstall/uninstall; current plugin/version and legacy preservation verified. No application/game was launched.'
} finally {
    foreach ($file in $sentinels) {
        if ((Test-Path -LiteralPath $file) -and (Get-Content -LiteralPath $file -Raw) -eq $marker) {
            Remove-Item -LiteralPath $file
        }
    }
    if ((Test-Path -LiteralPath $oldKey) -and (Get-ItemProperty -LiteralPath $oldKey).DisplayName -eq $marker) {
        Remove-Item -LiteralPath $oldKey -Recurse
    }
}
