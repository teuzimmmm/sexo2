# QA — Proposta A (Hub por recurso)

Arquivo: `index.html` (abrir por file://; `#assistente` abre só o painel compacto). Dados ilustrativos, sem rede, sem fetch.
Método: Chromium headless (cache do Playwright) controlado por CDP com cliente stdlib (`evidencias/harness/`; Playwright Python não instalado, nada instalado globalmente). Eventos Tab/Shift+Tab/Enter/Escape são teclas reais via `Input.dispatchKeyEvent`; cliques de fluxo usam `element.click()` após `focus()`. Viewports: 1280×720, 820×560, 452×492. Logs: `evidencias/log-t2/t5/t7.txt` (95 verificações, 0 falhas na rechecagem final).

## Resultado por critério

| ID | Resultado | Evidência |
|---|---|---|
| A01 | PASSOU | 5 destinos + Seleção navegáveis (`aria-current`). Falha simulada em Skins e erro de importação em Mods mostram alerta, "Abrir Suporte" leva ao Suporte com origem; "Repetir verificação" resolve; "Voltar" retorna com campeão/skin/croma intactos e a aplicação passa a funcionar. `a01-*.png` |
| A02 | PASSOU | Campeão/skin/croma/favorita; aplicar skin (chip "Skin aplicada"); editar conjunto em modal (renomear, remover, adicionar seleção) e aplicar (ativo/inativo, nº da aplicação). Entrar no sorteio coordenado: modal avisa que desativa o conjunto; confirmar zera o conjunto ativo (visível em Sala e Skins) e bloqueia aplicar conjuntos; sair não reativa. `a02-*.png` |
| A03 | PASSOU | 10 categorias legadas com contagem, busca, importar exemplo (exige campeão + skin-base; "em seleção" → fica na fila até "Simular fim da seleção"), editar, exportar (nome do .fantome), remover (confirmação). Sala: criar, copiar chave, adicionar participante, sair, reconectar, conectar por chave (valida formato). `a03-*.png` |
| A04 | PASSOU | Fonte preferida (só rascunho; verificado que não importa runas). Comparar fontes sob demanda: Lolalytics e Onetricks com WR/amostra/patch próprios, sem agregado; Onetricks marcado "Futuro · simulação", indisponível por padrão ("Sem dados", sem números substitutos) ou simulado. Clique em "Importar página original" importa na hora (importando → sucesso/falha/no_free_page, páginas pessoais preservadas); editor agrupa edições; "Outras runas". `a04-*.png` |
| A05 | PASSOU | 6 trios ordenados por partidas (verificado), 3 ícones + WR conjunto + partidas; busca por nome/ID; "Usar" coloca o trio antes do padrão; "Voltar ao padrão" desfaz; "Confirmar campeão" simula importação. Nenhum slot de seis itens inventado. `a05-itens-trios.png` |
| A06 | PASSOU | Preferências rápidas (gaveta no painel) e completas (Configurações) compartilham um rascunho; "Todas as configurações" preserva o rascunho e oferece "Voltar à seleção"; Salvar/Cancelar coerentes (contador, ponto na lateral). Ouro e Aprimoramentos/Bravura em seções separadas; link ao modo B do lab de overlays. Elegibilidade antes do ranking: Exalted + croma Obsidiana inelegível com motivo; 60 sorteios sem inelegível. Bravura: oculto → revelar → sortear novamente, sem estatísticas/desafios. `a06-*.png` |
| A07 | PASSOU | Oswald e Inter `loaded` (document.fonts), todo elemento com Oswald/Inter, nenhuma cor azul computada. 1280×720 e 820×560 sem estouro horizontal em todas as páginas; 452×492 sem rolagem de página. D-017 medido: painel 452×492, borda direita = borda direita do botão (0 px), 8 px acima, dentro do palco, sem sobrepor o botão (1280×720 e 820×560). Foco: anel sólido #ececec 2 px. `a07-*.png` |
| A08 | PASSOU | Abre por file://; 0 imagens quebradas; links ../sexo2-ux-b e ../sexo2-overlays existem. Tab percorre nav e conteúdo; Shift+Tab volta; modal: foco preso em 12 passos Tab/Shift+Tab, Escape fecha e devolve foco ao abridor; foco mantido após ações que re-renderizam; Escape fecha a gaveta e devolve foco. `a08-modal-foco.png` |

## Rodada de correção (uma)
- Foco restaurado ao abridor depois de fechar o modal (falha real: ficava no botão removido).
- Hash (`#assistente`, `#sala` ...) passa a funcionar também sem recarregar; compacto abre direto no painel.
- Barra de ações ancorada ao fim da página; alinhamento das linhas de Mods (largura mínima de tags/botões); erro simulado de importação movido para junto da busca.
- Falsos negativos do próprio harness (texto em caixa alta por CSS, contagem de itens) corrigidos nos testes, não no produto.

## Limitações
- Simulações explícitas: sala/chave, Onetricks, importação de runas e itens, exportação, pastas, relatório. Clipboard real só se o navegador permitir; o estado "copiada" é simulado.
- Em 820×560 o palco da Seleção (452×492 + botão) exige rolar a página principal para ver o botão; o painel em si mantém o tamanho real. O modo compacto (`#assistente`) mostra o assistente sozinho.
- Retratos são ícones de campeão; nomes de skins/itens/runas e números são ilustrativos. Contraste e leitor de tela não auditados com ferramenta; não é teste de usabilidade nem do cliente real.
- Capturas pelo navegador headless; Safari/Windows não testados. Overlay aprovado não alterado (fora desta frente).
