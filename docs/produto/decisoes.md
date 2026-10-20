# Registro de decisões

Fonte única das decisões de produto e arquitetura. Agentes consultam este arquivo antes de propor ou
implementar interface, nomes ou comportamento. Status possíveis: **aprovada**, **pendente**,
**rejeitada** e **obsoleta**.

- Uma decisão aprovada vale sem nova consulta enquanto o contexto não mudar.
- Uma decisão nova entra como pendente e não é implementada.
- Exemplos em propostas não são decisões.

O histórico anterior está em `docs/arquivo/DECISOES.md` (entrega r6) e no plano-mestre.

## Aprovadas

| ID | Decisão | Origem |
|---|---|---|
| D-001 | O núcleo continua em Python e evolui por marcos, sem reescrita. | plano-mestre, ADR-1 |
| D-002 | O assistente de seleção roda no Pengu e substitui o botão de mods da seleção (`SEXO2-CustomWheel`). | plano-mestre, ADR-2 |
| D-003 | Dados estatísticos, cache e escritas no LCU ficam só no Python; o Pengu exibe e envia intenções. | ADR-3 |
| D-004 | Cloudflare Tunnel, relay e chave da sala ficam como estão. | ajuste A1 |
| D-005 | A telemetria herdada do Rose foi removida. | ajuste A1 |
| D-006 | A ponte local não usa segredo entregue aos plugins; recusa `Origin` externo e `Host` que não seja deste computador. | M1, ADR-4 revisto |
| D-007 | Tipografia: Oswald (títulos, cabeçalhos, categorias, destaques) e Inter (todo o resto). Estatísticas em `tabular-nums`. Nenhuma terceira família. Arquivos WOFF2 locais. Componentes nativos do Windows usam Segoe UI. | ajuste A7 |
| D-008 | Sem rótulos explicativos na interface (ex.: “dados ranked”, “valor em itens”). A honestidade estatística fica na lógica. | ajuste A5 |
| D-009 | Overlay de ouro: sobre o placar (Tab), linha a linha. Seta azul para o seu time quando a diferença é a favor, vermelha para o time inimigo quando é contra. Diferença sem sinal abaixo, na mesma cor. Totais no topo. | ajuste A5, §3.7 |
| D-010 | Aprimoramentos e itens de Arena e ARAM Mayhem exibem WR e PR, com fonte, patch e amostra. | ajuste A3 |
| D-011 | A injeção funciona na 1.6.4. Não refazer por antecipação; preservar testes e recuperação. | ajuste A4 |
| D-012 | Sem Electron. Propostas de interface em Markdown, ASCII ou HTML estático; nunca imagens geradas. | instruções do projeto |
| D-013 | Desenvolvimento na branch `sexoatividade`, por marcos. A `main` e as releases só mudam com autorização. | instruções do projeto |
| D-014 | Escala tipográfica: opção B de `design/propostas/tipografia.html`, compactada para o cliente. O dimensionamento final segue em avaliação no protótipo `sexo2-v1`. | usuário, sessão v1.0 |
| D-015 | Fluxo de runas: recomendação exibida não importa nada. Clicar num card importa a página original na hora. Edições válidas são aplicadas sozinhas, agrupadas, uma de cada vez; a mais recente vence. A última página confirmada é preservada se a seleção terminar. Uma operação antiga nunca afeta outra sessão ou campeão. Páginas pessoais não são sobrescritas. | usuário, sessão v1.0 |
| D-016 | Não há rótulos de origem dos dados, mas a natureza da estatística aparece no tooltip: WR da runa-chave, do trio de itens ou de cada item. O valor no placar é o preço dos itens, não o ouro obtido. | usuário, sessão v1.0 |
| D-017 | O visual do protótipo `sexo2-v1` (tipografia, cores, componentes, ícones de runas, organização) está aprovado; só ajustes, sem novo redesenho. O assistente abre logo acima do botão SEXO2 da seleção: borda direita alinhada à do botão, 8 px de distância, abrindo para cima, sempre dentro da janela, sem cobrir o botão. | usuário, sessão 1.0b |
| D-018 | Conjunto de itens: uma única página gerenciada “SEXO2 — {Campeão}”, reaproveitada entre campeões, com até nove seções em três grupos: `{WR}% — {N} partidas` (maior WR; WR do trio core observado), `Itens iniciais`, `Alternativas`; o mesmo para a mais jogada; `Counter {Campeão} — {WR}% — {N} partidas` (WR do confronto), `Itens iniciais`, `Alternativas`. Sem o confronto, o terceiro grupo não aparece. Conjuntos pessoais nunca são alterados nem apagados; os gerenciados são reconhecidos pelo `uid`. | usuário, sessão 1.0b |
| D-019 | A importação do conjunto de itens é automática ao confirmar o campeão (SR, ARAM, Swiftplay), sem abrir o assistente, e se repete quando o campeão muda. Campeão provisório ou de outro jogador não importa. | usuário, sessão 1.0b |
| D-125 | Aprimoramentos: o título de cada carta é lido com OCR (o do próprio Windows) e comparado com os nomes do modo; o ícone fica como reserva. Os textos sob as cartas seguem o protótipo (nome lido; “WR · PR · partidas”; “Sem dados”; “Não reconhecida”). | usuário, sessão 1.0b |
| D-126 | A Arena mostra WR quando a fonte a fornece, além de PR e partidas (a supressão em `lolalytics/` foi removida). | usuário, sessão 1.0b |
| D-020 | Aprimoramentos de Arena e ARAM Mayhem: só as cartas realmente oferecidas, com correção manual; nada é escolhido pelo SEXO2; números de Arena e Mayhem nunca se misturam; sem WR inventada; com só PR e partidas, mostram-se só esses. Destaque discreto das estatisticamente melhores. | usuário, sessão 1.0b |
| D-127 | Seção “Overlays” em Configurações: caixas “Ouro no placar (Tab)” e “Aprimoramentos na Arena e no Mayhem”, que gravam `[Overlay] gold_enabled`/`augments_enabled` e ligam ou desligam ao salvar, sem reiniciar; abaixo, “O jogo precisa estar em tela sem bordas.” | usuário, sessão 1.0b |
| D-128 | Ouro no placar com o visual do Blitz, desenhado pelo SEXO2 (sem arquivos do Blitz): losango escuro com borda bronze na divisa das linhas, seta azul ou vermelha dentro e a diferença embaixo; barra dos totais com moeda antes de cada total e o losango da diferença no meio; números sem separador de milhar, como o placar. Fica fora do estilo do app por pedido do usuário (“mais natural in-game”). | usuário, sessão 1.0b |
| D-129 | Escolhas além das recomendações, no estilo do painel (D-017), definidas pelo agente por delegação do usuário (“faça do seu jeito”). Itens: botão “Outras builds” abre a lista dos trios observados (mais jogados primeiro; ícones, WR e partidas; campo “Buscar item”); clicar põe o trio como primeira seção do conjunto SEXO2, acima das seções padrão, e “Voltar ao padrão” desfaz. Runas: seção “Outras runas” com cada runa-chave (WR e partidas); clicar abre a página mais jogada com ela no editor, como as recomendações (ranked e ARAM). Substitui a proposta D-118. | usuário, sessão 1.0b |
| D-130 | Overlay de ouro com o design aprovado (modo B), no lugar do visual Blitz de D-128 e das setas de D-009: em cada linha o número com sinal (+850, -3.000; zero = `0`) e uma barra discreta embaixo (trilho `#3c494b`, 140 px a 1280; barra `min(58, |v|/12)` px; vantagem `#97d1b8`, desvantagem `#edaf8c`, número `#e4eadf` negrito), indo para o lado da equipe em vantagem; no topo só o total com sinal num retângulo `#253b35` com texto `#c4dfba`; sem totais por equipe, setas, losangos, ‘ITENS’ nem ‘ouro’. Preço ausente não desenha linha nem total parcial. Referência: `overlay-aprovado.png` e `design/propostas/sexo2-overlays` (#b). Reaplicada na integração 0.9 (D-128 tinha prevalecido). Aprovada pelo usuário em 19/10/2026. | usuário, 19/10/2026 |
| D-112 | O ícone novo (`assets/sexo2.svg`, D-123) é o único ícone e marca do app em qualquer lugar que teria ícone; Galo e BORK não têm mais papel de marca (arquivos removidos). Decidido; aprovado pelo usuário na sessão de design em 19/10/2026. | usuário, 18–19/10/2026 |

## Pendentes

| ID | Assunto | Onde será decidido |
|---|---|---|
| D-101 | Dimensionamento final da escala B compactada | protótipo `design/propostas/sexo2-v1` |
| D-102 | Cores, incluindo a cor de sinal | proposta futura (M4) |
| D-103 | Componentes base: botão, lista, cartão, seletor, aviso | proposta futura, com `design/wireframes.md` |
| D-104 | Navegação e menus (Hub, assistente, configurações) | antes do M7 |
| D-105 | Destino das funções de mods (opções A, B ou C do plano) | antes do M7 |
| D-106 | Automatismos: critério de “maior WR”, nível de risco, amostra mínima, uso do adversário inferido (a importação automática de itens foi decidida em D-019) | antes do M8 |
| D-107 | Linguagem e textos visíveis | inventário de textos (M4/M5) |
| D-108 | Limites aceitáveis de RAM, CPU e FPS | depois da linha de base (`docs/MEDICAO.md`) |
| D-109 | Oferecer “voltar à versão anterior” | M2 ou posterior |
| D-110 | Fila (queue ID) do novo modo competitivo | informação do usuário |
| D-111 | Opt-in para Dynamic Workflows | por marco |
| D-113 | Nome da página de runas gerenciada (provisório: “SEXO2”). O conjunto de itens foi decidido em D-018 | antes do M8 |
| D-114 | Sem página de runas livre: hoje a importação falha com `no_free_page` e nenhuma página pessoal é apagada ou sobrescrita | antes do M8 |
| D-115 | Painel SEXO2: cantos retos, cabeçalho só "SEXO2" (Oswald), menus Sala, Favoritas, Configurações, Suporte e Swiftplay (só no Swiftplay); abre em Sala. Implementado em `SEXO2-Hub`. Proposto pelo usuário na sessão de design de 18/10/2026. Aprovado pelo usuário na sessão de design em 19/10/2026. | aprovada |
| D-116 | Favoritas: todos os campeões, busca por campeão e por skin, skins com imagem do cliente, cromas favoritáveis separadamente, só o botão "Favoritar". Implementado em `SEXO2-Amigos` (e `skin-index` em `friends/service.py`). Proposto pelo usuário na sessão de design de 18/10/2026. Aprovado pelo usuário na sessão de design em 19/10/2026. | aprovada |
| D-117 | Assistente da seleção 452×492 (plugin `SEXO2-Assistant`): Rota, Confronto e Fonte no topo; abas Runas, Itens, Mods e Todas as configurações (Preferências rápidas retirada pelo usuário em 19/10/2026); sem aba Skins; biblioteca de mods na aba Mods. Proposto pelo usuário na sessão de design de 18/10/2026. Aprovado pelo usuário na sessão de design em 19/10/2026. | aprovada |
| D-119 | Remover Conjuntos (perfis) e Sorteio como funções: apenas retirados da UI. O código e os testes ficam (o sorteio serve à Bravura). Remoção de código só com testes que provem equivalência. Nota para a equipe. Aprovado pelo usuário na sessão de design em 19/10/2026. | aprovada |
| D-120 | Swiftplay: o campeão sem escolha (nem pin do SEXO2 nem skin no cliente) recebe sorteio ponderado, favoritas primeiro; o sorteado nunca é gravado como escolha. Implementado; proposto pelo usuário na sessão de design de 18/10/2026. Aprovado pelo usuário na sessão de design em 19/10/2026. | aprovada |
| D-122 | M5b: identificadores `Rose` renomeados para `SEXO2` com leitura do formato antigo; formato de código/link de sala e metadados dos mods mantidos (a pasta de dados migra para `SEXO2` por decisão própria). Em validação pelo usuário; não aprovada. Falta validação no Windows. | `docs/PROGRESSO-M5B.md` |
| D-124 | Nova abertura animada do SEXO2 (`[ícone] SEXO 2` → `[ícone] 2`, 2,55 s, uma vez; fundo `#0d0e10`, Oswald 600, ícone aprovado). Implementada no plugin `SEXO2-Startup` conforme `skins/identidade/animacao-abertura/HANDOFF.md`; validação em `docs/ABERTURA-QA.md`. Aprovada pelo usuário na sessão de design em 19/10/2026 (o pedido foi explícito); falta o teste no cliente real | confirmação do usuário |
| D-123 | Novo ícone do aplicativo (SEXO2 · “2 · Degrau”, `assets/sexo2.svg`) aplicado no executável, atalhos, instalador, atualizador, janelas, bandeja, aviso do Pengu e item de menu do cliente, no lugar do galo. Aprovado pelo usuário na sessão de design em 19/10/2026. Tray “iniciando” e “pronto” idênticos: diferença visual (se desejada) é decisão nova, pendente. Galo/BORK: D-112 | `docs/ICONE-NOVO.md` |
| D-131 | Filas sem estatísticas (Arena etc.): o botão SEXO2 abre o assistente normal (452×492, ancorado) só com as abas Mods e Todas as configurações; sem Rota, Confronto e Fonte nem Runas e Itens. Filas com estatísticas: como antes. Implementado em `SEXO2-Assistant`. Aprovado pelo usuário em 19/10/2026. | aprovada |
| D-132 | Remover o painel de mods antigo (`SEXO2-CustomWheel`, `window.__sexo2Mods`) e o código morto da aba Preferências rápidas. Aprovado pelo usuário em 19/10/2026. Código morto das Preferências rápidas removido. O painel antigo NÃO foi removido: é a única interface de seleção de mods (por skin, mapas, fontes, locutores e categorias) e das reaplicações do modo histórico; remover exige antes decidir onde essa seleção passa a viver (ver `docs/PROGRESSO-INTEGRACAO.md`). | parcial: aguarda decisão do usuário |
| D-133 | Sala sempre online: relay próprio num Worker da Cloudflare (plano gratuito), `sexo2-sala.matheus-barbosa-gomes10.workers.dev`, no lugar do relay público do Rose. Mesmo protocolo do relay local; o link por túnel (`trycloudflare.com`) continua funcionando. Pedido pelo usuário em 19/10/2026. Código em `sala/`. | aprovada |
| D-134 | Início limpo na 1.7.0: na primeira abertura, `%LOCALAPPDATA%\Rose` e `%LOCALAPPDATA%\SEXO2` são apagadas inteiras (configurações, favoritas, biblioteca de mods, Pengu, logs), uma vez só (`sexo2/fresh_start.py`). Exceção pedida pelo usuário em 20/10/2026 à regra de preservar os dados; os mods da pasta Rose não são migrados. Não roda com o LoL ou outro SEXO2/Rose aberto, nem apaga a pasta de onde o SEXO2 roda. | aprovada |
| D-135 | Build favorita por campeão, separada para SR (ranqueada, normal, Swiftplay) e ARAM: em Runas, "Fixar como favorita" no rodapé (página aplicada) e a linha "Favorita" com "Desafixar"; em Itens, "Fixar"/"Desafixar" no cabeçalho e o título "Build favorita" quando o trio do topo é o fixado. Ao confirmar o campeão, a página favorita é aplicada (fora do Swiftplay) e o trio favorito encabeça o conjunto; se não servir mais, não é aplicada, o aviso "Favorita indisponível neste patch." aparece e o padrão fica. Salvo em `assistant-favorites.json`. Aprovado pelo usuário em 20/10/2026. | aprovada |
| D-136 | Importação automática de runas: ao confirmar o campeão (fora do Swiftplay), sem favorita, ou com favorita indisponível, o SEXO2 importa a página Maior WR, a não ser que o jogador já tenha escolhido ou aplicado uma página nessa seleção. Uma escolha posterior do jogador substitui a importada. Pedido pelo usuário em 20/10/2026. | aprovada |
| D-137 | Runas automáticas no Swiftplay: ao escolher os campeões no lobby, cada slot recebe a página favorita do campeão (SR) ou a Maior WR do Swiftplay, uma vez por campeão e lobby (uma página que o jogador definir depois fica). Só escreve se o campo de runas do slot estiver no formato conhecido; senão registra no log e não mexe. Sem mudança visual. Pedido pelo usuário em 20/10/2026. | aprovada |
| D-138 | Configurações salvam sozinhas: caixas na hora, números e textos ao sair do campo ou com Enter; sem os botões "Salvar alterações" e "Descartar alterações". "Aceitar partidas automaticamente" sai do Suporte e vai para Configurações, logo após "Ocultar categorias de mods vazias", com o mesmo texto de ajuda. Pedido pelo usuário em 20/10/2026. | aprovada |
| D-139 | Cliente com plugins antigos: ao abrir, o SEXO2 reinicia a tela do cliente do LoL (sem tocar no jogo) quando os arquivos dos plugins mudaram desde que o cliente abriu, para não ser preciso fechar o LoL à mão. Só em Início, Lobby ou fim de partida; em fila, seleção ou jogo espera. Loader de outro Pengu do usuário não é reiniciado. Aprovado pelo usuário em 20/10/2026. | aprovada |

## Rejeitadas

| ID | Alternativa | Motivo |
|---|---|---|
| D-201 | Token da ponte entregue por endpoint ou arquivo legível pelos plugins | Não protege nada além do que `Origin` e `Host` já cobrem. |
| D-202 | WebView2, Tauri ou Electron para janelas e overlays | RAM comparável à do Electron no Windows (ADR-5). |
| D-203 | Rótulos explicativos sobre a origem dos dados | Ver D-008. |

Nota (antiga D-121, "Hub"/"Atividades"): o usuário decidiu "é só tirar"; o app não exibe esses nomes (19/10/2026).
