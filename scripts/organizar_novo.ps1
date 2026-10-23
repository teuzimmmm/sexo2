<#
Organiza a pasta "novo" (a que guarda os projetos e builds antigos do SEXO2).

  Guarda em  novo\velho  o que a próxima release precisa e não existe no GitHub:
    projeto-2.0 (código, chave de assinatura, token de leitura), SEXO2, SEXO2-r2 e SEXO2-r3 (r1, r2 e r3).
  Joga o resto na Lixeira (inclusive dist-* e build-* de dentro da projeto-2.0: as baselines de versões
  publicadas voltam do GitHub com scripts\restore_baselines.py).

Por padrão só MOSTRA o que faria. Para valer:  -Executar  (e confirmar digitando SIM).

  powershell -ExecutionPolicy Bypass -File scripts\organizar_novo.ps1                      # mostra
  powershell -ExecutionPolicy Bypass -File scripts\organizar_novo.ps1 -Executar            # faz

Se o disco for de rede ou a Lixeira estiver pequena, o Windows apaga de vez. Nesse caso use
-MoverParaPasta: move tudo para novo\_para-apagar, que você apaga à mão depois de conferir.
#>
param(
    [string]$Novo = "Z:\mathe\onedrive\Desktop\gpt-etc\novo",
    [string]$Projeto = "projeto-2.0",
    [switch]$Executar,
    [switch]$MoverParaPasta
)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName Microsoft.VisualBasic

