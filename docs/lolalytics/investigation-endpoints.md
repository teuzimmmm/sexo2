# Investigação dos endpoints LoLalytics (16/10/2026)

Escopo: HTML SSR público e bundles Qwik servidos pela página Ahri, com algumas
requisições GET públicas. Sem login, cookies de sessão, browser automatizado ou
rotas adivinhadas em lote. Evidência temporária em `/tmp/lolalytics-recon`.

## Conclusão prática

A página já entrega os dados iniciais de build no HTML em `<script
type="qwik/json">` (estado Qwik serializado) e há um espelho HTTP desse estado
em `https://lolalytics.com/lol/ahri/build/q-data.json`. Uma requisição GET direta
a esse caminho retornou HTTP 200, `application/json`, 184.683 bytes, com as
chaves `_entry` e `_objs`. O equivalente ARAM também respondeu JSON (5.683
objetos). Essa é a fonte mais simples observada para consumo estruturado sem
acionar carregamento client-side. O formato tem referências de objetos compactadas
(base36), e por isso precisa de decoder Qwik; não é JSON de domínio direto.

A mesma resposta SSR é incorporada no HTML; a inspeção da serialização Qwik
precisa mapear `refs` e decodificar referências de `_objs`/`objs`. No HTML Ahri,
objeto de navegação (índice 2 no `objs` dessa captura) decodifica para `page=build`,
`champion=ahri`, `patch=16.20`, `tier=emerald_plus`, `lane=all`, `mode=ranked`,
`region=all`; `api` aponta `build/front/tierlist/arena` para `a1`, `item` para
a2 e `vs/keystone` para a3. Objeto payload de build tem métricas em `header`
e arrays/objetos de `summary`, `runes`, `items`, `skill*` etc. Conferir
`/tmp/lolalytics-recon/decoded-2.json` e `decoded-9053.json` (saídas locais do
decoder do coordenador).

## Evidência do código público

A página HTML referencia `/build/q-naDMFAHy.js`, `/build/q-BKZ00VYc.js`,
`/build/q-BBUG16gj.js`, bundle graph e vários chunks nomeados no próprio estado
Qwik. O HTML contém links SSR de filtros (`?lane=top`, `?lane=jungle`, etc.) e
inclui os seletores/valores atuais. Logo, a leitura de HTML/estado já cobre SSR;
JS é necessário principalmente para consultas tardias.

Chunk `q-DYLO7hrq.js` define a função Qwik `G`. Para página build, ela monta
`https://${nav.api.build}.lolalytics.com/mega/` e envia query params `ep`, `v`,
`patch`, `c`, `lane`, `tier`, `queue`, `region`; acrescenta `keystone` se
escolhido, ou `item` em outro caso. Para página `vs`, usa o host `nav.api.vs`
e params `ep`, `v`, `patch`, `c`, `lane`, `vs`, `vslane`, `tier`, `queue`.
Depois faz `fetch(url)` e espera JSON. O chunk `q-BiYYLzFX.js` usa essa função
para atualizar os dados de item sets, endpoint lógico `build-itemset`.

A chamada concreta `build-itemset` foi confirmada por HTTP 200 JSON em
`https://a1.lolalytics.com/mega/?ep=build-itemset&v=1&patch=16.20&c=ahri&lane=all&tier=emerald_plus&queue=ranked&region=all`
(resposta salva pelo coordenador em `/tmp/lolalytics-recon/mega-itemset.json`).
Esse é o exemplo para o fluxo SSR de build; `a1/mega/` sem query ainda retorna
`Invalid Endpoint`, que não contradiz a chamada com parâmetros completos.

## Endpoints lazy e métricas de Arena

O bundle SSR `q-D0ekPaYN.js` (página Arena) monta o host `nav.api.arena` e a
query com `ep`, `v`, `patch`, `c`, `tier` e `region`. O handler dos item sets
chama `arena-itemset`. GET público a
`https://a1.lolalytics.com/mega/?ep=arena-itemset&v=1&patch=16.20&c=ahri&tier=emerald_plus&region=all`
retornou HTTP 200 `application/json` (7.401 bytes; chaves `itemSets` e
`response`; `/tmp/lolalytics-recon/arena-itemset-extra.json`). O caminho de Arena
não envia `lane` ou `queue` nesse fetch.

