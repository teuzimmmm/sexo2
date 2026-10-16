# API de sugestões de builds

O módulo `lolalytics` coleta sugestões agregadas do LoLalytics, sem conectar ao
LCU, Pengu, overlay ou processo do jogo. Esta API cobre builds gerais filtradas
pela runa principal e uma sugestão Highest Win por adversário. Ela não grava,
importa nem ativa runas ou itens no cliente LoL.

## Builds gerais: WR e Common

`Query` recebe o campeão e os filtros usuais. Em Ranked, `lane="all"` é aceito,
mas `collect_builds` precisa de uma posição efetiva resolvida para fixar as
consultas pela keystone; prefira informar uma posição concreta quando ela já é
conhecida. A saída tem duas páginas: `selection="win"` (`label="WR"`) e
`selection="pick"` (`label="Common"`). Cada página e seus blocos carregam
query, filtros resolvidos, URL, horário, cache e avisos de origem.

```sh
python -m lolalytics ahri --lane middle --builds
python -m lolalytics ahri --lane middle --builds --keystone 8992
python -m lolalytics ahri --lane middle --keystone 8992
```

Sem `--keystone`, o cliente lê a keystone de `summary.win` e `summary.pick` na
consulta-base, fixa patch e lane efetivos e consulta cada keystone. Se ambas as
sugestões tiverem a mesma keystone, a resposta filtrada é reutilizada. Com
`--keystone ID`, ambas vêm da mesma resposta filtrada. `--keystone` sozinho
retorna o snapshot normalizado; `--builds --keystone ID` retorna as duas páginas
estruturadas. Builds estruturadas são oferecidas em Ranked e ARAM; Arena não é
suportada nesse modo.

Keystone também foi confirmada por HTTP em ARAM: a verificação ao vivo de Jinx
consultou a base e o filtro 8008, e ambas as sugestões filtradas usaram essa
primária (WR 60,6% / 3.090 jogos e Common 55,6% / 14.421 jogos). O probe
registrou três cenários e seis consultas HTTP no total; consulte o
[manifest das fixtures](../../tests/fixtures/lolalytics/keystone/manifest.json)
e o [probe reproduzível](../../scripts/lolalytics_builds_probe.py).

```python
from lolalytics import Client, Query, plan_item_pages

with Client() as client:
    general = client.collect_builds(Query(
        "ahri", patch="16.20", lane="middle", tier="emerald_plus"))
    vs = client.collect_matchup(Query(
        "ahri", patch="16.20", lane="middle", tier="emerald_plus",
        region="all", opponent="annie", opponent_lane="middle"), min_games=100)
    pages = plan_item_pages([*general.pages, vs], max_pages=1)
    print([page.to_dict() for page in pages])
```

WR e Common são filtros da fonte condicionados à keystone principal. O título
usa exclusivamente `summary.*.items.core.wr` e `.n` do core: por exemplo,
`WR 52.7% / 1.795 jogos` ou `Common ...`. Métricas indisponíveis continuam
indisponíveis, sem virar zero. A página completa de nove runas não tem taxa
conjunta validada; `warnings` inclui `not_full_rune_page_joint_sample`. A runa
principal identifica o filtro aplicado, mas não prova coocorrência dos nove IDs
com os itens.
`BuildPage.conditioning` é `"keystone"`; os blocos planejados carregam o escopo
`keystone_conditioned` nos metadados `source`.

Os blocos preservam conjuntos iniciais, core ordenado de três itens e escolhas
alternativas individuais para itens 4, 5 e 6. Alternativas não formam uma
sequência de compra. IDs permanecem opacos, e o DTO da biblioteca não é formato
de importação Riot. Consulte [RUNAS_E_ITENS.md](RUNAS_E_ITENS.md) e
[FONTES.md](FONTES.md) para evidências e limites.

## Matchup: uma sugestão contra adversário explícito

