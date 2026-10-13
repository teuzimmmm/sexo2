param(
    [Parameter(Mandatory=$true)][string]$Version,
    [Parameter(Mandatory=$true)][string]$BaseFolder
)
$ErrorActionPreference = 'Stop'
if ($Version -notmatch '^v?[0-9]+\.[0-9]+\.[0-9]+$') { throw 'Use a version such as 1.5.1.' }
$releaseVersion = $Version.TrimStart('v')
$projectRoot = Split-Path -Parent $PSScriptRoot
$previousFolder = (Resolve-Path -LiteralPath $BaseFolder).Path
Push-Location $projectRoot
try {
    $keyFile = Join-Path $projectRoot 'release-secrets\signing.key'
    if (-not (Test-Path -LiteralPath $keyFile)) { throw 'Local signing key is missing. Do not generate a replacement for existing clients.' }
    $source = Get-Content -LiteralPath 'assets\update-source.json' -Raw | ConvertFrom-Json
    $env:GITHUB_REPOSITORY = $source.repository
    $env:SEXO2_SIGNING_KEY_HEX = [Convert]::ToHexString([IO.File]::ReadAllBytes($keyFile))
    python scripts/prepare_release.py --base $previousFolder --version $releaseVersion
    if ($LASTEXITCODE -ne 0) { throw 'Preparation failed.' }
    python -m unittest discover -s tests -q
    if ($LASTEXITCODE -ne 0) { throw 'Tests failed.' }
    $appDist = "dist-sexo2-$releaseVersion"
    $helperDist = "dist-updater-$releaseVersion"
    python -m PyInstaller SEXO2.spec --distpath $appDist --workpath "build-sexo2-$releaseVersion" --noconfirm
    if ($LASTEXITCODE -ne 0) { throw 'Application build failed.' }
    python -m PyInstaller SEXO2-Updater.spec --distpath $helperDist --workpath "build-updater-$releaseVersion" --noconfirm
    if ($LASTEXITCODE -ne 0) { throw 'Updater build failed.' }
    python audit_frozen.py "$appDist/SEXO2"
    if ($LASTEXITCODE -ne 0) { throw 'Audit failed.' }
    $releaseFolder = "../SEXO2-$releaseVersion"
    python scripts/package_update_release.py --base $previousFolder --new "$appDist/SEXO2" --helper "$helperDist/SEXO2 Update.exe" --version $releaseVersion --output $releaseFolder
    if ($LASTEXITCODE -ne 0) { throw 'Packaging failed.' }
    python scripts/build_patch.py --base $previousFolder --new "$appDist/SEXO2" --output "$releaseFolder/SEXO2-update.zip" --version $releaseVersion --key-file $keyFile
    if ($LASTEXITCODE -ne 0) { throw 'Signing failed.' }
    Write-Output "Local signed release ready: $releaseFolder"
} finally {
    Remove-Item Env:SEXO2_SIGNING_KEY_HEX -ErrorAction SilentlyContinue
    Pop-Location
}
