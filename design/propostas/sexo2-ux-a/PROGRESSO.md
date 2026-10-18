# PROGRESSO — Frente A (Hub por recurso)

Estado: CONCLUÍDO (8/8 critérios verificados; ver QA.md).

## Feito
- Reaproveitado o rascunho A (navegação por recurso) e reescrito `index.html` com identidade neutra: #0d0e10/#15171a/#22252a/#2a2d32/#ececec, foco claro, Oswald (títulos/categorias) + Inter (texto/controles, números tabulares), WOFF2 locais de ../sexo2-shared, sem serifa, sem azul.
- Destinos: Skins (coleção, conjuntos, sorteio/Bravura), Mods, Sala, Configurações, Suporte + Seleção de campeões (assistente 452×492 ancorado ao botão, D-017).
- Estado compartilhado entre telas: seleção, conjunto ativo, rascunho de preferências, erros, retorno (back) contextual.
- Foco: anel claro, restauração após modal/re-render, trap de Tab no modal, Escape.

## Verificação
- Chromium headless via CDP (cliente stdlib), 3 viewports, document.fonts, geometria D-017, Tab/Shift+Tab/Escape reais.
- 95 verificações; rechecagem final com 0 falhas. Logs em evidencias/log-*.txt, scripts em evidencias/harness/.
- Capturas: evidencias/*.png (a01…a08).

## Correções (1 rodada)
- Foco pós-modal, hash sem reload, alinhamento Mods/barra de ações.

## Pendências / limitações
- Tudo que é futuro é simulação explícita (Onetricks, sala, importações).
- 820×560: palco da Seleção rola para mostrar o botão; compacto resolve em #assistente.
- Sem Safari/Windows, sem auditoria de leitor de tela.