Use `Query(opponent=..., opponent_lane=...)` e `Client.collect_matchup`. A rota
observada é ranked, com região resolvida `all`; a URL envia lane, vslane e tier
(por padrão `emerald_plus`) e omite o parâmetro `region`, pois `region=all`
explícito retornou 404. Mantenha `Query.region="all"`. O matchup não aceita
keystone: as tentativas `/vs/` com keystone retornaram 404, então o cliente não
simula esse filtro nem volta silenciosamente a dados gerais.

```sh
python -m lolalytics ahri --lane middle --opponent annie \
  --opponent-lane middle --tier emerald_plus --matchup --min-games 100
```

A página é Highest Win (`selection="vs"`) de `summary.win` do payload do
oponente. Suas runas e blocos de itens são extraídos dessa resposta. `item1`,
`item2` e `item3` são escolhas individuais; `item4` a `item6` são alternativas.
Não existe core observado no matchup, logo não se combinam os três primeiros
slots nem se apresenta taxa conjunta runas+itens. `core_metrics` permanece com
`win_rate=None` e `games=None`; `matchup_metrics` é uma métrica separada de
escopo campeão-confronto. O título explicita que a taxa conjunta está
indisponível. A keystone no campo `BuildPage.keystone` identifica a primária
sugerida, não um filtro usado na consulta. Avisos incluem
`opponent_conditioned`, `keystone_filter_unavailable` e `not_joint_build_sample`.
Aqui `BuildPage.conditioning` é `"opponent"`; o planejador registra o escopo
`opponent_conditioned` na proveniência de cada bloco.

Se a pessoa escolher a runa principal sugerida contra o adversário e quiser
atualizar WR/Common para essa runa, componha uma nova consulta geral com o mesmo
campeão, patch, lane e keystone. Não inclua `opponent` nessa consulta:
`collect_builds` retorna WR/Common gerais condicionadas à primária, sem filtro de
adversário. A itemização de matchup continua opcional e separada, condicionada
somente pelo adversário. O consumidor pode planejar só WR/Common após a escolha,
sem adicionar a página de matchup como uma terceira sugestão.

```python
general_for_rune = client.collect_builds(Query(vs.query["champion"], patch=vs.resolved["patch"], lane=vs.query["lane"], tier=vs.query["tier"], region="all", keystone=vs.keystone))
```

`min_games` (CLI `--min-games`, padrão 100) apenas adiciona `low_item_sample`
para escolhas abaixo do limiar, ou `missing_item_sample` se `n` não existe. É
política local de aviso: não mede confiança, não remove itens e não muda sua
ordenação.

Consultas gerais e de matchup ficam separadas mesmo se exibirem a mesma runa:
isso não garante que a itemização geral se aplique ao confronto. Um novo
adversário exige um novo `Query` e resultado, sem estado global de alvo.

## Planejamento de páginas de itens

`plan_item_pages(list_of_build_pages, max_pages=1, max_blocks_per_page=20)` é
uma função pura que prepara blocos e metadados de origem para um consumidor
futuro. Ela não conhece nem afirma o limite real de páginas do LoL. Com os
contratos atuais, WR e Common têm até cinco blocos cada e a sugestão de matchup
até sete: as três sugestões chegam a 17 blocos e cabem no padrão de 20. Duas
sugestões gerais mais dois matchups somam até 24 blocos e exigem pelo menos duas
páginas com orçamento de 20.

Passe o orçamento conhecido pelo futuro importador. Se não couber em
`max_pages`/`max_blocks_per_page`, a função falha sem devolver plano parcial;
quem chama precisa aumentar o orçamento ou escolher/remover alvos
explicitamente. Ela não corta sugestões, não deduplica itens, não altera páginas
pessoais e conserva `source` por bloco (`query`, `resolved`, URL, seleção,
escopo, cache, coleta e avisos). Rótulos como `WR · Core`, `Common · Item 4` e
`vs Annie · Item 1` mantêm a origem visível.

Não há integração com draft, seleção de adversário no overlay, importação de
runas/itens, LCU ou gravação de páginas no jogo. Sugestões estruturadas e o
planejador são dados para uma etapa futura; não devem ser descritos como
sugestões já importadas.
