# QA — laboratório de overlays (frente overlays)

Escopo: `index.html` (rascunho anterior corrigido em uma rodada, sem reconstruir o overlay aprovado). Ferramenta: Firefox 64-bit headless via Marionette (sem Playwright/Chromium/Node nesta máquina; Claude_Browser não executa script em file://). Teclas Tab/Shift+Tab/Enter/Espaço/Escape são reais (WebDriver Actions). Script: `evidencias/teste-interacao.py` (+ `mn.py`); saída bruta: `evidencias/resultado-teste.txt` (47 PASS, 0 FAIL na rechecagem final).

## Cálculos (O02) — ouro investido em itens por rota; diferença = aliado − adversário
Entradas fictícias (adversário à esquerda / aliado à direita no cenário da imagem):
| Rota | Adversário | Aliado | Esperado | Obtido |
|---|---|---|---|---|
| Darius × Garen | 9350 | 9010 | -340 | -340 |
| Lee Sin × Vi | 8230 | 9000 | +770 | +770 |
| Zed × Ahri | 10750 | 10110 | -640 | -640 |
| Kai'Sa × Jinx | 11200 | 11740 | +540 | +540 |
| Lulu × Thresh | 6320 | 5780 | -540 | -540 |
| Total | 45850 | 45640 | -210 | -210 (texto "-210"; "ITENS" e "ouro" removidos a pedido do usuário) |

Outros cenários (obtido = esperado): vantagem (+300,+500,+200,+650,+420) total +2070; desvantagem simétrica -2070; empate: 0 em todas e "ITENS · empate (0 ouro)", sem barras. Preço indisponível (Zed×Ahri sem preço do aliado): d[2]=null, total=null; a rota mostra "—" (não 0), total "TOTAL INDISPONÍVEL" nos três modos, totais de equipe do Blitz também omitidos (sem total parcial).
Observação: os números 16 e 8 do topo vêm da imagem aprovada; são fixos, fictícios, sem cálculo e seu significado não está definido no pacote. Na imagem 16 (azul) fica sobre o lado dos adversários; preservado como aprovado.

## Critérios
| # | Resultado | Evidência |
|---|---|---|
| O01 | PASS (com desvio de enquadramento registrado) | B é o modo inicial (sem hash -> #b). Lado a lado: `evidencias/b-lado-a-lado-1280.png` (imagem aprovada à esquerda, render recortado ao mesmo enquadramento à direita). Mesma composição, cores, Inter Bold, barras (-340=28 unid., +770 e -640 = limite 58). Desvios: o render do laboratório mostra o palco 16:9 inteiro na página, a imagem é um recorte (~1,16x); comparação feita com recorte equivalente do viewBox ("76 21 1167 654") — ajuste de enquadramento estimado a olho, não calibrado por pixel. |
| O02 | PASS | tabela acima; `window.sexo2Calc` e texto na tela conferidos no teste. |
| O03 | PASS | vantagem/desvantagem/empate; equipe à direita/esquerda: nomes, ícones, KDA espelham; vantagem vai para o lado da sua equipe (barra, seta ◂/▸ no A, seta do losango no Blitz); indisponível não vira zero. Capturas `*-equipe-esquerda`, `*-indisponivel`, `b-empate`, `b-vantagem`, `b-desvantagem`. |
| O04 | PASS | botões "Estudo · …" e etiqueta "ESTUDO, não aprovado"; B etiquetado "Aprovado"; #a/#b/#blitz por clique, abertura direta, voltar/avançar. Blitz mantém losango, seta, diferença absoluta abaixo, moedas e totais sem separadores (45850/45640). Referência `blitz-reference.webp` não alterada (mtime original); sem alegação de equivalência pixel a pixel. |
| O05 | PASS | `document.fonts`: Inter e Oswald status loaded (woff2 locais); h1/rótulos Oswald, corpo Inter, texto do overlay B em Inter por padrão. Sem serifa nem fonte remota. Seletor "Fonte" ainda oferece Oswald e Arial como comparação do próprio overlay (herdado do rascunho; Arial é fallback técnico e opção de estudo — ver limitações). |
| O06 | PASS | 1280×720: `b-1280x720.png`, `blitz-1280x720.png`, `a-1280x720.png`. Nomes/KDA/itens sem obstrução; controles legíveis. Tab real percorre 12 controles na ordem; foco visível 2px #ececec (`foco-teclado-1280x720.png`); Espaço no checkbox e Escape ocultam. A prévia agora ocupa a largura (palco 16:9), a parte inferior exige rolagem da página em 720 de altura (palco inteiro rola). |
| O07 | PASS | file:// (Firefox), imagens/fontes locais, links A/B relativos presentes (destinos A/B existem no worktree; abertura deles não foi testada nesta frente); cenário/lado/fonte/visibilidade em localStorage (try/catch) e restaurados ao recarregar; ocultar e reexibir mantém preferências. Modo fica no hash. |
| O08 | PASS | este QA, capturas em `evidencias/`, defeitos e rechecagem abaixo. Placar reconstituído (dados fictícios); sem validação no Windows, em partida real ou de FPS. |

Capturas: 1280×720 (b, blitz, a, indisponível B/Blitz, empate, vantagem, desvantagem, equipe à esquerda B/Blitz, oculto, foco), 820×560 (`b-820x560.png`), 452×492 (`b-452x492.png`).

## Defeitos do rascunho e correção (uma rodada)
1. Modo inicial era Blitz -> agora B (aprovado); hash vazio vira #b. Corrigido.
2. Chrome da página usava azul (botões, links, foco) e fundo azulado -> neutros #0d0e10/#15171a/#22252a/#2a2d32/#ececec; azul só dentro do overlay (exceção aprovada).
3. Preço ausente zerava só a linha e mantinha total parcial (B/A) -> linha "—" e total indisponível nos 3 modos.
4. Sem controle de equipe esquerda/direita, vantagem/desvantagem e empate sem cenário dedicado -> adicionados.
5. Preferências perdiam-se (sem persistência) -> localStorage; Esc oculta.
6. Palco de 420px reduzia texto a ~8px -> palco 16:9 em largura total; em telas estreitas rola dentro do palco (min 760px).
7. Blitz com total ao espelhar: números transbordavam a faixa -> reposicionados.
8. Faltava comparação lado a lado e rótulo "aprovado/estudo".
Falhas do meu primeiro roteiro de teste (valores esperados errados, foco residual) foram corrigidas no script; nenhuma falha do produto restante na rechecagem (47/47).

## Limitações
- Sem Chromium/Playwright; só Firefox. Sem validação no Windows, partida, FPS ou posição no cliente real.
- A 452×492 o palco rola horizontalmente dentro de si (texto legível, não cabe inteiro).
- Seletor de fonte mantém Oswald/Arial para comparação; a regra "só Oswald/Inter" vale para a UI, não revalidei se o produto quer remover Arial do estudo.
- 16/8 do topo e a coloração (azul sobre os adversários) vêm da imagem e não foram reinterpretados.
- Links A/B só verificados como presentes/relativos.
