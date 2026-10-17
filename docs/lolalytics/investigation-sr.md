# LoLalytics SR: investigação HTTP

Data da coleta: 2026-10-16. O objetivo foi descobrir se a página SR entrega combinações completas no HTML e como distinguir essas combinações de estatísticas marginais. Todas as requisições abaixo são GET públicos sem cookies ou credenciais. As amostras abaixo são dados agregados de jogo e não incluem identificadores pessoais.

## Requisições reproduzidas

Com Python padrão, `urllib` (não foi preciso instalar `requests`):

```sh
python - <<'PY'
from urllib.request import urlopen
for path in (
    '/lol/ahri/build/?lane=middle&tier=emerald_plus',
    '/lol/ashe/build/?lane=bottom&tier=diamond_plus',
):
    url = 'https://lolalytics.com' + path
    response = urlopen(url, timeout=30)
    body = response.read()
    print(response.status, response.headers.get('Content-Type'), len(body), response.url)
    open('/tmp/' + path.split('/')[2] + '.html', 'wb').write(body)
PY
```

As duas respostas foram HTTP 200 `text/html; charset=utf-8`, com HTML SSR Qwik (container `q:render="ssr"`, versão 1.20.0) e um bloco `<script type="qwik/json">`. Os tamanhos observados foram aproximadamente 623 KB para Ahri e 668 KB para Ashe; tamanho pode variar com os dados servidos. A página base de Ahri também respondeu 200. `?lane=middle&tier=emerald_plus` produziu chave de página `ahri_middle_ranked_list_emerald_plus_16.20_all__all`; para Ashe, `?lane=bottom&tier=diamond_plus` produziu `ashe_bottom_ranked_list_diamond_plus_16.20_all__all`. Títulos/canonical e o texto “Average Emerald+ Win Rate” / “Average Diamond+ Win Rate” refletiram os filtros. `lane=top&tier=all&patch=16.20` também respondeu 200; `patch` não persistiu no canonical observado e o patch selecionado continuou 16.20. Isso confirma o comportamento desta coleta, não a validade futura de todos os parâmetros.

Uma amostra de estado Qwik foi decodificada durante a investigação: o contexto de navegação contém `champion`, `lane`, `mode`, `tier`, `patch` e `key`. Na amostra base de Ahri, os valores eram `champion="ahri"`, `lane="all"`, `mode="ranked"`, `tier="emerald_plus"`, `patch="16.20"`; nas páginas com filtros, as chaves SSR no HTML refletiram os lanes consultados. O payload principal contém referências compactas em base 36, com tabelas `objs`, `refs`, `ctx` e `subs`. Uma amostra raiz decodificada de Ahri tinha `header`, `summary`, `graph`, `runes`, `itemSets`, `builtBootSet3`, `item1`…`item6`, entre outras propriedades. Arquivos de trabalho decodificados ficam em `/tmp/lolalytics-recon/decoded-*.json`, não são fixtures para incorporar sem nova sanitização/revisão.

## Combinações de itens e runas

No objeto `summary`, as ramificações `pick` e `win` contêm campos de runas e itens. A evidência não dá o mesmo nível de certeza semântica para os dois tipos:

- `summary.pick.runes.set` e `summary.win.runes.set` contêm arrays `pri`, `sec` e `mod` de IDs de runas, além de `page`, `n` e `wr`. O site chama esses modos “Most Picked Rune Page” e “Highest Win Rune Page”, mas a ocorrência conjunta dos nove IDs não foi comprovada. Na amostra Ahri, o `n` da sugestão `pick` (`142583`) coincide exatamente com a estatística individual do keystone 8112 em `runes.stats`; o `n` da sugestão `win` (`19982`) coincide com a estatística individual do keystone 8992. O WR coincide após arredondamento para uma casa decimal (`52.78` vs. `52.8`; `53.38` vs. `53.4`). Os outros IDs não têm uma contagem de página conjunta correspondente no objeto analisado. Portanto, preservar esses arrays como layout de runas apresentado pelo site, com `n/wr` brutos e sem declarar que representam nove runas observadas juntas. Exemplo `pick`: `pri=[8112,8139,8140,8106]`, `sec=[8226,8210]`, `mod=[5005,5008,5001]`; exemplo `win`: `pri=[8992,8226,8210,8237]`, `sec=[8451,8444]`, `mod=[5008,5010,5011]`. IDs foram preservados do payload.
- `summary.pick.items.core` e `summary.win.items.core` são sequências completas de três itens, com `set`, `n` e `wr`. Exemplo Ahri `pick`: `[3118,3020,4645]`, `n=28815`, `wr=53.52`; `win`: `[2503,3158,3100]`, `n=7429`, `wr=56.97`.
- `builtBootSet3` fornece outra tabela de trincas ordenadas, com campos posicionais `["item_item_item", wr, pickRate, n]`. Exemplo: `["3118_3020_4645",53.52,17.45,28815]`. A chave de três itens é uma combinação observada e preserva a ordem do site.
- `itemSets.itemBootSet3` agrega conjuntos de três itens/boots; chaves como `3118_3020_4645` e valores `[10401,4770]` foram observados. O significado exato dos dois números não foi confirmado nesta investigação, então não devem ser nomeados como jogos/vitórias sem validação.

