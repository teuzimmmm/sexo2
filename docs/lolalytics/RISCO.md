# Risco nas recomendações LoLalytics

O nível de risco controla quanto cada WR observada é suavizada em direção a
uma referência do campeão. É uma política local para ordenar candidatos com
amostras diferentes; não é uma porcentagem de risco, intervalo de confiança,
probabilidade calibrada nem previsão de WR.

## Fórmula e níveis

Para uma observação com `n` jogos e WR `observedWR`, a pontuação é:

```text
(n × observedWR + k × referenceWR) / (n + k)
```

`k` é o prior de jogos de build para o nível escolhido. Um prior maior puxa
mais a pontuação para a referência; um prior menor dá mais peso à observação.
O padrão é `medium`.

| Nível | Prior geral no DraftGap (`priorGames`) | Prior de build no DraftGap | Prior usado no SEXO2 |
| --- | ---: | ---: | ---: |
| `very-low` | 3000 | 3000 | 3000 |
| `low` | 2000 | 2000 | 2000 |
| `medium` | 1000 | 1000 | 1000 |
| `high` | 500 | 750 | 750 |
| `very-high` | 250 | 500 | 500 |

A referência do SEXO2 é a WR agregada do campeão no contexto confirmado da
consulta. Isso difere do modelo histórico/de Elo esperado e dos ratings
cruzados do DraftGap. O SEXO2 usa a coluna de prior de build acima para todas as
observações a que aplica risco, inclusive os candidatos de runa principal; não
copia a implementação DraftGap.

Sem WR, sem contagem de jogos ou com zero jogos, a pontuação fica indisponível;
esses casos não viram zero nem entram como sucesso. A ordenação mantém esses
candidatos sem pontuação ao final. As observações originais não são alteradas.
A conta usa a WR arredondada fornecida pelo site, sem inventar um contador exato
de vitórias. Priors são pesos da política e não aumentam os jogos observados.

Popularidade e incerteza usam quantidades diferentes. Um item escolhido em
10 de 100 jogos e em 10.000 de 100.000 tem a mesma frequência observada (10%),
mas a segunda frequência vem de uma amostra muito maior. Pick rate informa
popularidade; jogos e WR da tabela correspondente informam a amostra usada na
suavização. Não derive uma dessas medidas da outra.

## Fontes da recomendação

Em consulta geral, o SEXO2 seleciona entre os layouts completos `summary.win`
e `summary.pick` usando WR e jogos da runa principal observados na própria
resposta. Esse escopo é a amostra da primária (`metric_scope`), não a amostra
conjunta dos nove IDs. Se houver `keystone` explícita, somente candidatos com
essa primária são considerados. O resultado limita-se aos dois layouts do
upstream; não é uma busca de ótimo global. Contra oponente, a recomendação usa
somente o condicionamento pelo adversário, sem filtro de keystone.

As tabelas de itens continuam independentes e são ordenadas separadamente com
as métricas próprias de cada escolha. As pontuações de runa usam a referência
WR do campeão no contexto da consulta inicial; as tabelas de itens usam a WR do
campeão no contexto da fonte dos itens (`item_source.champion_query_overview`),
que pode ser uma consulta filtrada por keystone. A proveniência `item_source`
registra URL, query, filtros resolvidos, coleta e cache. A saída pode incluir o
`build_page` proposto pelo site, mas sua ordem não é reconstruída com os itens
mais bem ranqueados em tabelas distintas. Não interprete um ranking de escolhas
como uma build de seis itens observada.

Em Arena, recomendações usam popularidade/pick rate. Risco baseado em WR é
`not_applicable`; não se reconstrói WR de itens ou aprimoramentos a partir de
contagens ocultas.
O campo `pick_rate` preserva o valor da fonte. Algumas tabelas de itens de
Arena trazem valores acima de 100 (a fixture de Jinx contém 570,73 para o ID
220000). Sua semântica exata de frequência não foi confirmada: o coletor ordena
esse valor como popularidade, sem limitá-lo a 100 ou anunciá-lo como probabilidade
de uma partida. Isso não muda a ausência de WR de itens/aprimoramentos.

## API, CLI e preferência salva

```sh
python -m lolalytics ahri --lane middle --recommend --risk-level medium
python -m lolalytics ahri --lane middle --recommend --risk-level high --opponent annie --opponent-lane middle
python -m lolalytics jinx --mode aram --tier all --recommend --risk-level low
python -m lolalytics jinx --mode arena --tier all --recommend
```

