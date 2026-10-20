# Guia: resolver os overlays com DeepSeek + Reason Network (Claude só no limite)

Adaptação do guia "OpenCode + Reason Network + DeepSeek + Claude Sonnet" para o trabalho que
falta no SEXO2: **overlay de aprimoramentos (Arena e ARAM Mayhem)** e **overlay de ouro**.
Escrito em 20/10/2026. Windows, PowerShell.

> **O que é fato e o que não é.** Os comandos do Reason Network (`reason-network who|send|setup`,
> ferramentas `list_team` e `send_message`) conferem com o README do projeto. Os do OpenCode e a
> chave da DeepSeek **não foram conferidos aqui** (o site do OpenCode não abre neste ambiente):
> confirme com `opencode --help` e com a documentação antes de seguir. O Reason Network é só um
> canal de mensagens; ele **não** cria sessões, não distribui tarefas sozinho e não faz merge.

---

## 1. O problema, em três linhas

| # | Sintoma | O que já se sabe |
|---|---|---|
| A | Aprimoramentos: "quase nunca reconhece as cartinhas" | OCR do Windows está disponível; no log da Arena de 15:50 só carregou o catálogo (57 aprimoramentos) e **nenhuma oferta foi reconhecida**. Não há captura real da Arena atual nos testes. |
| B | O FPS cai ~50% (antes eram ~10x) | Não se sabe se a culpa é a **captura de tela** ou a **janela por cima do jogo**. O estudo embutido (versão `teste-0e22c6d`) rodou, mas o PresentMon devolveu **0 quadros** nas três medições. |
| C | Ouro: "está errado na tela e faz cair FPS" | Calibrado só em 1920x1080; outras resoluções e escalas de HUD nunca foram vistas. Sem medição de FPS. |

Já está decidido e **não precisa de pesquisa**: a API local do jogo e o cliente **não** entregam as
cartas oferecidas (confirmado na pesquisa e no estudo); o Overwolf não aprova app privado. O caminho é
**ler a tela**, barato e só na hora da oferta.

### Metas de aceite (valem para todo o trabalho)

1. **Cartas:** nas capturas reais de Arena e Mayhem do dono (resoluções dele), as 3 cartas certas em
   todas, ou "?" quando não tiver certeza; nunca uma carta errada com confiança alta.
2. **FPS:** com o overlay ligado, FPS médio e 1% low **dentro do ruído de 3 medições** do FPS com ele
   desligado (regra de `docs/MEDICAO.md` e da ADR-5).
3. **Ouro:** números alinhados às linhas do Tab em 1920x1080 e nas outras resoluções do dono, sem
   perda de FPS acima do ruído.
4. CI verde: `python scripts/run_tests.py -q`, `node --test tests/test_*.cjs`,
   `ruff check . && ruff format --check .`, `python design/build_tokens.py --check`.

---

## 2. O que SÓ você pode fornecer (bloqueia o trabalho de A e C)

Sem isso os agentes vão otimizar no escuro. Faça antes de ligar os agentes.

