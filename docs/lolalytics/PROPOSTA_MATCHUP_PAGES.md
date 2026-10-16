# Proposta: builds por matchup e páginas de itens

A API atual permanece como base: `collect_builds(query)` entrega as duas sugestões condicionadas à keystone (`win` e `pick`). A extensão adiciona consulta explícita de adversário e retorna uma terceira sugestão `vs`, usando runas e itens do mesmo snapshot filtrado. Não preencher `vs` com dados gerais se a resposta não tiver esse bloco.

## DTO e funções puras

- `MatchupQuery`/campos de consulta incluem adversário escolhido e lane própria; resultado guarda os filtros pedidos e resolvidos para detectar redirects ou mismatch.
- `BuildCollection.pages` conserva WR/Common; campo aditivo `matchups: list[BuildPage]` comporta os alvos consultados. Um alvo novo é uma nova consulta/resultado cacheável, sem mutar as sugestões anteriores.
- `BuildPage.selection="vs"`, `label="vs Annie"` e título com nome e métricas exclusivamente do bloco core do matchup. `source_url`, query/resolved, data, cache e avisos continuam por página.
- `pack_item_pages(collection, max_sections_per_page)` é pura e recebe limite configurável; não codifica nem presume o limite aceito pelo LoL. Retorna DTO `ItemPage(sections, source_pages)` e preserva todas as seções, repartindo em páginas se necessário.
- Cada seção/bloco conserva `section_label` (`WR`, `Common`, `vs Annie`), `kind`, itens, ordem, métricas e proveniência. Até em página única, o prefixo aparece em cada bloco e no título da seção.
- Não deduplicar itens entre seções: o mesmo ID em WR e matchup representa recomendações e amostras diferentes. Agrupar duplicatas de IDs somente dentro do conjunto de partida que já as agrega por quantidade.
- Essas funções convertem DTOs; não acessam LCU, inventário pessoal, estado de partida, watch de draft ou importação. Sugestão externa e página de itens preparada são tipos distintos de uma futura página pessoal importada.

## Regras e limites

- Adversário é escolha explícita; validar slug/ID, modo e lane conforme endpoint confirmado. Preservar lane própria e adversário pedido/resolvido; não inferir lane do oponente nem misturar estatísticas de outras posições.
- Métricas mantêm a origem (`core` para título, cada alternativa para seu próprio wr/n). Incluir jogos; amostra ausente não vira zero. Amostra pequena recebe aviso com limiar configurável e documentado, sem descartar build nem declarar recomendação estatisticamente segura.
- Cache e frescor são por query completa, incluindo adversário e keystone. Ao trocar alvo, mostrar qual alvo originou cada seção; uma resposta velha não deve aparecer como alvo atual. Informar horário/patch e `cache_hit`/stale para decisões do overlay futuro.
- Alvos diferentes podem exceder o limite de seções/páginas: divisão é determinística, configurável e sem perda. Limite configurado é política do consumidor, não afirmação sobre capacidade exata do LoL.
- Futuro consumidor escolhe explicitamente entre prévia de sugestão e importação de página. Nunca substituir ou excluir páginas pessoais existentes implicitamente; escrita no jogo exige fluxo próprio e consentimento explícito.

## Decisão implementada

O contrato final ficou em PLANO_MATCHUPS.md: `collect_matchup` devolve um
BuildPage independente por alvo, sem adicionar estado de alvo atual ao cliente
ou alterar a dupla de `collect_builds`. O consumidor combina explicitamente
`[*general.pages, matchup]` no planejador. A fonte não permite keystone+vs nas
amostras testadas e não fornece core conjunto: itens de matchup são por slot.
