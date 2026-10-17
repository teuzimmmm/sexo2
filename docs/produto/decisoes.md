# Registro de decisões

Fonte única das decisões de produto e arquitetura. Agentes consultam este arquivo antes de propor ou
implementar interface, nomes ou comportamento. Status possíveis: **aprovada**, **pendente**,
**rejeitada** e **obsoleta**.

- Uma decisão aprovada vale sem nova consulta enquanto o contexto não mudar.
- Uma decisão nova entra como pendente e não é implementada.
- Exemplos em propostas não são decisões.

O histórico anterior está em `docs/DECISOES.md` (entrega r6) e no plano-mestre.

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

## Pendentes

| ID | Assunto | Onde será decidido |
|---|---|---|
| D-101 | Dimensionamento final da escala B compactada | protótipo `design/propostas/sexo2-v1` |
| D-102 | Cores, incluindo a cor de sinal | proposta futura (M4) |
| D-103 | Componentes base: botão, lista, cartão, seletor, aviso | proposta futura, com `design/wireframes.md` |
| D-104 | Navegação e menus (Hub, assistente, configurações) | antes do M7 |
| D-105 | Destino das funções de mods (opções A, B ou C do plano) | antes do M7 |
| D-106 | Automatismos: critério de “maior WR”, nível de risco, amostra mínima, uso do adversário inferido | antes do M8 |
| D-107 | Linguagem e textos visíveis | inventário de textos (M4/M5) |
| D-108 | Limites aceitáveis de RAM, CPU e FPS | depois da linha de base (`docs/MEDICAO.md`) |
| D-109 | Oferecer “voltar à versão anterior” | M2 ou posterior |
| D-110 | Fila (queue ID) do novo modo competitivo | informação do usuário |
| D-111 | Opt-in para Dynamic Workflows | por marco |
| D-112 | Papel do Galo e do BORK na nova identidade | com D-102 |

## Rejeitadas

| ID | Alternativa | Motivo |
|---|---|---|
| D-201 | Token da ponte entregue por endpoint ou arquivo legível pelos plugins | Não protege nada além do que `Origin` e `Host` já cobrem. |
| D-202 | WebView2, Tauri ou Electron para janelas e overlays | RAM comparável à do Electron no Windows (ADR-5). |
| D-203 | Rótulos explicativos sobre a origem dos dados | Ver D-008. |
