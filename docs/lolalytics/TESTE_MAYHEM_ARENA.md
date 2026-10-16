# Investigação Mayhem e Arena

Execução em 2026-10-16, Linux/Python 3.12, checkout `/workspace/sexo2`.
Rede observada pelo ambiente: conectada, política `unrestricted` e `enforced`,
observações atuais; sem credenciais ou identidades configuradas. Foram feitas
19 chamadas HTTP públicas neste agente: 12 na rodada inicial, seis para seguir
o seletor e uma para auditar Arena, sem cookies/autenticação e sem navegador.
Não foram chamadas rotas de Mayhem adivinhadas. O coordenador reproduziu
separadamente Jinx Arena; essa chamada não está incluída neste total.

## Mayhem

**Indisponível nesta investigação; não é prova de inexistência no site.** Ahri e
Jinx não foram consultadas num modo Mayhem porque o seletor público observado
não oferece essa opção e nenhum código/rota Mayhem foi encontrado na cadeia de
imports desse seletor.

Evidência observada:

- `GET https://lolalytics.com/lol/ahri/aram/` → HTTP 404, 33.621 bytes, sem
  ocorrência de `mayhem` no HTML. Esta URL não é a rota estruturada usada pela
  biblioteca.
- `GET https://lolalytics.com/lol/ahri/` → HTTP 404, 44.271 bytes. A resposta
  listou os chunks públicos `/build/q-naDMFAHy.js`, `/build/q-BKZ00VYc.js` e
  `/build/q-BBUG16gj.js`.
- `GET https://lolalytics.com/build/q-BKZ00VYc.js` → HTTP 200, 3.729 bytes;
  não contém `mayhem`, `ARAM Mayhem`, `ultimatebook`, `aram-mayhem` ou `arena`.
- `GET https://lolalytics.com/build/q-BBUG16gj.js` → HTTP 200, 50.709 bytes;
  contém duas ocorrências de `ARAM`, sem os termos de variante acima. As
  ocorrências observadas não identificam uma opção ou rota Mayhem.
- `GET https://lolalytics.com/build/q-naDMFAHy.js` → HTTP 200, 3.100 bytes;
  sem os termos `mayhem`, `aram-mayhem`, `ultimatebook`, `arurf`, `ARAM` ou
  `arena`.
- A inspeção do HTML público ARAM salvo em `/tmp/lolalytics-recon/aram.html`
  revelou o seletor real de modo: `on:click="q-DDxH2iEJ.js#s_G9WOHRQQcUQ[0]"`,
  no elemento cujo texto é `Mode` e `aram`.
- `GET https://lolalytics.com/build/q-DDxH2iEJ.js` → HTTP 200, 1.206 bytes.
  O chunk implementa o seletor e importa `q-BnVhUCu-.js` (rótulo do modo) e
  `q-CIwMmwCO.js` (menu). Não contém `mayhem`, `aram-mayhem`, `ultimatebook`
  ou `arurf`.
- `GET https://lolalytics.com/build/q-BnVhUCu-.js` → HTTP 200, 165 bytes;
  importa dinamicamente `q-BVaZNiOm.js`.
- `GET https://lolalytics.com/build/q-CIwMmwCO.js` → HTTP 200, 165 bytes;
  importa dinamicamente `q-DQoQEOhi.js`.
- `GET https://lolalytics.com/build/q-BVaZNiOm.js` → HTTP 200, 669 bytes.
  Seu mapa de rótulos contém `ranked`, `aram`, `swift`, `arena`, `ultspellbook`
  e `arurf`; não contém Mayhem nem `aram-mayhem`.
- `GET https://lolalytics.com/build/q-DQoQEOhi.js` → HTTP 200, 408 bytes.
  Este menu cria links para `ranked`, `aram`, `swift` e `arena`. Não há Mayhem
  na lista nem os termos `mayhem`, `aram-mayhem`, `ultimatebook` ou `arurf`.

O menu verificado mostra as opções acessíveis nesse seletor público. Os nomes
`arurf` e `ultspellbook` aparecem apenas no mapa de rótulos do chunk de
apresentação, não na lista literal de links do menu. Nenhuma dessas evidências
estabelece uma opção Mayhem.

