# Abertura SEXO2: validação (HANDOFF §9)

Implementação: `Pengu Loader/plugins/SEXO2-Startup/index.js` (+ `icone-final.svg`, `oswald.woff2`, `inter.woff2`, copiados byte a byte; sha256 do SVG `ee8a0d41…ebb31`, woff2 idênticos aos originais).
Especificação e referência: `skins/identidade/animacao-abertura/` (HANDOFF.md, index.html). Decisão: D-124 (pendente).

## Como foi validado
- CI, sem navegador: `tests/test_abertura_modelo.cjs` (`node --test`). Modelo numérico puro (pchip, bez, janelas, folga, pen) com as medidas de §4.3.
- Navegador, fora do CI: `python tests/abertura_qa/qa_browser.py <pasta_de_trabalho>`. Chromium completo (o headless-shell não gera quadros), CDP stdlib, `requestAnimationFrame` e `performance.now` trocados por fila e relógio manuais (passo de 1 ms), `https://plugins/…` servido do disco, página que simula `index_loading_div`. O plugin roda sem alteração. 80 verificações, 76 dentro da tolerância.

## Resultado em 1280×720 (tolerâncias: 0,5 px; 0,02; 0,03 s)
| item | obtido | esperado | |
| --- | --- | --- | --- |
| t=0 ícone / S / E / X / O / 2 (x) | 200,93 / 605,73 / 705,40 / 794,76 / 894,86 / 1005,45 | idem | ok (0,00) |
| t=0 scaleX / opacidade | 1 / 1 | 1 / 1 | ok |
| t=2,45 ícone x | 497,64 | 497,64 | ok |
| t=2,55 ícone x; "2" x | 497,85; 708,53 | 497,85; 708,53 | ok |
| t=2,55 quatro letras scaleX / opacidade | 0,500 / 0,000 | 0,500 / 0,00 | ok |
| composição; centro; largura; altura | 497,85…782,15; 640,00; 284,30; 184 | idem | ok |
| ícone y final | 268 | 268 | ok |
| folga ícone–"2" (tinta de §4.3) | 32,18 | 32 | ok |
| instante de absorção S / E / X / O | 1,005 / 1,342 / 1,740 / 2,247 s | 1,01 / 1,34 / 1,74 / 2,25 | ok |
| distância de absorção S / E / X / O (tinta medida neste Chromium) | 37,9 / 35,9 / 26,6 / 28,1 px | 37 / 37 / 26 / 30 | **desvio** +0,9 / −1,1 / +0,6 / −1,9 |
| idem, com a tinta de §4.3 | 37,2 / 35,4 / 25,9 / 27,8 px | 37 / 37 / 26 / 30 | **desvio** E −1,6, O −2,2 |
| menor distância letra visível–ícone | 26,65 px | ≥ 26 | ok |
| nenhuma letra sobrepõe o ícone; tudo dentro do quadro | 200,9…1079,1 | 0…1280 | ok |
| sem reinício após 1,5 s parado | 0 rAF pendentes, posições iguais | — | ok |
| `prefers-reduced-motion` | quadro final direto, 0 rAF, ícone 497,85, centro 640 | — | ok |
| redimensionar 1280→1024→1280 em t=1,0 | X x 670,13 → 670,13; 1024×640 = carga nova (0,00 px) | instante preservado | ok |
| 0,5×, 1,5×, "reproduzir novamente" | não aplicável (sem hooks nem controles em produção) | | n/a |

Desvios reais: (1) a tinta (`actualBoundingBoxLeft`) deste Chromium é 0,4 a 1,1 px maior que a do §4.3 (S 6,4 contra 5,3; "2" 6,3 contra 5,5). Com ela a folga final dá 33,0 px e não 32; as posições (translate) são idênticas. (2) As distâncias de absorção de E e O ficam 1,6 a 2,2 px abaixo da tabela do §9 mesmo com a tinta do §4.3; a fórmula (borda do ícone até `x + l·scaleX` no instante em que a opacidade chega a 0) não reproduz esses dois números, enquanto S e X batem. O critério de projeto (absorção encostada, 26–40 px, sem sobreposição) está atendido. Não alterei o modelo para "acertar" a tabela.

## Outras superfícies (centro horizontal e vertical, tolerância 0,5 px)
| viewport | centro x final | esperado | centro y do ícone | tudo no quadro |
| --- | --- | --- | --- | --- |
| 900×600 | 450,00 | 450 | 300,00 | 141,3…758,7 |
| 1024×640 | 512,00 | 512 | 320,00 | 160,7…863,3 |
| 1440×900 | 720,00 | 720 | 450,00 | 226,0…1214,0 |
| 1600×900 | 800,00 | 800 | 450,00 | 251,2…1348,8 |

## Ciclo de vida no cliente
Loading removido no meio da animação: o overlay segue até o fim e só então sai. Loading que aparece depois da carga: o overlay monta. Fonte indisponível (404): a cena aparece após 1,6 s com a métrica de reserva. Loading ainda presente no fim: o quadro final fica parado.

## Adaptações ao cliente
(a) Overlay `fixed; inset: 0; z-index: 2147483000`, montado quando existe `div[id^="index_loading_div"]`, `pointer-events: none`. (b) Quadro final parado enquanto o loading do cliente existir; removido sem animação quando o cliente o remove, nunca antes do fim. (c) Assets por `https://plugins/SEXO2-Startup/…` (formato dos demais plugins, ex. ROSE-Jade); entram no pacote porque `SEXO2.spec` empacota a pasta `Pengu Loader` inteira. (d) `@font-face` com os woff2 copiados, `font-display: block`; medição só após `document.fonts.load('600 100px Oswald')` (limite de 1,6 s). (e) Sem controles, `?t=` nem `?speed=`. (f) O fundo `#0d0e10` vale só dentro do overlay e no div de loading; o PNG e o texto "SEXO2" antigos foram removidos.
Não verificado: o cliente real (carregamento de fonte por `https://plugins/` e CORS). Exige teste em cliente real.
