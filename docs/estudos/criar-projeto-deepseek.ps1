<#
Cria a estrutura do guia docs/estudos/GUIA-DEEPSEEK-OVERLAY.md em Documentos\projeto:
pastas, arquivos de configuracao e briefings. NAO apaga nem sobrescreve nada que ja exista.

Uso (PowerShell):
  .\criar-projeto-deepseek.ps1              # so pastas e arquivos
  .\criar-projeto-deepseek.ps1 -Clonar      # tambem clona o repositorio, cria ds/overlay e as 3 worktrees
#>
param([switch]$Clonar)

$ErrorActionPreference = 'Stop'
$root = Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'projeto'
$utf8 = New-Object System.Text.UTF8Encoding($false)

foreach ($d in 'agentes','config','briefing','capturas','medicoes') {
    New-Item -ItemType Directory -Force (Join-Path $root $d) | Out-Null
}

$arquivos = @{}
$arquivos['config\opencode.json'] = @'
{
  "$schema": "https://opencode.ai/config.json",
  "model": "SEU_ID_DEEPSEEK"
}
'@
$arquivos['config\coordenador.txt'] = @'
Você é o coordenador DeepSeek do projeto SEXO2 (app de LoL; Python + plugins Pengu).
Antes de tudo, leia CLAUDE.md, docs/estudos/GUIA-DEEPSEEK-OVERLAY.md e docs/estudos/OVERLAYS.md.

Sua missão: resolver os overlays de aprimoramentos (Arena e ARAM Mayhem) e de ouro, nas metas do guia.
Passos: use list_team do Reason Network para achar as sessões nas pastas ds-01, ds-02 e ds-03.
Envie a cada uma o conteúdo do seu briefing (briefing/A-cartas.md, B-fps.md, C-ouro.md) com send_message.
Não implemente o que puder delegar. Acompanhe, revise cada diff contra as metas e contra CLAUDE.md,
rode `python scripts/run_tests.py -q` e `ruff check . && ruff format --check .` antes de integrar.
Integre na branch ds/overlay (cherry-pick de commits revisados). Uma mudança por commit, por finalidade.

REGRAS ABSOLUTAS
- Nunca faça push, merge na galinacio/main, reset --hard, force, nem apague branches. Quem publica sou eu.
- Nunca mude: formato de patch/assinatura, mutex, mensagens da ponte, dados em %LOCALAPPDATA%\SEXO2.
- Textos visíveis, nomes, menus, cores e layout novos NÃO se implementam: registre como pendente
  em docs/produto/decisoes.md e me pergunte. Sem imagens geradas.
- Nada de polling, timer ou observador novo sem necessidade. Não declare ganho de FPS sem medição.
- Mensagens de commit em inglês, sem nome de modelo ou de ferramenta de IA.
- Não use automação que jogue por mim (nada de aceitar fila, escolher campeão ou criar lobby por script).

QUANDO ESCALAR PARA O CLAUDE (só com minha autorização, ver seção 7 do guia): 2 tentativas fracassadas
na mesma meta, ou decisão de arquitetura, ou risco de conta. Prepare o resumo no formato do guia e pare.
'@
$arquivos['config\trabalhador.txt'] = @'
Você é um trabalhador DeepSeek do projeto SEXO2. Trabalhe SOMENTE na sua worktree (a pasta atual).
Leia CLAUDE.md e docs/estudos/GUIA-DEEPSEEK-OVERLAY.md antes de começar.
Aguarde o briefing do coordenador pelo Reason Network (check_inbox ou mensagem recebida).

