# Investigação HTTP: ARAM e Arena

Reproduzido em 2026-10-16 por `urllib.request` padrão do Python (proxy do ambiente), sem sessão de navegador. HTMLs iniciais: `/tmp/lolalytics-recon/aram.html` e `arena.html`. Chamadas diretas adicionais foram limitadas a Ahri e Jinx, às variantes de tier indicadas abaixo. Valores numéricos e exemplos vêm de conteúdo público SSR e estão resumidos; não há credenciais nos artefatos.

## Reproduções

```python
from urllib.request import urlopen
url = "https://lolalytics.com/lol/ahri/aram/build/?tier=all"
with urlopen(url, timeout=20) as response:
    html = response.read().decode("utf-8", "replace")
```

Chamadas verificadas:

| URL | Resultado HTTP | Evidência útil |
| --- | --- | --- |
| `/lol/ahri/aram/build/` | 200 | SSR, Qwik; chave de estado contém `ahri_all_aram_list_emerald_plus_16.20_all__all`; linha de base mostra “Average Emerald+ Win Rate” (52.09%). |
| `/lol/ahri/arena/build/` | 200 | Mesmo tipo de SSR; chave contém `ahri_all_arena_list_emerald_plus_16.20_all__all`; média exibida 52.94%. |
| `/lol/ahri/aram/build/?tier=all` | 200 | A chave muda para `ahri_all_aram_list_all_16.20_all__all` e o texto para “Average All Ranks Win Rate” (50%). |
| `/lol/ahri/arena/build/?tier=all` | 200 | Chave muda para `ahri_all_arena_list_all_16.20_all__all`; “Average All Ranks Win Rate” (50%). |
| `/lol/ahri/aram/build/?tier=bronze` | 404 | Valor arbitrário/incompatível não foi aceito. Não inferir catálogo completo de tiers por esta resposta. |
| `/lol/jinx/aram/build/` | 200 | HTML contém seção “Starting Items” e estatísticas de builds. |
| `/lol/jinx/arena/build/` e `?tier=all` | 200 | SSR acessível, com média e controles de Augments; não contém o rótulo “Starting Items” encontrado em ARAM. |

As páginas de Ahri contêm estado Qwik em `<script type="qwik/json">` e conteúdo SSR relevante. O payload foi decodificado nesta investigação para encontrar os campos e rows abaixo; isso confirma uma fonte estruturada embutida, mas não um contrato estável. A investigação paralela confirmou `q-data.json` para os três modos, consolidado em FONTES.md. `/assets/C_dbWiA9-bundle-graph.json` é infraestrutura Qwik, não a API de estatísticas.

## ARAM

**Confirmado por HTTP/SSR:** os builds são renderizados em `<img>`/texto e incluem rótulos de categorias, taxa de vitória e jogos. Exemplo sanitizado da amostra Ahri: `Starting Items` com ícones de item (CDN `/item64/3802.webp`, `/item64/2031.webp`), `54.97% Win Rate`, `4,013 Games`; item do core build também mostra percentagem e contagem. Isso demonstra que a página expõe estatísticas de categorias de build/combo, não autoriza reconstruir combinações a partir de itens isolados. IDs visíveis nos caminhos de imagem são IDs de item, mas a semântica completa deve ser validada antes de normalização.

O HTML tem controles de tier com `data-id` como `all` (rótulo “Overall”), `emerald`, `platinum`, `gold` e `silver`; a chave SSR padrão usa `emerald_plus`, embora o controle apresente “Emerald”. Só `tier=all` foi comprovado como filtro de query que altera a resposta e o estado SSR. Bronze retornou 404. O seletor de patch mostra `16.20`; o formato de filtro/URL para patch diferente não foi provado. Outros controles visíveis incluem GLOBAL e seletores de rota/posição, sem teste de suas queries.

Não apareceu literal `xx.xx` nas páginas capturadas. Os espaços SSR amostrados carregam valores como `<!--t=22-->52.09` ou `<!--t=22-->50`; não se pode concluir que métricas ocultas estejam ausentes em todos os caminhos/estados. Preservar tais métricas como indisponíveis se não expostas, em conformidade com o escopo do plano.

## Arena

**Confirmado por HTTP/SSR:** a página também é SSR Qwik e expõe taxas de vitória, pick rate e contagens. Correção após inspeção do payload: no HTML/payload inicial de Ahri Arena, o resumo do campeão é **59% win rate**, **5.51% pick rate**, 12,583 partidas (`n`), tier `S+`, rank 2/173. A taxa média geral do filtro (`avgWr`) é **52.94%** e `analysed` é 1,827,880. São campos diferentes e não devem ser confundidos. O payload contém `place1`–`place8` (amostra: 21.6, 19.9, 17.5, 15.7, 13.6, 11.7, 0, 0), e listas de itens/augmentos com IDs e estatísticas.

## Estado Qwik decodificado

Foi extraído `<script type="qwik/json">` e resolvidas referências de strings em base36 para `objs`, preservando strings especiais (`\u0001`) como valores, sem coerção a null e preservando os nulos JSON encontrados. `metadata` vem do objeto global Qwik de índice 2; `root` é o objeto de dados que contém header e arrays/categorias do modo. Os payloads públicos mínimos amostrados estão em `/tmp/lolalytics-recon/modes-aram.json` e `modes-arena.json` (fora do repositório).

Metadados resolvidos de Ahri:

```json
{"path":"/lol/ahri/aram/build/","cid":103,"champion":"ahri","mode":"aram","modeName":"ARAM","patch":"16.20","tier":"emerald_plus","region":"all","status":200}
{"path":"/lol/ahri/arena/build/","cid":103,"champion":"ahri","mode":"arena","modeName":"Arena","patch":"16.20","tier":"emerald_plus","region":"all","status":200}
```

