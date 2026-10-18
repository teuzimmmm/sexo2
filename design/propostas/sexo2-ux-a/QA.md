# QA — Proposta A (rodada 3)

`index.html` por file://. Estrutura: faixa de simulação fora do produto (Estado: Cliente / Seleção de campeões / Partida; Modo: Normal / Swiftplay; resultado da importação de runas; Onetricks; falha do cliente; fim da seleção) + palco 1280×720 que simula o client. Painel do SEXO2 820×560 abre pelo botão SEXO2 do cabeçalho (em Sala); assistente 452×492 abre pelo botão SEXO2 inferior da seleção.
Método: Chromium headless (cache Playwright, `chromium-1228`, não o headless-shell) via CDP stdlib, viewport 1280×820. Teclas reais (Tab/Shift+Tab/Enter/Escape). `evidencias/log-t15.txt`: 115 verificações, 0 falhas. Script em `evidencias/harness/`. Capturas `evidencias/r3-*.png` (21).

## Rodada 3: decisões do usuário
- UI antiga resgatada: layout do assistente (Maior WR / Mais comum / Contra X / Outras runas, rodapé de estado), cena de seleção (título + contagem, listas laterais, grade 8×3, CONFIRMAR, "Runas · Feitiços"). Ver também "Trazido da B".
- Painel abre em Sala; menus Sala, Favoritas, Configurações, Suporte (+ Swiftplay só no modo Swiftplay). Mods saiu do painel (vive na aba Mods da seleção). PASSOU.
- Sorteio/conjuntos removidos; "elegível ao sorteio", "Conjunto ativo", "Skin aplicada" ausentes (verificado por texto). PASSOU.
- Favoritas: 171 campeões na grade (24 retratos locais, 147 placeholders), busca por nome; página do campeão com 3 skins e snippet placeholder explícito; skin selecionada expande cromas; só "Favoritar"; favoritar a skin não favorita croma (estados separados, testado em ambas as direções). PASSOU.
- Swiftplay: campeão travado; manual vence; nada tocado → sorteio estilo Bravura com favoritas primeiro, aleatória sem favorita; erro simulado → Suporte → retorno. PASSOU (simulação, não validado em partida real).
- Assistente: texto "Ver a recomendação…" removido; header Rota/Confronto/Fonte sem nome do campeão; abas Runas, Itens, Mods, Preferências rápidas, Todas as configurações (cabem em 452 px); sem aba Skins; Build padrão Inicial/Essenciais/Situacionais e trios mantidos. PASSOU.
- Cantos: nenhum border-radius > 0 em #stage, faixa de simulação e diálogos (computed style), exceto círculos de croma. PASSOU.
- Marca: cabeçalho do painel só "SEXO2" + Fechar; nenhum "Hub"/"Demonstração" em texto, aria-label, title ou alt do palco. PASSOU.

## Critérios A01–A08
| ID | Resultado | Observação |
|---|---|---|
| A01 | PASSOU | erro em Mods (assistente), runas (falha) e Swiftplay → Suporte com origem → Repetir verificação → Voltar preserva contexto (aba/campeão) |
| A02 | REINTERPRETADO | conjuntos e sorteio coordenado removidos a pedido; cobertos por Favoritas (campeão/skin/croma/favorita separados) e Swiftplay |
| A03 | PASSOU | mods na aba Mods: 10 categorias, busca, filtro, importar (campeão+skin-base, fila até fim da seleção), editar, exportar, remover; Sala criar/copiar/sair/reconectar/chave |
| A04 | PASSOU | fonte no header (não importa); comparar fontes; Onetricks indisponível/simulado; importar com um clique; importando/sucesso/falha/no_free_page; editor agrupa |
| A05 | PASSOU | trios por partidas, busca por nome/ID, usar/restaurar, confirmar campeão (cena) simula importação |
| A06 | PASSOU | Preferências rápidas (aba) e completas (Configurações) com rascunho único; ouro × aprimoramentos separados; Bravura |
| A07 | PASSOU | Oswald/Inter loaded; sem serifa/azul; D-017 medido (452×492, direita alinhada, 8 px acima, dentro, sem cobrir); painel sem estouro |
| A08 | PASSOU | file://, 0 imagens quebradas; Tab/Shift+Tab ciclam no painel e no modal; Escape fecha modal → painel → assistente com foco devolvido |

## Trazido da B (somente visual; nenhuma UX da B)
Tokens e tratamento do client: barra com marca JOGAR em dourado sublinhado e borda #4a4233, fundo da cena em gradiente esverdeado escuro, título dourado da seleção, tiles de campeão com borda #3c3526 e destaque dourado, botão CONFIRMAR dourado, botão SEXO2 do cabeçalho vazado (cheio quando aberto) e SEXO2 inferior cheio; botões 28/24 px, abas Oswald com sublinhado interno, tags de contorno, cabeçalhos Oswald em caixa alta; sombra do painel. Os 2 px de raio da B NÃO foram trazidos (tudo 0). Não herdado: atividades, preparo em etapas, breadcrumbs, resumo de sessão.

## Limitações
- Retratos: só 24 de ~170 campeões; placeholder neutro com iniciais nos demais. Imagens de skin: todas placeholder.
- Nomes de skins/cromas dos campeões sem dado são ilustrativos; lista de campeões escrita à mão (pode divergir do catálogo oficial).
- Fundo do client aproximado; modais `<dialog>` cobrem a janela do navegador, não só o palco. O texto "Hub" ainda existe só em arquivos de documentação/código, não na UI.
- Chromium completo (sem headless-shell); sem Safari/Windows; sem auditoria de leitor de tela.
