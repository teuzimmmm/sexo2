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
   Causa vista no console: a lista traz também os IDs 60000+ (ex.: Aatrox 266 e 60266), variantes
   de modo especial que o cliente lista junto.
4. **Botão SEXO2 na seleção da Arena:** ao clicar, nada aconteceu, e o painel não abriu nem por
   um instante. Decidido: fora das filas com estatísticas, o botão abre direto o painel de mods.
   Feito, junto com o modo treino (fila 3140) usando as estatísticas das filas competitivas e o
   rótulo "SEXO2" mesmo quando o assistente carrega depois do botão. A causa do "nada" no
   cliente real não foi reproduzida (no navegador o painel abre); o console do cliente agora
   registra `[SEXO2-Assistant] ready` e cada clique. Causa achada depois pelo console: o painel
   abria sem posição, fora da tela; corrigido em `bfbdffc` (pendente de validação real).
5. **Nome do log:** os arquivos de log devem se chamar `sexo2_*.log`, não `rose_*.log`
   (`utils/core/logging.py`, `LOG_FILE_PATTERN` em `config.py`, `friends/diagnostics.py`);
   junto, `rose_diagnostics.txt` vira `sexo2_diagnostics.txt`. A limpeza de logs antigos precisa
   continuar apagando os `rose_*.log` que vieram da pasta migrada. Feito: `sexo2_*.log`,
   `sexo2_runoverlay_*.log` e `sexo2_diagnostics.txt` (o arquivo antigo é renomeado uma vez).
6. **Ícone do aplicativo:** refazer o ícone do SEXO2 (executável, atalho, bandeja, instalador)
   para ficar no estilo do programa. É identidade visual: proposta para aprovação antes de trocar
   `assets/sexo2.ico`.