O root ARAM tem `header`, `summary`, `startItem`, `item`, `item1`…`item5` e demais listas SR-like. `header` decodificado inclui `queue=450`, `wr=54.32`, `avgWr=50.29`, `pr=2.16`, `n=5930`; `analysed=548288`, `avgWr=52.09`. Exemplo de linha `summary.pick.items.start`: `{"n":4013,"wr":54.97,"set":[3802,2031],"setUnique":[3802,2031],"count":[1,1]}`. Uma amostra de `item` é `[1052,51.95,277.72,16469,9]`; o HTML e os módulos de renderização dão contexto de estatísticas do item, mas a interpretação de todas as colunas permanece pendente.

O root Arena tem `header`, `augment`, `prismatic`, `startItem`, `items`, `item`, `item1`…`item6`; não tem o objeto `summary` ARAM. `header` decodificado: `{"cid":103,"n":12583,"wr":59,"pr":5.51,"br":4.5,"rank":2,"rankTotal":173,"tier":"S+","place1":21.6,"place2":19.9,"place3":17.5,"place4":15.7,"place5":13.6,"place6":11.7,"place7":0,"place8":0}`. `analysed=1827880`, `avgWr=52.94`. Amostras de rows: `augment.augment0` `[0,null,36.37,4577]`; `augment.augment1` `[65,null,8.3,1044]`; `prismatic` `[447108,null,25.23,3175]`; `item` `[220000,null,571.84,71954,17]`. A célula WR destas amostras foi substituída por null segundo a política Riot. O espaço de IDs depende da categoria: `augment` usa identificadores próprios; `prismatic` contém IDs de itens Arena. Não presumir equivalências com itens SR. Não mapeei IDs numéricos a nomes por endpoint estável, portanto nomes de augmentos continuam indisponíveis sem consultar catálogo separado.

Os rows não têm schema único. O valor inicial de `augment0` tem quatro colunas e o de `item` cinco; listas `summary` usam objetos com chaves nomeadas. Não atribuir as posições de colunas só com base em uma lista: conferir o componente consumidor correspondente. O JS público Arena `q-D0ekPaYN.js` consome os dados como `data.augment`, `data.prismatic`, `data.startItem`, `data.item1`…`item6`; seu helper de itemsets constrói `/mega/?ep=${a}&v=${m}&patch=${patch}&c=${champion}&tier=${tier}&region=${region}` em `${nav.api.arena}.lolalytics.com`. Esse endpoint trata de itemsets sob interação. A investigação paralela reproduziu `arena-itemset` (ver FONTES.md); não é a fonte inicial das tabelas.

Busca por literal `xx.xx` nas duas árvores decodificadas e nos chunks `.js` associados ao HTML Arena não encontrou correspondências. Isto limita a conclusão às páginas/chunks inspecionados, sem provar ausência global do marcador em todas as rotas/estados do site. A sentinel `\u0001` foi mantida na decodificação e aparece em `vsCid`/`vsName` quando matchup está ausente; não deve ser convertida em dado real nem descartada silenciosamente.

Há controles de tier semelhantes aos de ARAM; `?tier=all` muda a chave SSR de `emerald_plus` para `all` e o resumo para “All Ranks”. Não foi provado o filtro de cada tier individual. Em particular, não chamar os tiers de Arena de ranking ou colocação final: a página também exibe categorias/camadas de augmentos e a semântica de muitos rótulos não foi validada.

**Diferença confirmada entre modos:** a rota e a chave SSR incluem `aram` ou `arena`; o resumo/contagens diferem. A amostra ARAM tem seção “Starting Items” explícita; a amostra Arena tem controles de augmentos e não contém esse rótulo. Embora ambas exibam itens, win rate e contagens, não presumir contratos intercambiáveis nem combinar observações de jogos dos modos.

## Estados de evidência e limites

- **Confirmado por HTTP/estado SSR decodificado:** URLs e filtros `tier=all` anteriormente listados; schema de root e valores numéricos de Ahri; metadados com champion id/caminho/modo/patch/tier/region; contagens, win/pick rate e rows de augmento/items expostos no payload.
- **Observado no HTML/código público:** Qwik 1.20, script serializado e chaves compactas; consumidor Arena conhece seções de augments, prismatic, starting/prismatic items e item1…item6; helper faz chamada `/mega/` para itemsets quando necessário. A chamada foi reproduzida na investigação paralela, ver FONTES.md.
- **Hipótese, não implementável como fato:** a chave compacta codifica dimensões de consulta; os controles podem atualizar o estado via chamadas além do endpoint `/mega/`. Não foram testados endpoint de augmentos, traduções dos IDs nem a semântica completa das colunas de cada row.
- **Indisponível nesta investigação:** catálogo dos nomes de augmento por ID, significado formal de cada posição nos arrays, marcador `xx.xx` nas páginas/JS amostrados, regras completas de seleção de partidas, filtros de patch/região/tiers individuais por HTTP e estabilidade histórica. Não houve crawling nem tentativa de contornar bloqueios.

Para reproduzir, fazer GET nas URLs listadas com `urllib.request`, salvar o corpo e procurar as strings `q:key="ahri_all_..."`, `Average ... Win Rate`, `Starting Items`, `Prismatic Augments` e `<script type="qwik/json">`. O conteúdo pode mudar com patch, sessão ou atualização do site; amostras aqui são observações de 2026-10-16, não garantia de contrato.

Atualização da validação integrada: ARAM com `lane=all` explícito retorna 404.
O construtor final omite lane em ARAM/Arena; `tier=emerald_plus&region=all`
retornou 200, com lane=all apenas nos metadados resolvidos.
