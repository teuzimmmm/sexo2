# Fontes, capacidades e evidências

Consolidado e reproduzido pelo coordenador em 2026-10-16. A referência
[xPerSki/lolalytics-api](https://github.com/xPerSki/lolalytics-api) é **não oficial**,
licença MIT (copyright 2025 xPerSki). Não copiamos seu código. Duas funções
atuais funcionaram na amostra do agente (`get_champion_data`, `get_tierlist`);
ela não fornece o coletor de builds/runas/ARAM/Arena desta fase.

Legenda: **HTTP** = resposta real lida/decodificada; **código** = observação
em HTML/JS, sem prova de chamada; **hipótese** = não oferecer como capacidade;
**indisponível** = não confirmado, não suportado ou suprimido explicitamente.

| Categoria | Modo | Fonte | Filtros confirmados na amostra | Reprodução | Estado e limites |
| --- | --- | --- | --- | --- | --- |
| Resumo campeão, itens individuais, trincas observadas e conjuntos iniciais | Ranked/SR | GET `/lol/{slug}/build/q-data.json` | Ahri: patch 16.19, tier gold, region br, lane middle; Ahri padrão emerald_plus/all; Ashe bottom/diamond_plus no HTML | E1 / probe | **HTTP**. Trincas e conjuntos não são builds completas de seis itens; tabelas `item1` etc. são marginais. |
| Layouts de runas sugeridos e estatísticas individuais | Ranked/SR | Mesmo estado, `summary.*.runes.set` e `runes.stats` | Mesma consulta E1 | E1 | **HTTP**. N/WR do summary coincide com keystone; amostra conjunta dos nove IDs **não comprovada**. Nenhuma WR normalizada de página completa. |
| Itens, combinações, layouts/estatísticas de runas | ARAM | GET `/lol/{slug}/aram/build/q-data.json` | Ahri/Jinx, emerald_plus/all e tier=all | E2 / probe | **HTTP** em ARAM próprio, queue 450; não inferido de SR. Sem lane específico. |
| Variantes de ARAM | Outras variantes | Nenhuma fonte confirmada nos controles/links examinados | Nenhum | Busca de `mayhem`, `aram-mayhem`, `ultimatebook`, `arurf` no SSR não encontrou rotas | **Indisponível**. Não é prova de inexistência de variantes no site. |
| Estatísticas de campeão e distribuições de colocação | Arena | GET `/lol/{slug}/arena/build/q-data.json`, `header` | Ahri/Jinx, emerald_plus/all e tier=all | E3 / probe | **HTTP**. Patch vem da navegação; header não tem patch. `place1..8` preservados sem converter WR em colocação. |
| Itens, prismáticos, combinações e aprimoramentos | Arena | Mesmo estado, `item*`, `prismatic`, `builtItemSet3`, `augment.augment0..4` | Mesma consulta E3 | E3 / probe | **HTTP**. IDs, pick rate e contagens disponíveis. WR de itens/combinações/aprimoramentos **suprimida por política**, inclusive em raw/cache/CLI. Cartinhas futuras usarão pick rate, conforme decisão do usuário. |
| Conjuntos adicionais sob demanda | Ranked/SR | GET `a1.lolalytics.com/mega/`, ep=build-itemset, v=1 | Ahri, patch16.20, lane all, tier emerald_plus, queue ranked, region all | E4 / `--item-sets` | **HTTP**, opt-in. Arrays de contadores preservados sem nomes inferidos e sem calcular ranking/WR. Sem garantia de universo comum às tabelas. |
| Conjuntos adicionais sob demanda | Arena | GET `a1.lolalytics.com/mega/`, ep=arena-itemset, v=1 | Ahri, patch16.20, tier emerald_plus, region all (sem lane/queue) | E5 | **HTTP**, reproduzido pelo agente e coordenador. Não exposto pela biblioteca: contadores permitem derivar WR de itens e sua semântica não foi validada. Estado inicial Arena já é coberto. |
| Filtros por item/keystone, matchups e outros endpoints | Vários | Bundles Qwik, aliases a1/a2/a3 | Forma dos parâmetros observada | Relatório endpoints | **Código**, fora da interface nesta fase. Não afirmar funcionamento só por strings JS. |
| Tradução de IDs para nomes e IDs de importação Riot | Vários | Catálogo agregado do loader e componentes | IDs internos observados | Estado e bundles | **Código/HTTP** para IDs brutos; equivalência entre IDs de augmentos/itens/modos **não presumida**. Enriquecimento/importação não implementados. |

## Reproduções concretas

Todas as fontes abaixo são públicas, sem login/cookies de navegador. Executar da
raiz do checkout. A biblioteca valida a identidade e os filtros resolvidos; uma
página HTTP 200 com filtro ignorado não basta para passar.

```sh
# E1 — resposta Qwik estruturada: _entry aponta loaders em _objs.
curl --fail --max-time 30 'https://lolalytics.com/lol/ahri/build/q-data.json?patch=16.19&tier=gold&region=br&lane=middle' -o /tmp/ahri-qdata.json
python -m lolalytics ahri --patch 16.19 --tier gold --region br --lane middle

# E2/E3 — modos próprios, sem herdar lane de SR.
python -m lolalytics jinx --mode aram --tier all
python -m lolalytics ahri --mode arena --tier all

# E4 — chamada adicional explícita, com counters raw.
python -m lolalytics ahri --patch 16.20 --item-sets

# Reproduzir amostras de dois campeões e três modos, sem cache e sem crawling.
python scripts/lolalytics_probe.py --live
```

Amostras sanitizadas E1/E2/E3, comprovando conteúdo e filtros (valores voláteis):

```json
{"champion":"ahri","cid":103,"mode":"ranked","patch":"16.19","lane":"middle","tier":"gold","region":"br","header":{"n":14291,"wr":50.81},"builtBootSet3_row":["3118_3020_4645",52.14,16.32,2332]}
{"champion":"jinx","mode":"aram","tier":"all","patch":"16.20","status":200}
{"champion":"ahri","mode":"arena","tier":"all","patch":"16.20","augment0_row":[0,null,43.58,24017],"note":"WR redigida"}
```

E4: GET completo abaixo retornou HTTP 200 `application/json` com chaves
`itemSets` e `response.valid=true`. Fragmento real inicial:
`{"itemSets":{"itemSet1":[["3118",9960,3592],["2503",3976,1433], ...]}}`.
Não atribuímos significado aos dois contadores sem confirmação adicional.

```text
https://a1.lolalytics.com/mega/?ep=build-itemset&v=1&patch=16.20&c=ahri&lane=all&tier=emerald_plus&queue=ranked&region=all
```

E5: o mesmo tipo de GET com parâmetros próprios de Arena respondeu 200 JSON,
`itemSets` e `response`. Não guardar nem imprimir contadores de Arena em saídas
comuns, para evitar uma forma indireta de apresentar WR proibida.

```text
https://a1.lolalytics.com/mega/?ep=arena-itemset&v=1&patch=16.20&c=ahri&tier=emerald_plus&region=all
```

## Formato e limites da evidência

`q-data.json` entrega o estado inicial SSR já estruturado, não precisa analisar
HTML ou executar JavaScript em rotina. Não é uma API oficial: o formato interno
Qwik usa referências base36 e pode mudar. `_entry` leva ao mapa de loaders; os
loaders são identificados por estrutura, sem hashes/índices fixos. Strings
resolvidas na tabela são literais; sentinela undefined vira null. Marcadores
não suportados, ciclos, schema inesperado e filtros divergentes geram erro.

Não há paginação nas chamadas observadas por campeão. Não foram descobertos
limites contratuais de tamanho/retorno, truncamentos, cobertura de todos os
patches ou combinações de filtros. A biblioteca tem seus próprios limites,
não faz download de catálogos inteiros nem testa filtros por força bruta.
Nomes de chunks/hashes citados nos relatórios são evidência datada, não contrato.

Fixtures em `tests/fixtures/lolalytics/` são projeções de respostas reais: somente
loaders de navegação e dados agregados, tabelas limitadas a poucas rows, remoção
de campos não necessários e WR Arena redigida. Referências foram reencodificadas
sem mudar valores restantes. `manifest.json` registra filtros, data, hash SHA256
da resposta original e transformações. Não há summoners, tokens ou cookies.