Faça: investigue, escreva primeiro o teste que reproduz o problema, depois a correção mínima,
rode `python scripts/run_tests.py -q` e `ruff check . && ruff format --check .`.
Commits pequenos, por finalidade, mensagem em inglês, sem nome de modelo. Não faça push.
Ao terminar: envie ao coordenador resumo, arquivos alterados, resultado dos testes, o que NÃO foi
verificado (o que só dá para ver no jogo real) e o hash do commit.
Não toque em arquivos fora do escopo do briefing. Não mude textos visíveis nem o visual.
Dúvida de produto ou de segurança: pergunte ao coordenador, não decida.
'@
$arquivos['briefing\A-cartas.md'] = @'
META: reconhecer as 3 cartas de aprimoramento na Arena (fila 1750, CHERRY) e no ARAM Mayhem (2400, KIWI)
nas capturas reais do dono em projeto\capturas\ (arena_*.png, mayhem_*.png).

ESTADO: o log mostrou "title OCR available" e "arena: 57 augments, 57 icons" e NENHUMA linha
"[AUGMENTS] offer:" numa partida de Arena. O catálogo da Arena foi ampliado depois (augments/catalog.py) sem
validação. ARENA_LAYOUT foi medido em UMA captura 1920x1080; a Arena de 2026 mudou (3x6, rodada 15, níveis
de aprimoramento): o layout pode ter mudado.

PRIMEIRO (diagnóstico, sem consertar): escreva um script em scripts/ (não entra no app) que, para cada PNG
de projeto\capturas\, imprima: cards_present() (e borders_lit()), as 3 caixas de carta e de título em pixels,
o texto lido pelo OCR em cada título, o melhor nome do catálogo e a confiança, e salve recortes de cada carta
e de cada título em projeto\medicoes\recortes\. Com isso, ache ONDE falha: (1) a porta das bordas nunca
acende, (2) as caixas caem fora das cartas, (3) o OCR lê lixo, (4) o texto não bate com o catálogo
(idioma, acentos, nome do pool), (5) o catálogo não tem aquele aprimoramento.

DEPOIS: corrija a causa, com teste usando as capturas (copiadas, sem nome de jogador, para
tests/fixtures/augments/ com linha em ORIGEM.md). Um manifesto com os IDs/nomes esperados por captura.

ARQUIVOS: sexo2/augments/{vision,ocr,catalog,session,offers}.py, sexo2/overlay/augment_overlay.py,
tests/test_augments.py, tests/fixtures/augments/.
ACEITE: todas as capturas do dono reconhecidas (ou "?" quando duvidoso, nunca errado com confiança alta);
os testes antigos continuam passando; suíte e ruff verdes.
NÃO MEXER: visual/texto do overlay, WR/PR, formato de dados. Só leitura de tela é permitida (nada de memória).
SÓ NO JOGO REAL: se o layout vale em outras escalas de interface do jogo. Diga isso no relatório.
'@
$arquivos['briefing\B-fps.md'] = @'
META: descobrir se o FPS cai pela CAPTURA de tela ou pela JANELA por cima do jogo, e deixar o overlay
dentro do ruído de 3 medições. NÃO declare ganho sem medição (docs/MEDICAO.md).

ESTADO: sexo2/overlay/study.py mede 3 janelas de 40 s com PresentMon (nada, captura, janela) e a versão de
teste devolveu "frames": 0 nas três, sem dizer por quê (o app já pede administrador). O código já guarda
o código de saída e o início do CSV quando isso acontece; a próxima versão mostra a causa. O dono vai medir
à mão (seção 9 do guia) e te entregar os CSV em projeto\medicoes\.

FAÇA: (1) leia os CSV com sexo2.overlay.study.summarize_csv e conclua: qual configuração derruba o FPS
(MsBetweenPresents, 1% low, PresentMode: "Hardware: Independent Flip" x "Composed: Flip");
(2) se o PresentMon automático do app não funciona onde o manual funciona, ache a diferença (nome do
processo, argumentos, sessão ETW de outra execução, caminho do exe);
(3) proponha e implemente a menor mudança que traga o FPS ao ruído, por ordem de custo:
   a) capturar só a tira fina das bordas (já feito em vision.border_strip) e só durante o jogo;
   b) captura por DXGI (dxcam) em vez de ImageGrab (GDI), uma região pequena, sob demanda;
   c) janela do overlay do tamanho do texto (já feito) e só visível durante a oferta;
   d) se a janela por cima ainda tira o jogo do independent flip: avaliar mostrar o overlay fora do jogo
      (segundo monitor/painel no cliente). ISSO MUDA A INTERFACE: não implemente, descreva e pergunte.