1. **Capturas de tela reais**, tela inteira, tecla `Print Screen`, salvas como PNG em
   `projeto\capturas\`:
   - Arena: 4+ capturas da escolha de aprimoramentos (de preferência uma logo depois de rolar de novo).
   - ARAM Mayhem: 4+ capturas da escolha.
   - Placar (Tab) aberto em partida de Summoner's Rift e em ARAM: 2 de cada.
   - Nomeie com a resolução e o modo: `arena_1920x1080_01.png`, `mayhem_2560x1440_02.png`,
     `tab_sr_1920x1080_01.png`.
2. **Configurações de vídeo:** print da tela Vídeo do LoL (resolução, modo de janela, escala da
   interface) e a **placa de vídeo + taxa do monitor** (ex.: RTX 3060, 144 Hz) num arquivo
   `projeto\capturas\LEIA-ME.txt`.
3. **Medida do FPS à mão**, 10 minutos (seção 9): é o que diz se o problema B é a captura ou a janela.

---

## 3. Quem faz o quê

Menos agentes que no guia original: os três problemas mexem em módulos vizinhos
(`sexo2/overlay/`, `sexo2/augments/`), e mais agentes só aumentam conflito e custo. Comece com **1
coordenador + 3 trabalhadores**; só amplie depois da primeira rodada integrada.

| Sessão | Pasta | Branch | Tarefa |
|---|---|---|---|
| Coordenador (DeepSeek) | `principal\` | `ds/overlay` | Distribui, revisa diffs, integra, roda os testes |
| ds-01 (DeepSeek) | `agentes\ds-01` | `agents/ds-01` | **A** reconhecer as cartas |
| ds-02 (DeepSeek) | `agentes\ds-02` | `agents/ds-02` | **B** medir e baixar o custo de FPS |
| ds-03 (DeepSeek) | `agentes\ds-03` | `agents/ds-03` | **C** corrigir e medir o overlay de ouro |
| Claude (Sonnet) | fora da rede | — | Só no limite (seção 7) |

Um quarto trabalhador (ds-04, **testes reais via CDP**, seção 8) entra quando A, B e C estiverem
andando.

---

## 4. Estrutura de pastas

```text
Documentos\
└── projeto\
    ├── principal\                 # clone de teuzimmmm/sexo2, branch ds/overlay (criada de galinacio)
    │   ├── .git\
    │   ├── CLAUDE.md              # regras do projeto (todos devem ler)
    │   ├── docs\estudos\          # OVERLAYS.md e este guia
    │   ├── sexo2\overlay\         # augment_overlay.py, gold_overlay.py, alpha_surface.py, study.py
    │   ├── sexo2\augments\        # vision.py, ocr.py, offers.py, catalog.py, stats.py
    │   ├── sexo2\services\gold.py
    │   └── tests\fixtures\augments\   # capturas reais de referência (ver ORIGEM.md)
    ├── agentes\
    │   ├── ds-01\                 # worktree agents/ds-01  (A: cartas)
    │   ├── ds-02\                 # worktree agents/ds-02  (B: FPS)
    │   └── ds-03\                 # worktree agents/ds-03  (C: ouro)
    ├── capturas\                  # SUAS capturas e o LEIA-ME.txt (fora do git)
    ├── medicoes\                  # CSV do PresentMon e resultados (fora do git)
    ├── config\
    │   ├── opencode.json
    │   ├── coordenador.txt
    │   └── trabalhador.txt
    └── briefing\                  # uma tarefa por arquivo; o coordenador lê e entrega
        ├── A-cartas.md
        ├── B-fps.md
        └── C-ouro.md
```

`capturas\` e `medicoes\` ficam **fora** do repositório (podem ter nome de jogador). Os agentes as
leem por caminho; as que virarem teste são copiadas, sem nome de jogador, para
`tests\fixtures\augments\` com uma linha em `ORIGEM.md`.

---

## 5. Instalação e comandos, na ordem

Todos em **PowerShell**. Rode o primeiro bloco em cada janela nova.

```powershell
$root = Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'projeto'
```

### 5.0 Atalho: um script cria as pastas e os arquivos

`criar-projeto-deepseek.ps1` (na mesma pasta deste guia) cria `Documentos\projeto` com as pastas da
seção 4, os arquivos de configuração da 5.6 e os briefings da seção 6. Não apaga nem sobrescreve nada que
já exista. Salve o arquivo e rode:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\criar-projeto-deepseek.ps1            # só pastas e arquivos
.\criar-projeto-deepseek.ps1 -Clonar    # também clona, cria ds/overlay e as 3 worktrees (5.2 e 5.3)
```

Os blocos 5.1 a 5.3 abaixo fazem o mesmo passo a passo, à mão.

### 5.1 Pastas

```powershell
New-Item -ItemType Directory -Force "$root\agentes","$root\config","$root\briefing","$root\capturas","$root\medicoes" | Out-Null
```

### 5.2 Código: clone e branch de integração

A branch oficial é **`galinacio`** (desde 20/10/2026). Não use `amolula`, `sexoatividade` nem `main`.

```powershell
git clone https://github.com/teuzimmmm/sexo2.git "$root\principal"
git -C "$root\principal" fetch origin
git -C "$root\principal" switch -c ds/overlay origin/galinacio
git -C "$root\principal" status
```

