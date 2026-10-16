# Extensão da core: adversário e planejamento de páginas

2026-10-16. Contratos antes da implementação. Integração de draft, seleção de
adversário no overlay e escrita no LoL ficam para depois. Biblioteca continua
sem estado global de alvo atual: cada consulta contém o adversário explícito.

## Descobertas que determinam o desenho

Rotas reais do site `/lol/ahri/vs/{annie|ryze}/build/q-data.json` retornam
summary.win/pick com runas e itens. Matchups testados não possuem core observado:
items.item1..3 são escolhas individuais, item4..6 são alternativas. Combinação
vs+keystone retornou404 em6tentativas com keystones8992 e8112. Não combinar os
IDs dos três slots e anunciar um core com estatística conjunta. Não preencher
uma falha com dados gerais. Ver INVESTIGACAO_MATCHUPS.md.

WR/Common gerais continuam filtrados por keystone, como contratado na rodada
anterior. A terceira sugestão é Highest Win do matchup, condicionada somente ao
adversário. Runa sugerida e itens são da mesma resposta de matchup, sem alegação
de condicionamento conjunto por keystone. Limitado a ranked confirmado; Arena
continua estatísticas/pick rate e ARAM não terá matchup inventado.

## Contratos e propriedade

A — Query/parsing/tests/test_lolalytics_matchup_query.py:
`Query` ganha `opponent: str | None = None`, `opponent_lane: str = 'all'` ao fim.
Slug validado igual champion. Opponent só ranked, region all nesta rodada; sem
opponent, opponent_lane precisa all. Opponent+keystone rejeitado ANTES HTTP.
Rota `/lol/{champion}/vs/{opponent}/build/q-data.json`, params existentes EXCETO region (region=all explícito retorna404), +
`vslane=opponent_lane`. Cache key inclui tudo pela URL. Sem opponent URL antiga
não muda. Parsing valida nav.vs/vsCid/vsLane e header.vs; sem opponent rejeitar
resposta inesperadamente com vs. Ids positivos não bool; vsLane refletido exato.
Resolved inclui opponent, opponent_id/name, opponent_lane, effective_opponent_lane
quando header fornece. Validar header.vsLane contra pedido concreto e contra
LANES; header.lane/queue/patch/cid existentes continuam. Metadata não corresponde
é SchemaError; nenhum echo de corpo remoto. Melhorar effective_lane para usar
header.defaultLane quando header.lane está None/all; sem ambos concretos não
inferir. Testar offline com fixtures reais projetadas pelo coordenador.

B — item_pages.py/tests/test_lolalytics_item_pages.py:
Dataclasses `PreparedItemBlock(label:str, block:ItemBlock, source:dict)` e
`PreparedItemPage(title:str, blocks:list[PreparedItemBlock])`, to_dict/asdict.
`plan_item_pages(pages:list[BuildPage], *, max_pages:int=1,
max_blocks_per_page:int=20) -> list[PreparedItemPage]`.
Função pura, não LCU e não afirma qual é o limite real do LoL. Até20sugestões
explícitas; limites inteiros positivos não bool, max_pages<=20,
max_blocks_per_page<=100. Rejeitar entrada vazia/sem blocos. Mesmo champion,
mode,patch,tier,region e lane efetiva; não misturar patches/filtros/posições.
Copiar os blocos sem deduplicar IDs ou descartar alternativas/métricas. Prefixo
legível em CADA bloco ('WR · Core', 'Common · Item 4', 'vs Annie · Item 1').
Não usar título completo/WR como label curto. Distribuição determinística, ordem
por entrada e por blocos. Se não cabe nos limites configurados, QueryError antes
de retornar plano parcial; consumidor troca/remova sugestões explicitamente.
Padrão20blocos permite2gerais(5+5)+1matchup(7) numa página; outro alvo aumenta
blocos e pode requerer2páginas ou troca do alvo. Campos source incluem título,
query/resolved/url/coleta/cache/warnings e escopo, para distinguir sugestões.
Título de página 'Builds de Ahri' + índice se dividido. Não excluir/modificar
páginas pessoais. DTO de planejamento é distinto de payloadLCU. Input não mutado.