`Client.recommend(Query, risk_level="medium")` retorna um `Recommendation` com
query, filtros resolvidos, fonte, horário/cache, política, candidatos de runas,
seleção recomendada, build fornecida pela fonte, rankings separados de itens,
avisos e versão de schema. O caminho da biblioteca aceita override explícito;
CLI usa `--recommend` e `--risk-level`. Consulta de matchup é explicitamente
opponent-conditioned e não soma condicionamentos.

Nesta integração à main, a biblioteca e a CLI recebem o nível explicitamente
ou usam `medium`. Não dependem das configurações do aplicativo. O adaptador
`LolalyticsService` e sua persistência/UI permanecem na branch experimental,
fora desta entrega.

```python
from lolalytics import Client, Query

with Client() as client:
    result = client.recommend(Query("ahri", lane="middle"), risk_level="high")
    print(result.to_dict())
```

`Client.recommend` é uma API distinta de `collect_builds` e
`collect_matchup`: esta recomendação retorna os candidatos de runa observados,
a seleção escolhida, a página de build do site e rankings por tabela. Em
matchup, a página é opponent-conditioned e não recebe filtro de keystone. Em
Arena, não há pontuação WR e o ranqueamento segue pick rate.
`recommended_selection` registra `win` ou `pick` também no matchup; a identidade
de sua `build_page.selection` permanece `vs`. Em Arena, ambas são indisponíveis.

O risco é aplicado localmente sobre os dados já coletados. Repetir a mesma
consulta e keystone enquanto o cache estiver válido reutiliza a fonte sem novo
GET. Mudar de nível pode escolher outra primária e exigir um GET para essa nova
consulta filtrada. Uma chamada geral usa no máximo dois GETs de fonte (base e
keystone escolhida); dois níveis distintos podem precisar de três no total
(base e duas primárias diferentes). Matchup, keystone explícita e Arena usam
uma fonte por chamada. Cada GET mantém o limite de três tentativas do transporte.
`cache_hit` da recomendação só é verdadeiro se todas as fontes usadas vierem do
cache; `build_page.cache_hit` e `item_source.cache_hit` descrevem sua própria fonte.

## Origem da fórmula e reprodução

A referência de desenho é DraftGap, commit MIT
[`872c6d5cebfec186fdebb14005fd42b2bf84ad22`](https://github.com/vigovlugt/draftgap/tree/872c6d5cebfec186fdebb14005fd42b2bf84ad22).
Veja os arquivos de [níveis de risco](https://github.com/vigovlugt/draftgap/blob/872c6d5cebfec186fdebb14005fd42b2bf84ad22/packages/core/src/risk/risk-level.ts),
[análise de draft](https://github.com/vigovlugt/draftgap/blob/872c6d5cebfec186fdebb14005fd42b2bf84ad22/packages/core/src/draft/analysis.ts)
e [análise de builds](https://github.com/vigovlugt/draftgap/blob/872c6d5cebfec186fdebb14005fd42b2bf84ad22/packages/core/src/builds/entity-analysis.ts).
Os arquivos podem ser conferidos sem copiar sua implementação:

```sh
git clone https://github.com/vigovlugt/draftgap.git /tmp/draftgap-risk-reference
git -C /tmp/draftgap-risk-reference show 872c6d5cebfec186fdebb14005fd42b2bf84ad22:packages/core/src/risk/risk-level.ts
git -C /tmp/draftgap-risk-reference show 872c6d5cebfec186fdebb14005fd42b2bf84ad22:packages/core/src/draft/analysis.ts
git -C /tmp/draftgap-risk-reference show 872c6d5cebfec186fdebb14005fd42b2bf84ad22:packages/core/src/builds/entity-analysis.ts
```

Validação offline:

```sh
python -m unittest tests.test_lolalytics_risk tests.test_lolalytics_recommendations -q
```

A verificação HTTP ao vivo é limitada e opt-in:

```sh
python scripts/lolalytics_risk_probe.py --live --output docs/lolalytics/risk-live-2026-10-16.json
```

Consulte o relatório sanitizado [risk-live-2026-10-16.json](risk-live-2026-10-16.json)
e a validação consolidada em [RISCO_VALIDACAO.md](RISCO_VALIDACAO.md).
