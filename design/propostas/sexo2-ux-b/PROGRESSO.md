# PROGRESSO frente B (atividades)

Estado final: concluido, 8/8 criterios verificados em Chromium headless por file://.

## Entregas
- index.html: workspace por atividade (Preparar partida: Antes da fila, Na selecao, Em jogo; Personalizar colecao; Resolver problema), identidade neutra (#0d0e10/#15171a/#22252a/#2a2d32/#ececec), Oswald+Inter locais, sem azul/serifa.
- QA.md, evidencias/*.png (1280, 820, 452), evidencias/qa_resultado_r2.json, evidencias/qa_b.py e cdp.py.

## Criterios
- B01 passa: entrar/sair, preparo em 3 etapas, estado preservado, erro vai ao suporte e volta a origem.
- B02 passa: escolhas por campeao, favoritas e conjuntos com resultado visivel; arquivos separados da aplicacao de mods.
- B03 passa: biblioteca (10 categorias, busca, importar, skin-base, espera fim da selecao, editar/exportar/remover) e sala simulada; coordenado desativa conjunto com aviso.
- B04 passa: preferencia de fonte sem importar, comparacao sob demanda, Onetricks futuro, runas com os 4 estados e editor.
- B05 passa: trios observados por partidas, busca, escolher e restaurar, estado mantido.
- B06 passa: configuracoes rapidas e completas com rascunho, Exalted inelegivel, Bravura sem desafios, aprimoramentos separados.
- B07 passa: fontes carregadas, sem azul, 3 tamanhos, D-017 medido.
- B08 passa: offline, teclado, foco, evidencias e uma rodada de correcao com rechecagem.

## Correcao
Rodada unica: trap de foco no dialogo, contorno do main, layout da selecao a 1280, botao primario pequeno, breadcrumb. Rechecagem r2: 130/130.

## Limites
Simulacao com dados ficticios; sem Windows/LoL/Safari/Firefox; Playwright ausente (CDP proprio).
