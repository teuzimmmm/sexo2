param(
    [Parameter(Mandatory=$true)][string]$Version,
    [Parameter(Mandatory=$true)][string]$BaseFolder,
    [string]$BuildSuffix = ""
)
$ErrorActionPreference = 'Stop'
if ($Version -notmatch '^v?[0-9]+\.[0-9]+\.[0-9]+$') { throw 'Use a version such as 1.5.1.' }
$releaseVersion = $Version.TrimStart('v')
if ($BuildSuffix -notmatch '^[-a-z0-9]*$') { throw 'Invalid build suffix.' }
$projectRoot = Split-Path -Parent $PSScriptRoot
$previousFolder = (Resolve-Path -LiteralPath $BaseFolder).Path
Push-Location $projectRoot
try {
    $keyFile = Join-Path $projectRoot 'release-secrets\signing.key'
    if (-not (Test-Path -LiteralPath $keyFile)) { throw 'Local signing key is missing. Do not generate a replacement for existing clients.' }
    $source = Get-Content -LiteralPath 'assets\update-source.json' -Raw | ConvertFrom-Json
    $env:GITHUB_REPOSITORY = $source.repository
    $env:SEXO2_SIGNING_KEY_HEX = [BitConverter]::ToString([IO.File]::ReadAllBytes($keyFile)).Replace("-", "").ToLower()
    python scripts/prepare_release.py --base $previousFolder --version $releaseVersion
    if ($LASTEXITCODE -ne 0) { throw 'Preparation failed.' }
    python scripts/run_tests.py -q
    if ($LASTEXITCODE -ne 0) { throw 'Tests failed.' }
    $appDist = "dist-sexo2-$releaseVersion$BuildSuffix"
    $helperDist = "dist-updater-$releaseVersion$BuildSuffix"
    python -m PyInstaller SEXO2.spec --distpath $appDist --workpath "build-sexo2-$releaseVersion" --noconfirm
    if ($LASTEXITCODE -ne 0) { throw 'Application build failed.' }
    python -m PyInstaller SEXO2-Updater.spec --distpath $helperDist --workpath "build-updater-$releaseVersion" --noconfirm
    if ($LASTEXITCODE -ne 0) { throw 'Updater build failed.' }
    python audit_frozen.py "$appDist/SEXO2"
    if ($LASTEXITCODE -ne 0) { throw 'Audit failed.' }
    $releaseFolder = "../SEXO2-$releaseVersion"
    python scripts/package_update_release.py --base $previousFolder --new "$appDist/SEXO2" --helper "$helperDist/SEXO2 Update.exe" --version $releaseVersion --output $releaseFolder
    if ($LASTEXITCODE -ne 0) { throw 'Packaging failed.' }
    # First-install file: the update packages only serve installations that already exist
    $iscc = @($env:SEXO2_ISCC, "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe", "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe", "$env:ProgramFiles\Inno Setup 6\ISCC.exe") | Where-Object { $_ -and (Test-Path -LiteralPath $_) } | Select-Object -First 1
    if ($iscc) {
        & $iscc "/DAppSourceDir=$((Resolve-Path "$appDist/SEXO2").Path)" "/O$((Resolve-Path $releaseFolder).Path)" "/FSEXO2-Instalador-$releaseVersion" installer-sexo2.iss
        if ($LASTEXITCODE -ne 0) { throw 'Installer build failed.' }
    } else {
        throw 'Inno Setup 6 not found: install it from https://jrsoftware.org/isdl.php (the release needs the first-install file).'
    }
    python scripts/build_patch.py --base $previousFolder --new "$appDist/SEXO2" --output "$releaseFolder/SEXO2-update.zip" --version $releaseVersion --key-file $keyFile
    if ($LASTEXITCODE -ne 0) { throw 'Signing failed.' }
    python scripts/build_compatibility.py --new "$appDist/SEXO2" --output $releaseFolder --version $releaseVersion --key-file $keyFile
    if ($LASTEXITCODE -ne 0) { throw 'Retroactive updates failed. Do not publish this release.' }
    Write-Output "Local signed release ready: $releaseFolder"
} finally {
    Remove-Item Env:SEXO2_SIGNING_KEY_HEX -ErrorAction SilentlyContinue
    Pop-Location
}
