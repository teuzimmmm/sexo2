# PROGRESSO — Frente A (Hub por recurso, dentro do client)

Estado: CONCLUÍDO (rodada 2). 8/8 critérios + enquadramento verificados (109 checagens, 0 falhas).

## Rodada 2
- Reenquadrado: palco 1280×720 simulando o client; faixa de simulação (Cliente / Seleção / Partida) fora do produto; sem cabeçalho/rodapé de app.
- Hub 820×560 abre sobre o client pelo botão SEXO2 do cabeçalho; fecha com Escape/Fechar.
- Seleção: cena com campeões, Confirmar e botão SEXO2 inferior; assistente 452×492 ancorado (D-017 medido). Hub e assistente compartilham estado.
- Bravura reescrita conforme docs/ARENA_BRAVURA.md (Arena, campeão -3, revelado em partida, skin favorita/aleatória, executável encerrado uma vez, reconexão com interrupção).
- Identidade mantida: neutros, Oswald/Inter locais, sem azul/serifa.

## Verificação
- Chromium headless (CDP stdlib) 1280×800; fontes loaded; Tab/Shift+Tab/Enter/Escape reais; geometria do palco/Hub/assistente medida.
- Logs: evidencias/log-t12.txt; capturas: evidencias/r2-*.png (23).

## Pendências / limitações
- Fundo do client aproximado; modais <dialog> cobrem a janela do navegador.
- harness-referencia.png não é do client (diagrama alheio); composição seguiu a réplica renderizada.
- Usado chromium completo (não havia headless-shell); sem Safari/Windows.