Dependências para rodar os testes (o CI usa Python 3.14 no Windows; use o mesmo; veja `requirements.txt`):

```powershell
Set-Location "$root\principal"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python scripts/run_tests.py -q
```

Se a suíte não passar **antes** de qualquer mudança, pare e me avise: o ponto de partida precisa estar
verde. (O teste `test_startup_resumes_a_game_a_dead_rose_left_suspended` falha de vez em quando por
tempo; rode de novo uma vez.)

### 5.3 Worktrees (uma pasta e uma branch por trabalhador)

```powershell
foreach ($n in '01','02','03') {
    git -C "$root\principal" worktree add -b "agents/ds-$n" "$root\agentes\ds-$n" HEAD
}
git -C "$root\principal" worktree list
```

Execute **uma vez**. Cada worktree precisa do seu próprio ambiente Python:

```powershell
foreach ($n in '01','02','03') {
    Set-Location "$root\agentes\ds-$n"
    python -m venv .venv
    .\.venv\Scripts\python.exe -m pip install -q -r requirements.txt
}
```

### 5.4 Conectar o DeepSeek (OpenCode)

1. Crie uma chave de API no painel da DeepSeek (platform.deepseek.com) e coloque crédito.
   **Nunca** salve a chave dentro de `projeto\principal` nem em arquivo versionado.
2. Abra o OpenCode e conecte o provedor:

```powershell
Set-Location "$root\principal"
opencode          # dentro dele: /connect  → escolha DeepSeek → cole a chave
```

3. Veja o identificador **exato** do modelo e use-o no passo 5.6:

```powershell
opencode models deepseek
```

4. Teste uma pergunta curta (ex.: "liste os arquivos de sexo2/overlay") e confirme que responde.

### 5.5 Conectar o Reason Network

Revise o script antes de rodar (ele instala um serviço local e abre o navegador para login numa
conta Reason, gratuita):

```powershell
irm https://reasonmachines.com/network/install.ps1 | iex
reason-network setup
reason-network who
```

Atenção: **os colegas da sua rede veem o nome da sessão, o computador, o repositório e a branch**
(ocupada ou livre). Use uma rede só sua.

### 5.6 Arquivos de configuração

`$root\config\opencode.json` (troque `SEU_ID_DEEPSEEK` pelo valor do passo 5.4):

```json
{
  "$schema": "https://opencode.ai/config.json",
  "model": "SEU_ID_DEEPSEEK"
}
```

`$root\config\coordenador.txt`:

```text
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
```

`$root\config\trabalhador.txt`:

```text
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
```

### 5.7 Abrir as sessões (uma aba do Windows Terminal para cada)

**Aba 1: coordenador**

```powershell
$root = Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'projeto'
$env:OPENCODE_CONFIG = "$root\config\opencode.json"
Set-Location "$root\principal"
$prompt = Get-Content -Raw "$root\config\coordenador.txt"
opencode --prompt $prompt
```

**Abas 2, 3 e 4: trabalhadores** (troque `ds-01` por `ds-02` e `ds-03`):

```powershell
$root = Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'projeto'
$env:OPENCODE_CONFIG = "$root\config\opencode.json"
Set-Location "$root\agentes\ds-01"
$prompt = Get-Content -Raw "$root\config\trabalhador.txt"
opencode --prompt $prompt
```

(Se o seu OpenCode for 2.x, o guia original aponta `opencode mini --prompt "..."`; confira
`opencode --help`.)

### 5.8 Teste da rede, antes de dar trabalho

Em outro PowerShell: `reason-network who` (devem aparecer as 4 sessões). No coordenador:

> Use list_team e me diga os nomes exatos das sessões nas pastas ds-01, ds-02 e ds-03. Depois envie ao
> ds-01 uma mensagem pedindo só a confirmação de recebimento. Não altere arquivos.

Só continue quando a resposta voltar.

---

## 6. Os briefings (copie cada um para `projeto\briefing\`)

### 6.1 `A-cartas.md` — reconhecer as cartas

```text
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
```

### 6.2 `B-fps.md` — medir e baixar o custo

```text
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
```

### 6.3 `C-ouro.md` — overlay de ouro

```text
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
```

---

## 7. Como usar o Claude, só no limite