Ledger das 12 chamadas da rodada inicial, na ordem. Repetições correspondem a
inspeções separadas de HTML e assets; a sequência posterior seguiu o seletor
em seis chamadas para cinco chunks distintos, seguida pela auditoria Arena.

| # | URL | Status |
| ---: | --- | ---: |
| 1 | `https://lolalytics.com/lol/ahri/aram/` | 404 |
| 2 | `https://lolalytics.com/lol/ahri/` | 404 |
| 3 | `https://lolalytics.com/lol/ahri/` | 404 |
| 4 | `https://lolalytics.com/build/q-BKZ00VYc.js` | 200 |
| 5 | `https://lolalytics.com/build/q-BBUG16gj.js` | 200 |
| 6 | `https://lolalytics.com/build/q-naDMFAHy.js` | 200 |
| 7 | `https://lolalytics.com/lol/ahri/build/` | 200 |
| 8 | `https://lolalytics.com/lol/ahri/build/` | 200 |
| 9 | `https://lolalytics.com/lol/ahri/arena/build/q-data.json?tier=emerald_plus&region=all` | 200 |
| 10 | `https://lolalytics.com/lol/jinx/arena/build/q-data.json?tier=emerald_plus&region=all` | 200 |
| 11 | `https://lolalytics.com/lol/ahri/build/` | 200 |
| 12 | `https://lolalytics.com/assets/C_dbWiA9-bundle-graph.js` | 404 |

A chamada 12 usou por engano `.js` para um asset listado como `.json`, portanto
não prova nada sobre o conteúdo do graph. O asset não foi seguido.

Ledger das chamadas 13–19: seis chamadas para seguir o seletor e uma para a
auditoria Arena:

| # | URL | Status |
| ---: | --- | ---: |
| 13 | `https://lolalytics.com/build/q-DDxH2iEJ.js` | 200 |
| 14 | `https://lolalytics.com/build/q-DDxH2iEJ.js` | 200 |
| 15 | `https://lolalytics.com/build/q-BnVhUCu-.js` | 200 |
| 16 | `https://lolalytics.com/build/q-CIwMmwCO.js` | 200 |
| 17 | `https://lolalytics.com/build/q-BVaZNiOm.js` | 200 |
| 18 | `https://lolalytics.com/build/q-DQoQEOhi.js` | 200 |
| 19 | `https://lolalytics.com/lol/ahri/arena/build/q-data.json?tier=emerald_plus&region=all` | 200 |

Na chamada 19, os asserts passaram para 2.259 Records e 2.259 linhas `raw`.
Reprodução Jinx feita separadamente pelo coordenador: HTTP 200, 2.161 Records
e 2.161 linhas `raw`; 996 Records de augment com pick rate e jogos presentes,
WR nula. Ela não faz parte do ledger deste agente.

Reprodução da inspeção da cadeia de imports, sem crawling ou rotas estimadas:

```python
import re
import requests

for chunk in ("q-DDxH2iEJ.js", "q-BnVhUCu-.js", "q-CIwMmwCO.js",
              "q-BVaZNiOm.js", "q-DQoQEOhi.js"):
    url = "https://lolalytics.com/build/" + chunk
    response = requests.get(url, timeout=(5, 15), headers={"User-Agent": "Mozilla/5.0"})
    print(url, response.status_code, len(response.content))
    text = response.text
    print("mode labels:", [word for word in
          ("ranked", "aram", "swift", "arena", "ultspellbook", "arurf", "mayhem")
          if word in text.lower()])
    print("imports:", sorted(set(re.findall(r"q-[A-Za-z0-9_-]+\.js", text))))
```

O modo consultado via biblioteca segue a rota documentada
`/lol/{slug}/arena/build/q-data.json`; nenhuma rota equivalente de Mayhem foi
observada nos links/seletores/chunks verificados. Sem rota real derivada, não
foram tentadas dezenas de caminhos possíveis.

## Arena

Foram executadas duas consultas sem cache, com a biblioteca existente:

```python
from lolalytics import Client, Query

for champion in ("ahri", "jinx"):
    with Client(ttl=0) as client:
        snapshot = client.collect(Query(champion, mode="arena"))
```

Ambas retornaram HTTP 200 e filtros resolvidos `mode=arena`,
`tier=emerald_plus`, `region=all`, `lane=all`, `patch=16.20`. Identidade
resolvida: Ahri, champion ID 103; Jinx, champion ID 222. URLs efetivas:

```text
https://lolalytics.com/lol/ahri/arena/build/q-data.json?tier=emerald_plus&region=all
https://lolalytics.com/lol/jinx/arena/build/q-data.json?tier=emerald_plus&region=all
```

Amostras sanitizadas (IDs são opacos e não foram traduzidos):

| Campeão | Categoria | ID(s) | Pick rate | Jogos |
| --- | --- | --- | ---: | ---: |
| Ahri | item_combination | 223020, 220004, 220004 | 5.56 | 700 |
| Ahri | item_statistics | 223020 | 51.12 | 6.433 |
| Ahri | augment_statistics | 0 | 36.37 | 4.577 |
| Jinx | item_combination | 223006, 223031, 223085 | 9.57 | 1.391 |
| Jinx | item_statistics | 223006 | 75.13 | 10.920 |
| Jinx | augment_statistics | 1328 | 35.29 | 5.130 |

A resposta normalizada incluiu 2.259 Records de Ahri e 2.161 de Jinx. Em ambas,
`item_combination:builtItemSet3`, tabelas de estatísticas de itens e
`augment_statistics` estavam disponíveis; `item_combination:startSet` e
`item_statistics:boots` estavam indisponíveis. O resumo do campeão contém
metadados, jogos e distribuições `place1..8`. A lista de campos do resumo
também inclui métricas gerais de campeão; nenhuma taxa de vitória de item ou
aprimoramento foi impressa neste relatório.

Os Records de item e augment expõem IDs, pick rate e jogos nesta interface. O
`raw` de cada Record é uma lista, mantendo a forma de linha da fonte. A
biblioteca documenta a redação de WR Arena em `raw`, Records e cache. Uma
consulta Ahri adicional (HTTP 200, sem cache) passou asserts para cada Record
de item, combinação e augment: `win_rate is None`, `pick_rate` e `games`
presentes. Os 2.259 Records passaram. Também passaram asserts em 2.259 linhas
`raw` correspondentes nas tabelas de combinações, itens e augments: a célula de
WR está `None`. O script não imprime valores de WR nem grava o corpo upstream:

```python
from lolalytics import Client, Query

with Client(ttl=0) as client:
    d = client.collect(Query("ahri", mode="arena"))
assert d.resolved["mode"] == "arena" and d.resolved["champion"] == "ahri"
assert d.resolved["patch"] and d.resolved["status"] == 200
categories = {"item_combination", "item_statistics", "augment_statistics"}
records = [r for r in d.records if r.category in categories]
for r in records:
    assert r.metrics.get("win_rate") is None
    assert r.metrics.get("pick_rate") is not None
    assert r.metrics.get("games") is not None
    assert len(r.raw) >= 4 and r.raw[1] is None
raw_rows = 0
for key in ("builtItemSet3", "startSet", "startItem", "items", "item",
            "item1", "item2", "item3", "item4", "item5", "item6",
            "popularItem", "winningItem", "prismatic", "boots"):
    for row in d.raw.get(key, []):
        assert row[1] is None
        raw_rows += 1
for table in d.raw.get("augment", {}).values():
    for row in table:
        assert row[1] is None
        raw_rows += 1
assert len(records) == 2259 and raw_rows == 2259
```

Esta auditoria verifica em memória as tabelas conhecidas da resposta
sanitizada; não imprime nem persiste a resposta upstream original.

Limitações observadas: os IDs não foram validados contra catálogo/nome; os
Records vêm de tabelas e slots diferentes, então pick rates não demonstram
combinações ou sinergia entre itens/augments. Os contadores são por tabela e
não devem ser somados como partidas únicas. Augments com ID `0` são preservados
como identificadores opacos. A investigação não validou os filtros de patch
histórico, outras regiões/tiers, nem outras variantes de ARAM.

O coordenador também reproduziu GET do chunk de menu
`https://lolalytics.com/build/q-DQoQEOhi.js`: HTTP 200; a lista literal observada
foi `["ranked","aram","swift","arena"]`. Isso confirma o conteúdo do menu
consultado, sem provar inexistência de Mayhem em outras superfícies do site.
Nenhum código da biblioteca ou CLI foi alterado nesta rodada de testes.