Cada mudança com teste e com uma linha no relatório: "FPS antes X / depois Y (3 repetições, ruído Z)".

ARQUIVOS: sexo2/overlay/{study,augment_overlay,gold_overlay,alpha_surface,runtime}.py, sexo2/augments/vision.py.
NÃO MEXER: watchdog, recuperação e GAME_EXIT_GRACE_S da injeção (injection/).
'@
$arquivos['briefing\C-ouro.md'] = @'
META: o número de ouro cai exatamente sobre a linha certa do placar (Tab) em todas as resoluções do dono,
sem perda de FPS acima do ruído, e só em Summoner's Rift, Swiftplay, ARAM e Mayhem (nunca em Arena).

ESTADO: sexo2/overlay/gold_overlay.py foi calibrado em UMA captura 1920x1080 (gold_rows_top, gold_row_step
em config.ini). A janela é de alpha por pixel só da coluna central (alpha_surface.py). Lê a tecla Tab a cada
100 ms e a API local a no máximo 1 Hz com o Tab segurado. O dono diz que está "errado na tela" e que cai FPS.

FAÇA: (1) com as capturas tab_*.png de projeto\capturas\, calcule onde o código desenharia cada número e
sobreponha num PNG de conferência em projeto\medicoes\ (para o dono ver o desalinhamento); ache a causa
(escala da interface, proporção 16:10, linha do jogador local, 5 vs 5 linhas, ordem das linhas);
(2) torne o cálculo das linhas proporcional à altura da tela e à escala da interface, com teste por resolução;
(3) meça o FPS (B-fps.md) com o Tab segurado, com e sem o overlay; se cair, reduza o custo (bitmap
redesenhado só quando os valores mudam, que já existe; janela só enquanto o Tab está pressionado).
ARQUIVOS: sexo2/overlay/gold_overlay.py, alpha_surface.py, sexo2/services/gold.py, tests/test_gold_overlay.py.
NÃO MEXER: o visual aprovado (D-130: modo B), cores, textos.
SÓ NO JOGO REAL: o alinhamento final; entregue o PNG de conferência para o dono aprovar.
'@
$arquivos['capturas\LEIA-ME.txt'] = @'
Coloque aqui as capturas (PNG, tela inteira, tecla Print Screen):
  arena_1920x1080_01.png   (escolha de aprimoramentos da Arena)
  mayhem_2560x1440_01.png  (escolha de aprimoramentos do ARAM Mayhem)
  tab_sr_1920x1080_01.png  (placar com Tab aberto)
E escreva abaixo: placa de video, taxa do monitor, resolucao, modo de janela e escala da interface do LoL.
'@

foreach ($nome in $arquivos.Keys) {
    $alvo = Join-Path $root $nome
    if (Test-Path $alvo) { Write-Host "ja existe, mantido: $nome"; continue }
    [IO.File]::WriteAllText($alvo, ($arquivos[$nome] -replace "`r?`n", "`r`n") + "`r`n", $utf8)
    Write-Host "criado: $nome"
}

if ($Clonar) {
    $repo = Join-Path $root 'principal'
    if (-not (Test-Path $repo)) { git clone https://github.com/teuzimmmm/sexo2.git $repo }
    git -C $repo fetch origin
    git -C $repo switch -c ds/overlay origin/galinacio
    foreach ($n in '01','02','03') {
        git -C $repo worktree add -b "agents/ds-$n" (Join-Path $root "agentes\ds-$n") HEAD
    }
    git -C $repo worktree list
}

Write-Host ""
Write-Host "Pronto: $root"
Get-ChildItem $root -Recurse -Depth 2 -Directory | Where-Object { $_.FullName -notmatch '\\\.git|\\principal\\' } | ForEach-Object { $_.FullName.Substring($root.Length) }
