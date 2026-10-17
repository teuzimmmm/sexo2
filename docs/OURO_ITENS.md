# Comparação de ouro em itens

Plano registrado em 17/10/2026, antes da implementação.

## Escopo confirmado pelo usuário

Comparar somente **seus itens equipados contra os de um adversário**. Não ler ou
mostrar ouro disponível/guardado, nem construir ouro total ou vantagem de equipe.
Preferir o adversário da mesma rota quando houver correspondência única; permitir
trocá-lo com F7. A Live Client API não documenta a ordem manual do TAB: não afirmar
que reproduzimos uma reordenação feita pelo jogador. Seleção é local, sem importar
páginas, comandar o jogo, acessar memória ou consultar estatísticas externas.

## Evidências e limites

Em 17/10/2026, HTTP 200 em:

- https://developer.riotgames.com/docs/lol#game-client-api_live-client-data-api
- https://static.developer.riotgames.com/docs/lol/liveclientdata_sample.json
- https://static.developer.riotgames.com/docs/lol/queues.json

A documentação fornece GET `/liveclientdata/playerlist` (campeão, equipe,
`position`, itens), GET `/liveclientdata/activeplayername` (identificação local) e
GET `/liveclientdata/gamestats` (modo, mapa, relógio). O exemplo de itens documenta
`itemID`, `price`, `count` e `slot`. A amostra JSON oficial tem somente Annie,
relógio zero e inventário vazio; não comprova inventários de uma partida atual.
Queues 480/490 são Swiftplay/Quickplay respectivamente, no Summoner's Rift.

Reprodução: `curl --fail --max-time 20` em cada URL pública acima. Em uma partida
real: `curl --insecure --max-time 3 https://127.0.0.1:2999/liveclientdata/gamestats`.
Não salvar respostas de jogadores sem sanitização. Não há LoL executando neste
checkout Linux: os testes locais usam um servidor TLS sintético e casos explícitos.

`price × count` fornece uma **estimativa do valor dos itens observados**. Não
representa ouro ganho, consumíveis gastos, itens vendidos nem ouro total. Preços
vêm da própria resposta do modo; não aplicar catálogo de preço de Ranked ao
Swiftplay. Item sem preço/quantidade válido torna o valor desse inventário
indisponível, sem somar somente a parte conhecida. Inventário realmente vazio
vale zero. Não fazer ranking de jogadores ou inferir ouro oculto.

## Arquitetura e etapas

1. `sexo2/overlay/gold.py`: transporte reutilizável, anônimo e exclusivo de HTTPS
   loopback, sem proxy/netrc, redirecionamento ou credenciais LCU. Somente os três
   endpoints acima; gamestats antes/depois delimita a amostra. Timeouts, limite de
   resposta e prazo da coleta; nenhum HTTP na thread de desenho.
2. Normalizar somente campeão, equipe, rota e valor de inventário. Identidade do
   jogador é usada transitoriamente para identificar o próprio campeão; não entra
   em snapshots, renderer, fixtures, logs ou disco. Correspondência ambígua falha.
3. Feed no observer já existente, no máximo uma coleta a cada 2 s, sem concorrência
   adicional. Estado vinculado à partida/modo, expira em 6 s desde o início da
   coleta. Falha limpa números, tem backoff limitado e não vira zero/sucesso.
4. Overlay habilita Swiftplay explicitamente (fila 480 ou modo SWIFTPLAY no mapa
   11), sem mudar o suporte do coletor/draft ou usar estatísticas Ranked como
   Swiftplay. Gold aparece como primeiro cartão; sugestões existentes continuam
   acessíveis com F9. F7 alterna o adversário somente nesse contexto.
5. Testar cálculo, preços/itens ausentes, correspondência por rota/manual,
   duplicidade, relógio reiniciado, TTL, troca de partida, timeout, TLS/HTTP/JSON,
   limites, ausência de credenciais e integração com hotkeys. Verificar que novos
   valores não reiniciam a navegação das builds a cada coleta.
6. Revisar código, rodar regressões pertinentes, compilar no Windows, auditar e
   entregar instalador privado atualizado. Validação numa partida real permanece
   necessária; testes sintéticos não a substituem.

## Primeira rodada de implementação

Comparação implementada somente em SR/Swiftplay, sem requisitar `/activeplayer`
ou `currentGold`. Usa identidade transitória de `/activeplayername` para localizar
os itens próprios em `/playerlist`. Nenhuma identidade chega ao renderer.
Treze testes novos passaram, incluindo servidor HTTPS real sintético, proxy
ignorado, reutilização de conexão, ausência de credenciais, HTTP/redirect/JSON/
limites/timeout, valores indisponíveis, rota/manual, TTL e troca de contexto.
Teste Chromium também passou para recuperação do próximo draft sem evento e
falha temporária de contexto. Isso não é validação do LoL atual.
