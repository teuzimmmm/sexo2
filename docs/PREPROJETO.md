# Pré-projeto para aprovação (18/10/2026)

Tudo abaixo está implementado na versão de teste. O que você recusar volta atrás em um commit;
o que aprovar fica. Responda por número: "1 aprovado", "2 recusado: motivo", e assim por diante.

Versão de teste: `teste-c88070e` (link na mensagem final).

## Para aprovar

### 1. Ícone do aplicativo (D-121)
Sete opções de galo vermelho e branco, minimalistas, com o mesmo desenho do tamanho grande ao de
16 px: `design/propostas/icone/index.html` (prévias em tamanho real, borrado, barra de tarefas,
área de trabalho e bandeja). **Recomendação: B (galo com barbela, fundo grafite).**
A versão de teste já usa a B em todo lugar (executável, atalhos, janela, bandeja e mensagem do
Pengu), só para você ver no Windows. Para trocar: `python scripts/apply_icon.py <letra>`.

### 2. Mensagem de boas-vindas do Pengu
Título "SEXO2" no lugar de "Rose", o ícone do SEXO2 no lugar da rosa, sem os selos de Discord,
Ko-fi e GitHub do Rose. Na tela de carregamento do cliente, "SEXO2" no lugar de "Rose"; o atalho
"Visit homepage" da paleta do Pengu deixa de abrir o GitHub do Rose. Os textos da mensagem
("Hi Summoner, your League is now Unlocked!", "Do not show again") são do Pengu e não mudaram.

### 3. Favoritas com imagens
Campeões em grade com retrato; clicar abre a tela do campeão com um cartão por skin (imagem do
próprio cliente). Clicar no cartão marca ou desmarca; favoritas coloridas com contorno e o selo
"Favorita", as outras apagadas; cromas como bolinhas de imagem sob a skin; "← Voltar".

### 4. Outras builds e Outras runas (D-120)
Itens: botão "Outras builds" com os trios observados (mais jogados primeiro, WR e partidas) e
"Buscar item"; clicar põe o trio no topo do conjunto SEXO2; "Voltar ao padrão" desfaz.
Runas: seção "Outras runas" com cada runa-chave; clicar abre a página mais jogada com ela no
editor. Feito por delegação ("faça do seu jeito"); confirme os nomes e o lugar.

### 5. Ouro no placar
Visual do Blitz (D-119, já aprovado) com a seta centralizada. A queda de FPS ao apertar Tab
continua em aberto: falta o teste com o VSync desligado no LoL (ver "Para testar").

### 6. Ícone, rodada 3
Atende ao "da esquerda mais sério e menacing" e ao "da direita mais simples":
`design/propostas/icone/rodada3.html` (oito de traço, quatro angulares). **Recomendação: L7
(traço, crista simples)**; da família angular, R1 (silhueta com olho vermelho). Escolha uma letra
e eu troco o ícone da versão de teste.

### 7. Padrão visual (auditoria em `docs/organizacao/design.md`, seção 7)
1. Cores de estado: ok `#7bd5a7` e erro `#f3a090`/`#d9a796` ainda sem token aprovado (D-102).
2. Painéis herdados (Automático/Pins, PartyMode, SettingsPanel) e as rodas sobre a seleção
   (Chromas, Formas, Skin personalizada, Aleatória, Histórico): migram para o visual neutro do
   SEXO2 ou mantêm o visual do cliente de propósito?
3. Tokens novos: linha suave, sombra, sobreposição, selo, foco visível e os tamanhos 22/13/11.
4. Overlay de aprimoramentos: trocar Segoe UI por Inter (como o ouro) e o amarelo `#f2d27a` por um
   token de destaque.
5. Ordem da migração (seção 6 do documento).

### 8. Código compartilhado dos plugins (`docs/organizacao/plugins.md`)
`waitForBridge`, `injectCSS` e `escapeHtml` estão copiados em vários plugins. Juntar num só lugar
(SEXO2-Style ou um plugin utilitário)? Muda comportamento de carga; só com teste e medição.

## Feito nesta rodada (sem mudar comportamento)

- Menus do SEXO2 com as fontes e cores aprovadas (Inter/Oswald, tokens `--s2-*`): Amigos,
  Configurações, Biblioteca de mods e a tela de carregamento (fundo `#0d0e10`). Inventário em
  `docs/organizacao/menus.md`.
- Plugins Hub, Amigos, Biblioteca de mods, Configurações e Startup deixaram de ser uma linha só:
  código legível, provado idêntico pela árvore sintática (`scripts/js_ast_equal.cjs`).
- Python: imports sem uso removidos (`docs/organizacao/python.md`).
- Documentação: índice em `docs/README.md`, antigos em `docs/arquivo/`, verificador de links.

## Sem decisão sua (correções)

- Campeões repetidos nas Favoritas: os IDs 60000+ (cópias de modos especiais) saíram da lista.
- Logs: `sexo2_*.log`, `sexo2_runoverlay_*.log` e `sexo2_diagnostics.txt` (o antigo é renomeado).
- Fechar o SEXO2 com o LoL aberto não reinicia mais o cliente, e reabrir com o mesmo cliente
  também não: os plugins continuam carregados e só reconectam.
- Erro "DLL never attached" do LTK ganhou uma dica própria no Diagnóstico (antivírus bloqueando
  a `ltk_patcher_dll.dll` ou arquivos do LTK desatualizados).
- Painel do assistente: abre na posição certa, conecta mesmo com o SEXO2 aberto depois do LoL
  e importa o conjunto de itens.
- Overlay da Arena: reconhece a partida mesmo com o SEXO2 aberto no meio dela.
- Configurações: caixas para ligar os overlays sem reiniciar (D-117).

Da branch `galinacio` aproveitei a base técnica do ouro (janela pequena, transparência real,
conexão reaproveitada) e a ideia de não reiniciar o cliente ao fechar o SEXO2, refeita para
também não reiniciar ao reabrir. A proposta de outras builds foi substituída pela versão enxuta.

## Para testar no cliente

1. Ícone: barra de tarefas, atalho, bandeja e a mensagem do Pengu ao abrir o LoL.
2. Favoritas: abrir um campeão, marcar skins e cromas, voltar.
3. Seleção (modo treino): Outras builds (escolher um trio, conferir na loja do jogo) e Outras
   runas (escolher uma runa-chave e confirmar).
4. Fechar o SEXO2 na seleção de campeões e abrir de novo: o cliente não pode reiniciar e o
   painel tem que voltar a funcionar.
5. Ouro: Tab com o VSync ligado e depois desligado; diga se a queda de FPS some.
6. Arena: as estatísticas aparecem sob as cartas.