Para runas, a estrutura completa já está em `payload.runes.stats` no estado SSR;
`summary.runes` é o resumo da página de runas e não deve ser confundido com a
tabela completa. O código `q-CI7WF0Dh.js` lê `data.stats[rune+i][side]`, envia
o campo `wr` para o formatador e imprime pick rate com uma casa decimal, além de
contagem de jogos. No caminho examinado não achei fetch lazy de runas: os dados
renderizados vêm do payload SSR e o filtro principal de keystone navega para
outra URL de build.

A página Arena tem tabela de Augments e tabelas de itens com colunas de Win Rate,
Pick Rate e Games. O estado de Arena contém os objetos usados por esses cartões;
o bundle os conecta aos componentes genéricos de dados/itens. O HTML SSR salvo
contém os cabeçalhos, mas a extração textual dessa captura não mostrou valores
individuais das linhas (o que não atesta o que aparece após hidratação). O JSON
`arena-itemset` foi confirmado como resposta estruturada, mas não é evidência de
que qualquer métrica particular de Augment/item seja exibida pela interface.
Não registrar nem propagar valores de win rate de Augments ou itens de Arena;
a avaliação aqui limita-se à presença de estruturas numéricas e à ligação dos
componentes, em linha com a política aplicável.

## Fatos, observações e limites

- **Confirmado por HTTP:** `/lol/ahri/build/q-data.json` dá JSON público; caminho
  equivalente `/lol/ahri/aram/build/q-data.json` também dá JSON. As chamadas
  `build-itemset` e `arena-itemset` com parâmetros documentados acima retornam
  JSON. Isso sugere endpoints de transporte por página e lazy loading, sujeitos
  a mudança.
- **Confirmado por HTTP no SSR:** HTML Ahri contém dados e estado serializado. O
  texto mostra patch 16.20; payload decodificado confirma `header.patch=16.20`.
- **Observado no código Qwik:** filtros patch, tier, lane, region e modo são
  carregados no objeto `nav`; valores extraídos são patch `16.20`, tier
  `emerald_plus`, lane `all`, region `all`, mode `ranked`. URL de lane visível usa
  query `lane=`. `queue` no fetch de build recebe `nav.mode` (string `ranked`,
  `aram` etc.); o fetch de Arena omite lane/queue. `patch` e filtros não são
  numericamente codificados na URL da página SSR.
- **Observado na metadata SSR:** hosts alias `a1/a2/a3` se distribuem entre build,
  item e vs/keystone (vide JSON decodificado). Os endpoints dependem de
  `ep`/versão/chaves específicas da página. Não há garantia de estabilidade
  pública/contratual.
- **Observado no bundle de runas:** leitura de `runes.stats` e repasse de WR ao
  formatador; não foi identificada chamada lazy distinta para carregar essa tabela.
- **Hipótese prática:** em implementações, preferir `q-data.json` para reproduzir
  payload SSR de rota se fixtures validarem que caminho e semântica são estáveis.
  Endpoint lazy deve ser chamado com os parâmetros do bundle e só com schema
  validado; nomes de chunks e rotas internas podem mudar.

## Decodificação Qwik

O `<script type="qwik/json">` contém objeto JSON com `refs`, `ctx`, `objs`,
`subs`. A maioria dos valores string em objetos são referências base36 para
índices de `objs`; `refs` associa identificadores compactos aos símbolos usados
pelo markup. O algoritmo precisa também distinguir strings literais de
referências e tratar wrappers especiais (undefined, datas, mapas/sets, funções).
Método prático: identificar objeto de navegação via propriedades `path/cid/page`
e objeto de dados via `header/summary`; resolver as referências com a tabela
`objs` e validar contra texto SSR (patch, nome do campeão, win rate). Qwik resume
listeners como referências a símbolos e chunks, mas não é necessário executar
JS para extrair o payload SSR.

## Método e contagem

Inspecionados `/tmp/lolalytics-recon/sr.html`, `aram.html` e `arena.html`, além
dos bundles ligados no HTML. Chamadas pontuais: `q-data.json` SR e ARAM; `build-itemset` válido,
`arena-itemset` válido e `/mega/` sem query. Não foi feita varredura de
endpoints nem coleta de credenciais/cookies. A resposta `q-data.json` guardada em
`/tmp/qdata` não deve virar fixture sem sanitização/verificação; é evidência local,
não artifact do repositório.
