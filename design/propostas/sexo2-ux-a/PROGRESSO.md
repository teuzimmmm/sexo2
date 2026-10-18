# PROGRESSO — Frente A (rodada 4)

Estado: CONCLUÍDO. 125 verificações CDP, 0 falhas (evidencias/log-t17.txt). A02 reinterpretado (ver QA.md).

## Mudou na rodada 3
- UI antiga resgatada (assistente, cena de seleção) + visual da B (só look); cantos retos em tudo.
- Painel SEXO2 (820×560) abre em Sala: Sala, Favoritas, Configurações, Suporte, Swiftplay (só no modo).
- Favoritas: ~170 campeões, busca, skins com snippet placeholder, cromas, só Favoritar, estados separados.
- Swiftplay simulado: manual vs sorteio estilo Bravura (favoritas primeiro).
- Sem sorteio/conjuntos no painel; sem rótulos "Hub"/"Demonstração" junto à marca.
- Assistente: header Rota/Confronto/Fonte; abas Runas, Itens, Mods, Preferências rápidas, Todas as configurações.
- NOTAS-PARA-CODIGO.md criado (retirar conjuntos/sorteio; snippet de skin; skins de mods; Swiftplay).

## Rodada 4
- Favoritas: busca também por nome de skin; resultado leva ao campeão com a skin destacada.
- Swiftplay: 2 campeões travados, skin por campeão; sem toque → sorteio Bravura (favoritas primeiro); casos 0/1/2 tocados testados.
- Fonte SEXO2 (botão inferior e marca) = Oswald; bug da regra .btn corrigido; teste adicionado.

## Verificação
Chromium headless 1280×820, teclas reais, fontes loaded, computed style sem border-radius, D-017 medido.

## Pendências
- Só 24 retratos locais; skins sem imagem; lista de campeões manual.
- Modais nativos cobrem a janela do navegador; sem Safari/Windows.
