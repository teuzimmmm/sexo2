# Investigação de matchup e builds

Reproduzido em 2026-10-16 com até treze GETs no total, sem sessão de navegador.
As respostas completas bem-sucedidas ficaram em `/tmp/lolalytics-matchups/`.

## Evidência

O HTML público de `https://lolalytics.com/lol/ahri/build/` respondeu 200. O
conteúdo SSR tem links de matchup explícitos, por exemplo
`/lol/ahri/vs/annie/build/?lane=middle&vslane=middle` e
`/lol/ahri/vs/ryze/build/?lane=middle&vslane=middle`. Usei esses nomes e lanes
extraídos do HTML para consultar os dados estruturados q-data. Ambos retornaram
HTTP 200 e queue 420:

| Matchup | URL q-data sem keystone | nav resolvido | header.n |
| --- | --- | --- | ---: |
| Ahri vs Annie | `https://lolalytics.com/lol/ahri/vs/annie/build/q-data.json?lane=middle&vslane=middle` | `vsName=Annie`, `vsCid=1`, patch `16.20`, lane/vsLane `middle`, keystone `-1`, tier `emerald_plus`, region `all` | 1.852 |
| Ahri vs Ryze | `https://lolalytics.com/lol/ahri/vs/ryze/build/q-data.json?lane=middle&vslane=middle` | `vsName=Ryze`, `vsCid=13`, patch `16.20`, lane/vsLane `middle`, keystone `-1`, tier `emerald_plus`, region `all` | 1.595 |

As duas respostas incluem `summary.win` e `summary.pick`, com `runes` e
`items`. O bloco de runas tem `wr`, `n`, `page` e `set`; os itens têm `start`,
`item1` a `item6`, com contagens e WR. Não há `summary.*.core` nesses exemplos:
`items.item1..item3` são posições individuais e `item4..item6` são listas de
alternativas. Portanto, a presença de runas e itens no mesmo payload não prova
uma amostra conjunta runas+itens nem fornece o bloco `core` que o contrato atual
de BuildPage requer. Exemplos de n internos: Ahri vs Annie `summary.win.runes.n`
1.606 e `summary.win.items.start.n` 1.842; Ahri vs Ryze, respectivamente 212 e
1.585. Esses contadores têm universos diferentes.

## Filtros aceitos no matchup

Uma verificação isolada em Ahri vs Annie confirmou que os filtros gerais de
ranked não são intercambiáveis com os parâmetros da rota `/vs/`:

| Query string | HTTP | Resultado |
| --- | ---: | --- |
| `lane=middle&vslane=middle&tier=emerald_plus` | 200 | `nav.tier=emerald_plus`, `nav.region=all`, patch `16.20`, `header.n=1852`, queue 420 |
| `lane=middle&vslane=middle&region=all` | 404 | região explícita rejeitada |
| `lane=middle&vslane=middle&patch=16.20` | 200 | patch `16.20`, `nav.tier=emerald_plus`, `nav.region=all`, `header.n=1852`, queue 420 |

Omitir `region` é necessário para essa rota observada; `tier` e `patch` foram
aceitos isoladamente. A amostra não confirma se todos os valores de tier são
aceitos, e cobre somente Ahri vs Annie em middle.

## Teste de keystone

Repeti as duas rotas com `keystone=8992` e com os parâmetros explícitos
`patch=16.20`, `lane=middle`, `vslane=middle`. As quatro requisições retornaram
HTTP 404. Logo, a rota de matchup não confirmou o filtro de keystone testado;
não se deve devolver uma resposta geral como se estivesse filtrada.

Para distinguir um keystone sem amostra de um filtro incompatível, testei também
`keystone=8112` (outra keystone observada nas sugestões de Ahri) nas mesmas duas
rotas, com `lane=middle&vslane=middle` e sem patch explícito. Ambas retornaram
HTTP 404 também. No total, foram seis consultas q-data filtradas por keystone:
duas para cada uma das duas keystones, todas 404. Não há resposta filtrada a
guardar nem evidência de que uma keystone alternativa resolva a limitação.

O parâmetro `keystone` foi confirmado por HTTP nas páginas regulares de campeão
e seu uso no renderer de runas está registrado em [RUNAS_E_ITENS.md](RUNAS_E_ITENS.md).
O HTML atual de Ahri mostra links `/vs/` com `lane` e `vslane`, mas não links de
matchup com keystone. O chunk atual `q-C-uYeFs0.js` só renderiza o bloco de runas
inspecionado e não contém `keystone`, `/vs/` ou `vslane`. Assim, a composição
`/vs/.../q-data.json?...&keystone=...` foi um teste negativo, não um contrato
derivado de um link atual do renderer.

## Capturas e limite

Capturas HTTP 200 decodificáveis: `ahri-build.html`,
`ahri-vs-annie-knone.json`, `ahri-vs-ryze-knone.json` e `rune-renderer.js` em
`/tmp/lolalytics-matchups/`. Os testes isolados de tier e patch retornaram 200;
registramos seus metadados nesta nota, sem gravar respostas adicionais. As
rotas filtradas por keystone e a rota com `region=all` falharam com HTTP 404 e
não produziram captura JSON. A investigação cobriu somente ranked, uma lane e
dois oponentes; não confirmou ARAM, outras lanes, regiões, nem patch passado.
