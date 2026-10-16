# Relação entre runas e itemização — teste dirigido

Reproduzido pelo coordenador em 2026-10-16 com duas chamadas HTTP200 de
q-data.json e inspeção de JavaScript público. Sem alterar biblioteca ou CLI.

## Resultado

A aba Highest Win/Most Common apenas escolhe localmente `summary.win` ou
`summary.pick`. O chunk `q-BHJIqklk.js`, obtido por GET HTTP200 em
https://lolalytics.com/build/q-BHJIqklk.js, muda `e.value` entre win/pick e
passa `t.summary[e.value]` ao componente. Esse handler não acrescenta filtro
de runas e não faz fetch. Isso comprova a seleção local do resumo, não o
algoritmo interno usado pelo servidor para escolher cada sugestão.

Na consulta sem filtro (`nav.keystone=-1`), o core Highest Win de Ahri coincide
exatamente com a linha da tabela geral `builtBootSet3` para os mesmos IDs:
`["2503_3158_3100",56.8,4.5,7505]`. Assim, os itens dessa amostra usam as
métricas da combinação geral; não há evidência de condicionamento aos nove IDs
de runas mostrados ao lado. Nenhuma taxa conjunta runas+itens foi encontrada.

Existe um filtro público explícito por **keystone**, observado no renderer de
runas `q-CI7WF0Dh.js`: o link é construído com `keystone:e.rune`. Reproduzimos
esse parâmetro por HTTP, sem deduzi-lo apenas do bundle. A resposta resolveu
`nav.keystone=8992` e trouxe outro universo de jogos e outras sugestões de itens.
Isso é evidência de dados condicionados à **runa principal**, não à página de
nove escolhas inteira. A semântica exata do algoritmo de recomendação no servidor
continua não documentada.

## Amostras públicas sanitizadas

### Sem filtro de runa

```json
{
  "url": "https://lolalytics.com/lol/ahri/build/q-data.json?lane=middle&tier=emerald_plus&region=all",
  "filters": {
    "champion": "ahri",
    "patch": "16.20",
    "lane": "middle",
    "mode": "ranked",
    "tier": "emerald_plus",
    "region": "all",
    "keystone": -1
  },
  "champion_games": 166721,
  "summary": {
    "win": {
      "runes": {
        "wr": 53.42,
        "n": 20160,
        "page": {
          "pri": 2,
          "sec": 3
        },
        "set": {
          "pri": [
            8992,
            8226,
            8210,
            8237
          ],
          "sec": [
            8451,
            8444
          ],
          "mod": [
            5008,
            5010,
            5011
          ]
        }
      },
      "core": {
        "set": [
          2503,
          3158,
          3100
        ],
        "wr": 56.8,
        "n": 7505
      }
    },
    "pick": {
      "runes": {
        "wr": 52.8,
        "n": 143965,
        "page": {
          "pri": 1,
          "sec": 2
        },
        "set": {
          "pri": [
            8112,
            8139,
            8140,
            8106
          ],
          "sec": [
            8226,
            8210
          ],
          "mod": [
            5005,
            5008,
            5001
          ]
        }
      },
      "core": {
        "set": [
          3118,
          3020,
          4645
        ],
        "wr": 53.64,
        "n": 29091
      }
    }
  }
}
```

### Com filtro de keystone

```json
{
  "url": "https://lolalytics.com/lol/ahri/build/q-data.json?lane=middle&tier=emerald_plus&region=all&keystone=8992",
  "filters": {
    "champion": "ahri",
    "patch": "16.20",
    "lane": "middle",
    "mode": "ranked",
    "tier": "emerald_plus",
    "region": "all",
    "keystone": 8992
  },
  "champion_games": 19714,
  "summary": {
    "win": {
      "runes": {
        "wr": 53.23,
        "n": 19714,
        "page": {
          "pri": 2,
          "sec": 3
        },
        "set": {
          "pri": [
            8992,
            8226,
            8210,
            8237
          ],
          "sec": [
            8473,
            8451
          ],
          "mod": [
            5008,
            5010,
            5011
          ]
        }
      },
      "core": {
        "set": [
          3118,
          3020,
          3100
        ],
        "wr": 59.33,
        "n": 1077
      }
    },
    "pick": {
      "runes": {
        "wr": 53.23,
        "n": 19714,
        "page": {
          "pri": 2,
          "sec": 1
        },
        "set": {
          "pri": [
            8992,
            8226,
            8210,
            8237
          ],
          "sec": [
            8106,
            8139
          ],
          "mod": [
            5005,
            5008,
            5001
          ]
        }
      },
      "core": {
        "set": [
          3118,
          3020,
          4645
        ],
        "wr": 52.67,
        "n": 1927
      }
    }
  }
}
```

Os valores são voláteis e as respostas podem ter instantes/cache upstream
diferentes; não usar a diferença entre contagens para deduzir perdas de jogos
ou uma relação exata entre todos os filtros. A confirmação do filtro depende
da metadata e da resposta estruturada, não só dessa diferença numérica.

## Reprodução

Executar na raiz do checkout:

```python
import requests
from lolalytics.decoding import decode_page

with requests.Session() as session:
    for suffix in ("", "&keystone=8992"):
        url = ("https://lolalytics.com/lol/ahri/build/q-data.json"
               "?lane=middle&tier=emerald_plus&region=all" + suffix)
        response = session.get(url, timeout=(5, 20))
        response.raise_for_status()
        nav, payload = decode_page(response.content)
        print(nav["champion"], nav["mode"], nav["patch"], nav["keystone"])
        print(payload["header"]["n"])
        for selection in ("win", "pick"):
            print(selection, payload["summary"][selection]["items"]["core"])
```

Este teste usa transporte de investigação. `Query` e a CLI da biblioteca
atualmente **não expõem keystone**. Acrescentar o filtro exige contrato de
consulta/cache, validação do filtro resolvido e testes; não está implicitamente
implementado por existir na fonte. Não foi encontrado filtro por página completa
de nove runas nesta investigação, nem comprovada coocorrência dessa página com
a itemização. Importação no LoL permanece fora da fase 1.
