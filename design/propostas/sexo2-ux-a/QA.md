# QA — Proposta A (rodada 2: SEXO2 dentro do client)

`index.html` por file://. Estrutura: faixa de simulação (fora do produto: Cliente / Seleção de campeões / Partida) + palco 1280×720 que simula o client (fundo neutro aproximado, barra de navegação, botão SEXO2 no cabeçalho). Hub 820×560 abre sobre o client pelo botão do cabeçalho; assistente 452×492 abre pelo botão SEXO2 inferior da seleção. Hash: `#cliente`, `#selecao`, `#skins`, `#mods`, `#sala`, `#config`, `#suporte`.
Método: Chromium headless (cache Playwright; só havia chromium completo `chromium-1228`, não o headless-shell) via CDP stdlib, viewport 1280×800 (palco 1280×720 + faixas). Teclas reais para Tab/Shift+Tab/Enter/Escape. `evidencias/log-t12.txt`: 109 verificações, 0 falhas. Script em `evidencias/harness/`.
Nota: `referencias/harness-referencia.png` é um diagrama de outro assunto (loop do Claude Code), sem relação com o client; a composição foi tirada de `sexo2-replica` renderizada (ids #stage/#clientnav/#hub-launch/bottom/confirm-champ).

## Enquadramento (rodada 2)
- Palco 1280×720; sem cabeçalho/rodapé de app; faixa de simulação fora do palco. PASSOU.
- Estado Cliente: botão SEXO2 abre Hub 820×560 (dentro do palco, abaixo da barra do client); Escape e Fechar fecham e devolvem o foco ao botão. PASSOU. `r2-01`, `r2-02`.
- Estado Seleção: cena com campeões clicáveis, Confirmar, botão SEXO2 inferior; assistente ancorado. Do assistente se chega ao Hub (Todas as configurações, abrir coleção, Suporte) e o retorno devolve à seleção com rascunho e escolhas. PASSOU. `r2-15`…`r2-21`.
- Estado Partida: sem client/Hub; aponta para overlays. `r2-23`.
- D-017 medido: 452×492, borda direita = a do botão (0 px), 8 px acima, dentro do palco, sem sobrepor o botão. PASSOU.

## Critérios
| ID | Resultado | Observação |
|---|---|---|
| A01 | PASSOU | 5 destinos no Hub; erro em Skins/Mods/assistente → Suporte com origem → Repetir verificação → Voltar preserva escolha (`r2-03/04`) |
| A02 | PASSOU | campeão/skin/croma/favorita/aplicar; conjunto editar/aplicar; coordenado avisa e efetiva desativação (`r2-05…r2-09`) |
| A03 | PASSOU | 10 categorias, busca, importar (campeão+skin-base, fila até fim da seleção), editar/exportar/remover; Sala criar/copiar/sair/reconectar/chave (`r2-10…r2-12`) |
| A04 | PASSOU | fonte preferida não importa; comparar com amostras/WR/patch separados, Onetricks futuro/indisponível; importar original; importando/sucesso/falha/no_free_page (`r2-16/17/19`) |
| A05 | PASSOU | trios por partidas, busca por nome/ID, usar/restaurar, confirmar campeão simula importação (`r2-20`) |
| A06 | PASSOU | prefs rápidas+completas com rascunho único; Exalted+croma inelegível antes do ranking (60 sorteios); ouro × aprimoramentos separados; Bravura (abaixo) |
| A07 | PASSOU | Oswald/Inter loaded; sem serifa/azul computados; Hub sem estouro horizontal; foco #ececec 2 px |
| A08 | PASSOU | file://, 0 imagens quebradas; Tab/Shift+Tab ciclam no Hub e no modal; Escape fecha modal→gaveta→Hub→assistente com foco devolvido |

## Bravura (conforme ARENA_BRAVURA.md)
Texto corrigido: só no Arena, quando o jogador confirma Bravura na seleção (campeão -3); o jogo sorteia/revela já em partida; o app detecta, escolhe skin (favoritas, senão aleatória, exclusões respeitadas), encerra o executável da partida uma vez e reconecta (interrupção de carregamento). Fluxo simulado em 3 etapas; verificado favorita usada, aleatória sem favorita, exclusão Obsidiana respeitada; nada de "revela antes da seleção", estatísticas ou desafios. Aprimoramentos ficam em Configurações › Overlays.

## Limitações
- Fundo do client e navegação são aproximações; nada é enviado ao LoL. Futuro = simulação explícita (Onetricks, sala, importações, Bravura).
- Modais nativos (`<dialog>`) cobrem a janela do navegador, não só o palco.
- Sem Safari/Windows, sem auditoria de leitor de tela/contraste por ferramenta.
