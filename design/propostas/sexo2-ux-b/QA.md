# QA da proposta B (atividades)

Escopo: prototipo HTML estatico, dados ficticios, sem cliente do LoL, sem validacao Windows/producao, sem teste de usabilidade. Nada aqui aprova a proposta.

## Como foi testado
- Chromium headless (chrome-headless-shell do cache Playwright) acionado por CDP com cliente stdlib proprio (`evidencias/cdp.py`, `evidencias/qa_b.py`); Playwright nao esta instalado. Pagina aberta por `file://`, sem servidor.
- Resolucoes: 1280x720, 820x560 (Hub), 452x492 (assistente compacto). Teclado real via `Input.dispatchKeyEvent` (Tab, Shift+Tab, Enter, Escape).
- Resultado final: `evidencias/qa_resultado_r2.json`, 130 checagens, 0 falhas. Comando: `python3 evidencias/qa_b.py r2`.
- Capturas em `evidencias/b-<largura>-*.png` (1280, 820, 452).
- O navegador de teste do checkpoint recusava file://; aqui o Chromium headless aceitou. Safari/Firefox/Windows nao foram testados.

## Criterios
| Criterio | Resultado | Evidencia (ids em qa_resultado_r2.json) |
|---|---|---|
| B01 entrar/sair, percorrer preparo, preservar estado, suporte e retorno | PASSA | B01.* (home, 3 etapas, retomar, preserva campeao/conjunto, erro de mod vai ao suporte com origem e volta a etapa e aba) |
| B02 colecao por campeao, favoritas/conjuntos com resultado, arquivos separados de aplicacao | PASSA | B02.* |
| B03 biblioteca e sala (A03), sorteio coordenado desativa conjunto com aviso | PASSA | B03.* (10 categorias, busca, importar, skin-base, espera fim da selecao, editar/exportar/remover, sala criar/copiar/queda/reconectar/sair/chave invalida, aviso e bloqueio de aplicar conjunto) |
| B04 fontes, comparacao, runas | PASSA | B04.* (trocar fonte nao importa; Onetricks indisponivel sem numeros; simulacao separada; clique importa; importando/sucesso/falha/no_free_page; editor agrupa edicoes) |
| B05 trios observados | PASSA | B05.* (ordem por partidas, 3 icones, WR do trio, busca, escolhido antes do padrao, restaurar, estado entre abas/painel, importacao ao confirmar campeao) |
| B06 configuracoes, rascunho, futuros, limites | PASSA | B06.* (rapidas na selecao, completas com rascunho/Esc/cancelar/salvar, idioma imediato, ouro separado de aprimoramentos, Exalted+croma inelegivel antes do sorteio, Bravura oculta ate revelar e sem desafios/itens, aprimoramentos sem dados/ofertas/nao reconhecida) |
| B07 visual e dimensoes, D-017 | PASSA | B07.* (fontes carregadas, so Oswald/Inter, nenhuma cor azul em computed styles, sem rolagem horizontal, textos sem corte, painel alinhado a direita do botao, 8px acima, dentro da janela e sem cobrir o botao nos 3 tamanhos) |
| B08 offline, teclado, estados, evidencias, correcao | PASSA | B08.* (imagens locais, links existem, sem fetch/URLs remotas, sem erros de console, foco preso e restaurado em dialogos, Esc do painel) |

Valores D-017 medidos: 1280x720 painel 452x492, botao em (1102,640)-(1264,676); 820x560 painel 452x464; 452x492 painel 428x396, todos com borda direita igual a do botao e folga de 8px.

## Defeitos achados e corrigidos (rodada de correcao)
1. Foco por Tab saia do dialogo para a interface do navegador (B08.tabtrap/shifttab falharam). Corrigido com trap de foco no dialogo; passou.
2. Linha clara no topo do conteudo (contorno de foco do `main` apos navegacao programatica). Corrigido (`main:focus{outline:0}`).
3. A 1280px o painel cobria o botao "Continuar" e o resumo da sessao. Corrigido: na selecao o conteudo reserva a coluna do painel (>=1000px) e o resumo desce.
4. Botao primario pequeno com texto branco sobre fundo claro (ilegivel). Corrigido (`.b.sm.p`).
5. Breadcrumb duplicado em Resolver problema e texto confuso no autoaceite. Corrigidos.
6. Falhas iniciais do proprio script de teste (comparar texto transformado por CSS, Enter sem texto no CDP, porta de debug fixa que colidia com outras frentes). Corrigidas no script; nao eram defeitos do HTML.
Rechecagem: execucao completa r2 apos todas as correcoes, 130/130.

## Limitacoes e decisoes assumidas
- Prototipo com dados ficticios (WR, amostras, patch 26.20, skins "exemplo"); Onetricks e Bravura sao simulacao futura declarada; nenhum algoritmo ponderado real.
- Copiar chave e abrir pasta so alteram estado/rotulo visivel; nao usam clipboard ou sistema de arquivos.
- A chave de sala e fabricada (SX2-XXXX) e omitida do diagnostico.
- Os conflitos de sorteio coordenado usam o conjunto ativo; nao foi usado conflito fictício de dois mapas.
- A preferencia de fonte do painel vale para a partida; o padrao salvo muda so em Configuracoes (Salvar).
- Overlays: ha apenas link para `../sexo2-overlays/index.html#b`; a frente de overlays nao foi alterada nem validada aqui.
- Nao foi feita avaliacao de contraste automatizada alem da escolha dos tokens neutros; leitura humana das capturas em 3 tamanhos.
