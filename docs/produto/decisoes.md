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
| D-002 | O assistente de seleção roda no Pengu e substitui o botão de mods da seleção (`ROSE-CustomWheel`). | plano-mestre, ADR-2 |
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
| D-115 | Aprimoramentos: o título de cada carta é lido com OCR (o do próprio Windows) e comparado com os nomes do modo; o ícone fica como reserva. Os textos sob as cartas seguem o protótipo (nome lido; “WR · PR · partidas”; “Sem dados”; “Não reconhecida”). | usuário, sessão 1.0b |
| D-116 | A Arena mostra WR quando a fonte a fornece, além de PR e partidas (a supressão em `lolalytics/` foi removida). | usuário, sessão 1.0b |
| D-020 | Aprimoramentos de Arena e ARAM Mayhem: só as cartas realmente oferecidas, com correção manual; nada é escolhido pelo SEXO2; números de Arena e Mayhem nunca se misturam; sem WR inventada; com só PR e partidas, mostram-se só esses. Destaque discreto das estatisticamente melhores. | usuário, sessão 1.0b |
| D-117 | Seção “Overlays” em Configurações: caixas “Ouro no placar (Tab)” e “Aprimoramentos na Arena e no Mayhem”, que gravam `[Overlay] gold_enabled`/`augments_enabled` e ligam ou desligam ao salvar, sem reiniciar; abaixo, “O jogo precisa estar em tela sem bordas.” | usuário, sessão 1.0b |
| D-119 | Ouro no placar com o visual do Blitz, desenhado pelo SEXO2 (sem arquivos do Blitz): losango escuro com borda bronze na divisa das linhas, seta azul ou vermelha dentro e a diferença embaixo; barra dos totais com moeda antes de cada total e o losango da diferença no meio; números sem separador de milhar, como o placar. Fica fora do estilo do app por pedido do usuário (“mais natural in-game”). | usuário, sessão 1.0b |
| D-120 | Escolhas além das recomendações, no estilo do painel (D-017), definidas pelo agente por delegação do usuário (“faça do seu jeito”). Itens: botão “Outras builds” abre a lista dos trios observados (mais jogados primeiro; ícones, WR e partidas; campo “Buscar item”); clicar põe o trio como primeira seção do conjunto SEXO2, acima das seções padrão, e “Voltar ao padrão” desfaz. Runas: seção “Outras runas” com cada runa-chave (WR e partidas); clicar abre a página mais jogada com ela no editor, como as recomendações (ranked e ARAM). Substitui a proposta D-118. | usuário, sessão 1.0b |

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
| D-112 | Papel do Galo e do BORK na nova identidade | com D-102 |
| D-113 | Nome da página de runas gerenciada (provisório: “SEXO2”). O conjunto de itens foi decidido em D-018 | antes do M8 |
| D-114 | Sem página de runas livre: hoje a importação falha com `no_free_page` e nenhuma página pessoal é apagada ou sobrescrita | antes do M8 |
| D-121 | Ícone do aplicativo: galo vermelho e branco minimalista, sem azul; sete opções (A a G) com o mesmo desenho em todos os tamanhos e `.ico` prontos. Recomendação: B (galo com barbela, fundo grafite) | `design/propostas/icone/index.html` |

## Rejeitadas

| ID | Alternativa | Motivo |
|---|---|---|
| D-201 | Token da ponte entregue por endpoint ou arquivo legível pelos plugins | Não protege nada além do que `Origin` e `Host` já cobrem. |
| D-202 | WebView2, Tauri ou Electron para janelas e overlays | RAM comparável à do Electron no Windows (ADR-5). |
| D-203 | Rótulos explicativos sobre a origem dos dados | Ver D-008. |
