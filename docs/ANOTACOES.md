# Anotações do usuário

Itens levantados nos testes no Windows, na ordem em que chegaram. Cada um sai daqui quando
for corrigido e verificado.

1. **Boas-vindas do Pengu ao abrir o cliente** ("Olá Invocador, sua League está agora
   desbloqueada!"): trocar o ícone da rosa pelo do SEXO2 e tirar o selo do Discord ("invalid
   server"). Vem do JavaScript embutido no `core.dll` herdado do Rose (há também selos de
   Ko-fi e GitHub do Rose); a correção vai em `scripts/patch_core_dll.py`.
2. **Favoritas com imagens:** ao clicar num campeão em Skins → Favoritas, abrir uma tela só
   dele com as skins em cartões com imagem (`tilePath`/`loadScreenPath` de
   `/lol-game-data/assets/v1/champions/{id}.json`, servidos pelo próprio cliente); clicar no
   cartão marca ou desmarca a favorita; cromas como bolinhas de cor sob a skin.
3. **Campeões duplicados** na lista de Favoritas (Aatrox, Ahri, Akali, Alistar… aparecem duas vezes).
4. **Botão SEXO2 na seleção da Arena:** ao clicar, nada aconteceu (a confirmar se o painel
   abriu e fechou ou ficou atrás do cliente). Na Arena o assistente não tem runas nem itens
   (fila sem estatísticas no assistente), então só mostraria "Sem dados"; decidir se, fora das
   filas com estatísticas, o botão abre direto o painel de mods, como antes.