Em contraste, `runes.stats` contém métricas individuais por ID e posição (linhas `[pickRate, winRate, count]`; as duas posições de uma linha podem representar usos primários/secundários, conforme o slot). Não traz uma tabela de coocorrência dos nove IDs e não basta para reconstruir uma página realmente usada em conjunto. `item1`, `item2`, `item3`, `item4` etc. são distribuições de itens individuais por slot/etapa; não estabelecem que um item da lista em `item4` foi usado com um item arbitrário de `item5` e `item6`. Em particular, os campos `summary.*.items.item4`, `item5`, `item6` também são listas marginais de candidatos, não builds de fim de jogo alinhadas entre si. Não combinar essas listas por produto cartesiano.

### Inspeção dos componentes públicos de runas

As páginas referenciaram módulos JS públicos, obtidos por GET em `/build/q-DFEAQw00.js`, `/build/q-CI7WF0Dh.js` e `/build/q-KJiKbZdF.js`. O primeiro oferece seletores “Overview”, “Highest Win Rune Page” e “Most Picked Rune Page”, percorre uma estrutura fixa de opções (`y.structure`) e passa `page`, `summary` e `data` ao renderer. O terceiro fornece essa estrutura de IDs organizada por árvore e linha.

Reprodução direta dos componentes examinados:

```sh
python - <<'PY'
from urllib.request import urlopen
for name in ('q-DFEAQw00.js', 'q-CI7WF0Dh.js', 'q-KJiKbZdF.js'):
    url = 'https://lolalytics.com/build/' + name
    response = urlopen(url, timeout=30)
    body = response.read()
    print(response.status, len(body), response.url)
    open('/tmp/' + name, 'wb').write(body)
PY
```

No renderer (`q-CI7WF0Dh.js`), a seleção visual é calculada verificando se cada ID aparece em `summary[page].runes.set.pri/sec`, ou se corresponde ao valor em `set.mod`. Separadamente, win rate, pick rate e games de cada ícone são lidos de `data.stats[rune + suffix][slot]`. A implementação não consulta uma contagem conjunta dos IDs selecionados para renderizar esses números. Na amostra Ahri, `runes.stats["8112"][0]` é `[86.3,52.8,142583]`, enquanto a entrada corresponde exatamente ao `n=142583` e `wr=52.78` de `summary.pick.runes`; `runes.stats["8992"][0]` é `[12.1,53.4,19982]`, alinhada ao `n=19982` e `wr=53.38` de `summary.win.runes` (diferença de arredondamento no WR). Para outras runas selecionadas, as contagens variam, como esperado para a métrica por opção/posição. Isso sustenta que o número geral acompanha o keystone escolhido, mas não prova como o servidor montou o restante do layout nem que os nove IDs ocorreram juntos. A interpretação segura é “layout recomendado/selecionado pela página com estatísticas marginais”, não “página de nove runas com coocorrência comprovada”.

## Formato de estado e interpretação

O estado em `<script type="qwik/json">` é JSON, mas os registros Qwik referenciam outros elementos de `objs` por tokens compactos base 36. Assim, não basta fazer `json.loads` e procurar as chaves sem resolver referências. O processo simples e robusto para uma implementação é:

1. Obter o HTML por GET e analisar o documento com parser HTML, localizando o script pelo atributo `type="qwik/json"` (evitar regex dependente de minificação para extrair o bloco).
2. Fazer parse JSON e validar presença/tipos de `objs` e `refs`; tratar ausência como resposta sem estado reconhecido, sem fallback para combinações inferidas do HTML.
3. Reproduzir a regra de referências do serializador Qwik usado no payload: strings em `objs` representam índices compactados em base 36 e objetos/listas guardam essas referências. Resolver recursivamente com memoização e detecção de ciclos; preservar valores primitivos, arrays e objetos. Confirmar versão/formato em fixtures de cada coleta.
4. Identificar o objeto de dados por estrutura (objeto com `header` e `summary`) em vez de assumir índice fixo, que variou entre páginas. Validar `header.patch`, campeão/lane e `summary` antes de consumir.
5. Extrair `runes.set` como layout nomeado pelo site, preservando a incerteza de coocorrência e os campos brutos; não tratá-lo como combinação observada sem uma fonte de contagem conjunta. Itens em `items.core.set` e `builtBootSet3` têm sequências e amostras associadas explícitas no payload. Manter IDs numéricos e métricas com a proveniência e filtros correspondentes.

A regra detalhada de escaping e dos marcadores internos do Qwik pode mudar entre releases. A recomendação confirmada é parsear o script JSON e resolver referências por base 36, mas uma biblioteca precisa de fixtures versionadas e validações estruturais antes de tratar isso como contrato estável. Na investigação paralela, `q-data.json` foi confirmado como fonte estruturada dos mesmos dados; ver FONTES.md e investigation-endpoints.md. A implementação final usa esse JSON e não extrai HTML.

## Limites da evidência

Confirmado por HTTP: respostas SSR 200 para as rotas e filtros citados, presença do estado Qwik no HTML e os campos/valores acima em uma amostra Ahri decodificada. A página também foi conferida para Ashe e confirmou mudança de lane/tier/chave; ainda não foi decodificado aqui o resumo de builds de Ashe. IDs de runas e itens foram preservados como IDs do payload, sem enriquecer com nomes externos.

Observação de código/serialização: referências base 36, `objs` e a necessidade de atravessar tabelas vêm do formato Qwik detectado na resposta e do decoder Qwik 1.20.0 consultado localmente. Isso não é garantia de compatibilidade futura do site.

Não confirmado: semântica dos pares em `itemSets.itemBootSet3`; se `n` em cada seção mantém sempre o mesmo universo/amostragem; se páginas com outras combinações de filtros têm os mesmos caminhos; nem estabilidade de campos internos. Os arquivos `/tmp/lolalytics-recon/*` são scratch locais e podem conter respostas completas; este relatório contém apenas exemplos agregados curtos.