C — matchups.py/client.py/__main__.py/__init__.py e
`tests/test_lolalytics_matchups.py`:
`build_matchup_page(snapshot, *, min_games:int=100) -> BuildPage` em matchups.py,
reutiliza dataclasses ItemChoice/ItemBlock/BuildPage; valida snapshot.query e
resolved opponent consistentes, keystone ausente e summary.win completo.
Runa: pri4/sec2/mod3 e metadata page preservada, sem métricas conjuntas.
Blocos: starting agregado, item1/2/3 como blocos com UMA escolha e suas próprias
métricas, item4..6 alternativas. Ausências opcionais avisadas, mas falta de layout
ou TODOS itens -> DataUnavailable; tipos inválidos SchemaError. Não criar core.
BuildPage.selection='vs', label='vs Annie', title='WR vs Annie / taxa conjunta
indisponível', keystone=pri[0] (identifica runa SUGERIDA, não filtro aplicado).
core_metrics={'win_rate':None,'games':None}. resolved/query mostram adversário
mas keystone=None. warnings incluem opponent_conditioned,
keystone_filter_unavailable, not_joint_build_sample e low_item_sample para
choice.n < min_games ou missing_item_sample para nNone. Limiar é política local
configurável, não estimativa de confiança nem descarte de sugestão. ItemChoice
raw preservado, métricas item a item não copiadas para conjunto. Não mostrar
WR de runa como se representasse a página inteira. Não atribuir métricas de
header ao título do conjunto. BuildPage ganha campos default adicionais
`conditioning: str = "keystone"` e `matchup_metrics: dict | None = None`;
matchup usa conditioning="opponent" e matchup_metrics de overview wr/games,
escopo explícito campeão-confronto, nunca métricas da build. Um resultado independente por alvo consultado.

`Client.collect_matchup(query, *, min_games=100)->BuildPage`: exige opponent,
ranked; collect(query) uma consulta validada/cacheável; montagem pura. Trocar
alvo=novo Query e novo resultado, nunca mutação de anterior. collect_builds com
opponent rejeita QueryError antes rede: API distinta evita inferir core.
CLI `--opponent SLUG`, `--opponent-lane ...`, `--matchup`, `--min-games 100`.
--matchup exigeopponent; --builds+opponent e --item-sets+opponent incompatíveis.
--opponent sem --matchup pode collect raw normalizado; filtrosresolved seguros.
Exportar modelos/funções de planejamento e factory no __init__ após integração;
B não editará __init__. Não implementar overlay/importação. Futuro consumidor
chama collect_builds(queryGeral), collect_matchup(queryComAlvo), depois
plan_item_pages([*gerais.pages,vs], max_pages=...).

## Problemas e soluções de produto registradas

- Mesma keystone em geral e matchup NÃO torna itemização equivalente; manter
  contexto/alvo e amostra separados mesmo quando IDs coincidirem.
- 'Ideal' significa sugestão Highest Win do site no filtro, não vitória garantida.
  Amostras pequenas são avisadas, nunca criar classificação de confiança.
- O consumidor futuro espera draft e escolhe alvo. Respostas assíncronas devem
  ser associadas à query e descartadas se alvo atual mudou; API não aciona draft.
- O limite efetivo/páginas existentes do LoL será lido pelo importador futuro.
  Planejador recebe orçamento disponível e nunca apaga páginas do usuário.
- Um plano compacto conserva grupos de origem visíveis e pode ser recusado se
  não couber com clareza. Não cortar listas silenciosamente para forçar1página.

## Etapas/conclusão

1. [concluído] Fonte real vs2adversários e limitações registradas.
2. [concluído] Query/validação, matchup, planejador delegados a Luna low.
3. [concluído] Coordenador revisa todos diffs e testes, corrige em rodadas.
4. [concluído] Validação real limitada de dois adversários, troca de alvo e
   composição com WR/Common; regressões; documentação e commits locais.

## Revisão de encerramento

Implementação por subagentes gpt-6-luna reasoning low, com arquivos exclusivos.
Coordenador leu diffs, reproduziu fontes, revisou entregas e testes. Rodadas
adicionais corrigiram títulos sem métricas, schema/IDs, aliases de fixtures,
sentinela de adversário ausente, validação das posições e metadados do cache.
Nenhum fallback geral é usado para simular matchup/keystone indisponível.
Dados do jogo/overlay e importação permanecem futuros. Ver CORE_VALIDACAO.md
para testes offline, provas reais e regressões. Commit local ao fim da rodada;
sem push, release, instalador ou escrita no cliente.
