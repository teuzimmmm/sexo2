# Arena Bravura — 1.6.1

Pedido: somente quando o próprio jogador confirma Bravura no Arena, detectar o
campeão revelado, preparar uma skin e reconectar automaticamente. O cliente
continua aberto; apenas o executável da partida é encerrado uma vez. Há uma
interrupção de carregamento, portanto não é uma troca instantânea.

Identificação confirmada no assets.wad do rcp-fe-lol-champ-select instalado:
BRAVERY_CHAMP.championId = -3; RANDOM_CHAMP.championId = -2. Exigir myTeam da
célula local com -3 e ação pick local completed=true com championId=-3, modo
CHERRY. Não deduzir Bravura de campeão vazio, ausência de API ou outro jogador.
Eventos websocket registram a confirmação; polling é somente fallback.

Campeão: gameflow teamOne/teamTwo por puuid próprio, com validação no catálogo.
Fallback pela Live Client Data API, linha correspondente ao activePlayer. Não
usar o primeiro jogador da lista. Aguardar no máximo 75 segundos desde GameStart;
se a identificação ou o arquivo da skin não vierem, não encerrar o jogo.

Escolha: skin local disponível, exclusões respeitadas. Se a preferência é
favorita/favoritas, usar favoritas quando presentes; sem favorita, aleatória.
Não proibir repetições. Sorteio com peso por preço e chroma aleatório é proposta
posterior, ainda não implementada.

Preparo/reconexão: adquirir a trava existente de aplicação, conferir caminho/PID
real do jogo, gravar gameId em arena-bravery-match.json antes de terminar esse
processo. Não tocar em LeagueClient/LeagueClientUx ou RiotClient. Preparar usando
o aplicador existente; pedir /lol-gameflow/v1/reconnect quando o overlay estiver
pronto. Se preparar falhar, pedir reconexão sem skin. A parada de emergência é
respeitada. Guard persistente impede repetição mesmo após reinício do aplicativo.
Não estender essa rotina a outras filas ou reconexões manuais.

Verificação: testes de detecção, repetição, processo correto, falhas, cancelamento,
preferências e fallback. Ainda precisa de partida real de Arena para validar o
momento de revelação e o resultado visual. Não prometer funcionamento instantâneo
nem corrigir todos os problemas de desempenho nesta atualização.

Documentação consultada:
https://developer.riotgames.com/docs/lol#game-client-api
/help?format=Full do cliente instalado: PostLolGameflowV1Reconnect.