$Novo = (Resolve-Path -LiteralPath $Novo).Path.TrimEnd('\')
$velho = Join-Path $Novo 'velho'
$aparte = Join-Path $Novo '_para-apagar'
$guardar = @($Projeto, 'SEXO2', 'SEXO2-r2', 'SEXO2-r3')

# 0. O Windows não move uma pasta que está em uso: nem o terminal nem este script podem estar dentro de novo.
$aqui = (Get-Location).Path
$esteScript = $PSCommandPath
if ($aqui.StartsWith($Novo, [StringComparison]::OrdinalIgnoreCase) -or ($esteScript -and $esteScript.StartsWith($Novo, [StringComparison]::OrdinalIgnoreCase))) {
    Write-Output 'Saia da pasta novo antes de rodar. Copie este script para a pasta de cima e rode de lá:'
    Write-Output "  cd `"$(Split-Path -Parent $Novo)`""
    Write-Output '  powershell -ExecutionPolicy Bypass -File .\organizar_novo.ps1 -Executar'
    exit 1
}

# 1. O que tem de existir para a próxima release. Se faltar algo, nada é tocado.
$exigidos = @(
    "$Projeto\release-secrets\signing.key",
    "$Projeto\assets\update-access.json",
    "$Projeto\scripts\release_local.ps1",
    "SEXO2\SEXO2\SEXO2.exe",
    "SEXO2-r2\SEXO2\SEXO2.exe",
    "SEXO2-r3\SEXO2\SEXO2.exe"
)
$faltam = @($exigidos | Where-Object { -not (Test-Path -LiteralPath (Join-Path $Novo $_)) })
if ($faltam.Count -gt 0) {
    Write-Output 'FALTA (nada foi alterado):'
    $faltam | ForEach-Object { Write-Output "  $_" }
    exit 1
}

# 2. O que vai para o lixo.
$pesados = @()
$pastaProjeto = Join-Path $Novo $Projeto
if (Test-Path -LiteralPath $pastaProjeto) {
    $pesados = @(Get-ChildItem -LiteralPath $pastaProjeto -Directory -Force | Where-Object { $_.Name -match '^(dist|build)' })
}
$resto = @(Get-ChildItem -LiteralPath $Novo -Force | Where-Object { $_.Name -ne 'velho' -and $_.Name -ne '_para-apagar' -and ($guardar -notcontains $_.Name) })

function Tamanho($item) {
    if ($item.PSIsContainer) {
        $soma = (Get-ChildItem -LiteralPath $item.FullName -Recurse -File -Force -ErrorAction SilentlyContinue | Measure-Object Length -Sum).Sum
    } else { $soma = $item.Length }
    if (-not $soma) { $soma = 0 }
    return [math]::Round($soma / 1GB, 2)
}

Write-Output ''
Write-Output "Pasta: $Novo"
Write-Output ''
Write-Output "FICA (movido para $velho):"
$guardar | ForEach-Object { Write-Output "  $_" }
Write-Output ''
Write-Output "VAI PARA O LIXO de dentro de ${Projeto}:"
if ($pesados.Count -eq 0) { Write-Output '  (nada)' }
$pesados | ForEach-Object { Write-Output ("  {0}  ({1} GB)" -f $_.Name, (Tamanho $_)) }
Write-Output ''
Write-Output 'VAI PARA O LIXO de dentro de novo:'
if ($resto.Count -eq 0) { Write-Output '  (nada)' }
$resto | ForEach-Object { Write-Output ("  {0}  ({1} GB)" -f $_.Name, (Tamanho $_)) }
Write-Output ''

if (-not $Executar) {
    Write-Output 'Isto foi só uma simulação. Confira a lista (tem algo seu que não é do SEXO2?) e rode de novo com -Executar.'
    exit 0
}

# 3. A Lixeira não funciona em disco de rede: nesse caso o Windows apaga de vez. Recuse.
if (-not $MoverParaPasta) {
    $letra = $Novo.Substring(0, 2)
    $disco = Get-CimInstance Win32_LogicalDisk -Filter "DeviceID='$letra'" -ErrorAction SilentlyContinue
    if (-not $disco -or $disco.DriveType -ne 3) {
        Write-Output "O disco $letra não é um disco local comum: a Lixeira pode apagar de vez."
        Write-Output 'Rode com -Executar -MoverParaPasta (move para novo\_para-apagar, que você apaga à mão).'
        exit 1
    }
}
$resposta = Read-Host 'Digite SIM para continuar'
if ($resposta -ne 'SIM') { Write-Output 'Cancelado. Nada foi alterado.'; exit 0 }

function Descartar([string]$caminho) {
    if ($MoverParaPasta) {
        if (-not (Test-Path -LiteralPath $aparte)) { New-Item -ItemType Directory -Path $aparte | Out-Null }
        $destino = Join-Path $aparte (Split-Path -Leaf $caminho)
        if (Test-Path -LiteralPath $destino) { $destino = $destino + '-' + (Get-Date -Format 'HHmmss') }
        Move-Item -LiteralPath $caminho -Destination $destino
        return
    }
    if (Test-Path -LiteralPath $caminho -PathType Container) {
        [Microsoft.VisualBasic.FileIO.FileSystem]::DeleteDirectory($caminho, 'AllDialogs', 'SendToRecycleBin')
    } else {
        [Microsoft.VisualBasic.FileIO.FileSystem]::DeleteFile($caminho, 'AllDialogs', 'SendToRecycleBin')
    }
}

# 4. Primeiro o que está dentro do projeto, depois move o que fica, por último o resto.
foreach ($item in $pesados) { Write-Output "Lixo: $Projeto\$($item.Name)"; Descartar $item.FullName }
if (-not (Test-Path -LiteralPath $velho)) { New-Item -ItemType Directory -Path $velho | Out-Null }
foreach ($nome in $guardar) {
    $origem = Join-Path $Novo $nome
    $destino = Join-Path $velho $nome
    if (Test-Path -LiteralPath $destino) { Write-Output "Já existe em velho, não movi: $nome"; continue }
    Write-Output "Guardado: velho\$nome"
    Move-Item -LiteralPath $origem -Destination $destino
}
foreach ($item in $resto) { Write-Output "Lixo: $($item.Name)"; Descartar $item.FullName }

Write-Output ''
Write-Output 'Pronto. Para a próxima release:'
Write-Output "  cd `"$velho\$Projeto`""
Write-Output '  python scripts\restore_baselines.py     # baixa as baselines publicadas (1.5.0 a 1.6.4, 1.9.0, 2.0.0)'
Write-Output '  e depois o release_local.ps1 como no guia. A chave signing.key continua tendo de ter cópia fora do PC.'
