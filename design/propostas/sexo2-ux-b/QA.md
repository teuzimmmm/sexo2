# QA da proposta B (atividades dentro do client)

Escopo: prototipo HTML estatico, dados ficticios, sem cliente do LoL, sem validacao Windows/producao, sem teste de usabilidade. Nada aqui aprova a proposta. A cena do client (nav dourada, lobby, champ select, partida) e uma simulacao propria do enquadramento, nao a replica.

## Enquadramento (rodada 2)
- Palco 1280x720 simulando o client: barra de navegacao, cena de fundo e botao SEXO2 no cabecalho. Sem cabecalho/rodape de app.
- Faixa "Simulacao, fora do produto" com Cliente / Selecao / Partida (alterna o momento do client), estado da ultima acao e links para A e Overlays.
- Momento 1 (Cliente/lobby): SEXO2 do cabecalho abre o workspace por atividade 820x560 sobre o client (Preparar partida, Personalizar colecao, Resolver problema). Fecha com Esc ou Fechar; foco volta ao botao.
- Momento 2 (Selecao): cena de champ select (ids #champ-scene, #bottom, #confirm-champ); botao SEXO2 inferior abre o assistente 452x492 ancorado (D-017). Em jogo: cena de partida com placeholder de overlay (link ao laboratorio de overlays; nao redesenhado).
- Preparar partida: Antes da fila = lobby do client, Na selecao = champ select, Em jogo = partida; a etapa do hub e a faixa de simulacao controlam o mesmo estado.
- Bravura corrigida conforme ARENA_BRAVURA.md: so no Arena; confirmar Bravura na selecao (campeao -3) nao revela nada; o jogo revela em partida; o app detecta o campeao, escolhe a skin (favoritas, senao aleatoria, exclusoes respeitadas), encerra o executavel da partida uma vez e reconecta (interrupcao de carregamento); guard impede repetir; limite de 75 s mencionado. Sem estatisticas, desafios ou itens; aprimoramentos ficam em Configuracoes > Overlays.

## Como foi testado
- Chromium headless (chrome-headless-shell do cache Playwright) via CDP com cliente stdlib (`evidencias/cdp.py`, `evidencias/qa_b.py`); Playwright nao esta instalado. Pagina por `file://`, porta de debug aleatoria.
- Viewports 1280x720, 820x560, 452x492, nos dois momentos (hub sobre o client e selecao com assistente). Teclado real (Tab, Shift+Tab, Enter, Escape).
- Resultado: `evidencias/qa_resultado_r3.json`, 150 checagens, 0 falhas. Comando: `python3 evidencias/qa_b.py r3`.
- Capturas: `evidencias/b-<largura>-*.png` (client-lobby, hub-*, selecao-*, partida, config).

## Criterios
| Criterio | Resultado | Ids |
|---|---|---|
| B01 entrar/sair, preparo, estado, suporte com retorno | PASSA | B01.* (hub 820x560, 3 etapas ligadas ao client, Esc/Fechar, estado preservado, erro de mod no assistente vai ao suporte do hub e volta ao assistente na aba de origem) |
| B02 colecao por campeao, favoritas/conjuntos, arquivos separados da aplicacao | PASSA | B02.* |
| B03 biblioteca, sala, coordenado desativa conjunto | PASSA | B03.* (lobby mostra o grupo da sala) |
| B04 fontes, comparacao, runas | PASSA | B04.* |
| B05 trios observados | PASSA | B05.* (confirmar campeao pelo botao do client simula a importacao) |
| B06 configuracoes, rascunho, futuros, limites, Bravura | PASSA | B06.* (fluxo Bravura em 6 fases, favorita ou aleatoria, so Arena) |
| B07 visual e dimensoes, D-017 | PASSA | B07.* (palco, hub 820x560 e dentro da janela nos 3 tamanhos, D-017 nos 3, sem azul na UI SEXO2, fontes) |
| B08 offline, teclado, estados, evidencias, correcao | PASSA | B08.* |

D-017 medido: 1280x720 assistente 452x492; 820x560 452x464; 452x492 428x396. Borda direita igual a do botao, folga 8px, dentro da janela, sem cobrir.

## Defeitos achados e corrigidos
Rodada 1 (versao app-pagina): trap de foco no dialogo, contorno do main, botao primario ilegivel, breadcrumb duplicado.
Rodada 2: apos o reenquadramento a primeira execucao falhou em 5 checagens: (a) rotulo de origem do suporte vinha como "Atividades" quando o erro nascia no assistente, (b) o retorno nao restaurava o assistente, (c) teste de foco clicava sem focar, (d) Bravura favorita assumia a primeira favorita. Corrigidos; reexecucao completa 150/150. Tambem: grade de campeoes realinhada para o assistente nao cobrir tiles; faixa de simulacao compacta a 452px.

## Limitacoes
- Dados ficticios (WR, amostras, patch 26.20, skins "exemplo"); Onetricks e a deteccao/reconexao do Bravura sao simulacao declarada, sem partida real de Arena.
- Cena do client e aproximada; cores douradas valem so para a cena, a UI SEXO2 segue neutra (checagem de azul limitada a hub, assistente, botoes e dialogo).
- Copiar chave e abrir pasta so mudam estado visivel. Sem Safari/Firefox/Windows/LoL reais. Sem medicao automatica de contraste.