O Claude custa mais; use-o **quando um agente DeepSeek empacar**, não como revisor de rotina.

**Quando escalar** (qualquer um): 2 tentativas fracassadas na mesma meta; uma decisão de arquitetura
(ex.: tirar o overlay de dentro do jogo); risco de conta Riot; conflito de integração que o coordenador
não resolve; ou o dono querer publicar uma versão.

**Pedido de escalação** (o coordenador prepara; você aprova antes de enviar):

```text
META:            (copie do briefing)
O QUE FOI TENTADO: (commits, hash e resultado de cada tentativa)
EVIDÊNCIA:       (saída do teste, CSV de FPS, PNG de conferência)
ALTERNATIVAS:    (2 ou 3, com custo e risco)
DECISÃO PEDIDA:  (uma pergunta fechada)
```

### Forma A (recomendada, sem instalar nada): o Claude desta conversa

1. O coordenador sobe a branch para revisão (isso **não** publica versão; só a `galinacio` publica):

```powershell
Set-Location "$root\principal"
git push -u origin ds/overlay
```

2. Você cola o pedido de escalação aqui e diz o nome da branch. O Claude daqui busca a branch, lê o
   diff, roda os testes, ajusta o que faltar e, **com o seu "pode"**, leva para a `galinacio`, que gera a
   versão de teste (`teste-<hash>`) para você baixar.

### Forma B: Claude Code no seu PC, dentro da rede

Só se você quiser o Claude conversando com os agentes. Mantenha a sessão **fechada** até a escalação:

```powershell
Set-Location "$root\principal"
claude --model sonnet --permission-mode plan
```

O Reason Network integra o Claude Code. Como instrução de comportamento não é barreira técnica, a única
garantia de que ele não é chamado sem você é **não abrir essa aba**.

---

## 8. Testes: o que automatizar e o que continua sendo seu

Da pesquisa de testes (`pesquisa-testes.md`), adaptada ao que já existe:

| Nível | O que cobre | Quem roda | Para o nosso caso |
|---|---|---|---|
| 0. Testes + capturas reais | OCR, caixas, layout do ouro sem janela | agentes e CI | **É o núcleo de A e C.** Quanto mais capturas suas, melhor. |
| 1. Medição de FPS à mão | A janela e a captura custam FPS? | você, 10 min | Seção 9. Insubstituível para B. |
| 2. Fumaça no cliente real (CDP) | plugin carregado, console, tela do cliente | ds-04, depois | Só depois de A/B/C. **Abre uma porta de depuração local no cliente: precisa da sua aprovação.** |
| 3. Partida real assistida | tudo junto, com overlay sobre o jogo | você | A validação final de cada versão. |

**Não automatize** criar lobby, aceitar fila nem iniciar partida por script: a política da Riot e a do
Pengu tratam isso como automação. Todo teste em partida é você jogando, e os agentes só **leem** os
arquivos que sobram (logs, CSV, capturas).

Bots só existem em Summoner's Rift personalizado; Arena e Mayhem exigem partida de verdade. O Practice
Tool (fila 3140) serve para o **ouro** e para o FPS do placar, não para os aprimoramentos.

---

## 9. Medir o FPS à mão (você, 10 minutos, já)

Responde sozinho a pergunta "é o overlay ou é a captura?" e destrava o trabalho B.

1. Baixe o `PresentMon-2.4.1-x64.exe` em `github.com/GameTechDev/PresentMon/releases` e salve como
   `Documentos\projeto\medicoes\PresentMon.exe`.
2. Abra o PowerShell **como administrador**, entre no Practice Tool (ou numa partida) e, com o jogo em
   tela cheia sem bordas, rode **em outra janela, com o jogo aberto**:

```powershell
cd "$([Environment]::GetFolderPath('MyDocuments'))\projeto\medicoes"
.\PresentMon.exe --process_name "League of Legends.exe" --output_file nada.csv --timed 40 --terminate_after_timed --no_console_stats --v1_metrics
```

3. Repita trocando o `--output_file` e o estado do SEXO2, **sempre segurando o Tab** (para o ouro) durante
   os 40 s:

| Arquivo | Estado do SEXO2 |
|---|---|
| `nada.csv` | os dois overlays desligados (Configurações) |
| `ouro.csv` | só "Ouro no placar" ligado |
| `aprimoramentos.csv` | só "Aprimoramentos" ligado (precisa estar numa Arena/Mayhem) |

4. Se o PresentMon avisar que falta permissão ou não achar o processo, **copie a mensagem inteira**:
   é exatamente o que falta para o estudo automático funcionar.
5. Resuma cada CSV (dentro de `principal\`, com o ambiente ativado):

```powershell
python -c "from pathlib import Path; from sexo2.overlay.study import summarize_csv; import sys; print(summarize_csv(Path(sys.argv[1])))" ..\medicoes\nada.csv
```

Mande-me (ou ao coordenador) os três resultados: `fps`, `low1` e `modes`. Se `modes` mostrar
"Hardware: Independent Flip" no `nada` e "Composed: Flip" com o overlay, **a janela por cima é o
problema**. Se os três forem iguais, é a captura ou o custo de CPU.

---

## 10. Ciclo de uma rodada

1. Você põe as capturas (seção 2) e faz as medições (seção 9).
2. Você diz ao coordenador: "Distribua as tarefas A, B e C" (e as pastas `capturas` e `medicoes`).
3. Cada trabalhador faz **diagnóstico primeiro**, teste que reproduz, correção mínima, commit.
4. O coordenador revisa cada commit, roda a suíte e integra em `ds/overlay`:

```powershell
Set-Location "$root\principal"
git status                      # precisa estar limpo
git cherry-pick HASH_DO_COMMIT  # só commits revisados e verdes
python scripts/run_tests.py -q
ruff check . ; ruff format --check .
```

5. As worktrees **não** recebem o que foi integrado. Antes da próxima rodada, em cada uma:

```powershell
Set-Location "$root\agentes\ds-01"
git merge ds/overlay            # merge, nunca reset --hard
```

6. Você sobe `ds/overlay` (seção 7, forma A) e me chama; eu confiro, publico a versão de teste e você
   joga as partidas de validação. Os diagnósticos (Suporte → "Gerar diagnóstico sem chave da sala")
   voltam para a próxima rodada.

---

## 11. Limites, custo e segurança

- **Custo:** comece com 4 sessões. Anote o saldo da DeepSeek antes e depois da primeira rodada; só amplie
  se a rodada trouxe commits integrados. Não deixe os agentes em laço aberto: peça "pare e relate" ao fim
  de cada tarefa.
- **Chaves:** a chave da DeepSeek fica só no OpenCode. Nada de chave, `config.ini`, `lockfile` ou nome de
  jogador em commit, em mensagem do Reason Network ou em capturas versionadas.
- **Rede Reason:** só você e suas sessões; os nomes de sessão, branch e pasta ficam visíveis a quem estiver
  nela.
- **Branches:** `main` e `galinacio` só são tocadas por mim, com o seu "pode". Todo `push` da `galinacio`
  gera uma versão de teste pública do repositório privado (CI).
- **Riot:** o app só lê (API local e tela). Nada de memória do jogo, nada de jogar por você, nada de
  mostrar WR de aprimoramento além do que a decisão D-126 já registrou. Ler o elo dos adversários e
  habilitar a porta de depuração do cliente também precisam da sua aprovação.
- **Formatação:** mudança só de formato vai em commit separado, provada com `python scripts/ast_equal.py`.

## 12. Checklist

- [ ] Capturas e LEIA-ME.txt em `projeto\capturas\` (seção 2).
- [ ] FPS medido à mão (seção 9), com as mensagens do PresentMon.
- [ ] `git`, `python`, `opencode` funcionam; `opencode models deepseek` lista o modelo.
- [ ] `principal` em `ds/overlay`, suíte verde antes de qualquer mudança.
- [ ] `git worktree list` mostra ds-01, ds-02 e ds-03.
- [ ] `reason-network who` lista as 4 sessões; a mensagem de teste chegou e voltou.
- [ ] Briefings A, B e C entregues; cada trabalhador começou pelo diagnóstico.
- [ ] Primeiro commit integrado, suíte verde, `ds/overlay` enviada para revisão.
- [ ] Claude só foi chamado com o pedido de escalação preenchido.
