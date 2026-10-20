# PROGRESSO frente B (atividades dentro do client)

Estado: concluido (rodada 2), 8/8 verificados em Chromium headless por file://, 150/150 checagens.

## Rodada 2: reenquadramento
- Palco 1280x720 simulando o client LoL: nav, cena, botao SEXO2 no cabecalho; faixa de simulacao Cliente/Selecao/Partida fora do produto.
- Hub 820x560 abre sobre o client pelo SEXO2 do cabecalho (Esc/Fechar); entrada com as 3 atividades.
- Selecao de campeoes: assistente 452x492 ancorado ao botao SEXO2 inferior (D-017 medido nos 3 tamanhos).
- Antes da fila = lobby, Na selecao = champ select, Em jogo = partida.
- Bravura reescrita conforme ARENA_BRAVURA.md (so Arena, -3, revela em partida, encerra o executavel uma vez, reconecta, interrupcao de carregamento).

## Criterios
- B01 a B08 passam; ver QA.md e evidencias/qa_resultado_r3.json.

## Entregas
- index.html, QA.md, PROGRESSO.md, evidencias/ (PNG 1280/820/452, qa_b.py, cdp.py, qa_resultado_r3.json).

## Limites
Simulacao com dados ficticios; Bravura sem partida real; sem Windows/LoL/Safari/Firefox; cena do client aproximada; Playwright ausente (CDP proprio).
