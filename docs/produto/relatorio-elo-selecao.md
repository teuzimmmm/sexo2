# Relatório — Elo na seleção de campeões (D-140)

Data: 20/10/2026

## Objetivo

Mostrar o elo dos jogadores na seleção de campeões do SEXO2:

- “Meu time”, com posição, tier, divisão e PDL.
- “Adversário”, somente quando o cliente expõe o `puuid` de cada jogador.
- Solo/duo como primeira opção e flex como segunda, prefixado com “Flex”.
- Jogador sem ranqueada ou falha na leitura aparece como `—`.

## O que foi implementado

### Leitura no LCU

- `lcu/core/lcu_api.py`: novo `LCUAPI.ranked_stats(puuid, timeout)`, que consulta
  `/lol-ranked/v1/ranked-stats/{puuid}` com o `puuid` codificado no caminho.
- `lcu/core/client.py`: fachada `LCU.ranked_stats()` delegando para a API.

### Estado do assistente

- `sexo2/services/assistant.py`:
  - leitura de `queueMap` e `queues`, com fallback de solo/duo para flex;
  - cache por sessão e por `puuid`;
  - limite de 5 consultas para o time e 5 para o adversário por seleção;
  - falhas e ausência de ranqueada viram `elo: null`;
  - novo campo `ranked` no estado publicado;
  - mensagem `assistant-ranked` para atualizar apenas o elo, sem refazer runas
    ou builds.
- Nenhum polling, timer ou observador novo foi adicionado.

### Ponte e evento de elenco

- `pengu/communication/message_handler.py`: rota `assistant-ranked`.
- `pengu/communication/broadcaster.py`: novo `broadcast_assistant_roster()`.
- `pengu/core/skin_monitor.py`: delegação do evento.
- `threads/websocket/websocket_event_handler.py`: assinatura do elenco visível
  (`cellId`, `puuid`, campeão, intenção e posição) para emitir o evento somente
  quando algo muda.

### Painel

- `Pengu Loader/plugins/SEXO2-Assistant/index.js`:
  - nova aba **Equipe**, entre **Itens** e **Mods**;
  - seções **Meu time** e **Adversário**;
  - nomes de tier em português;
  - `Flex · Ouro II · 45 PDL` quando o elo vem do flex;
  - Mestre, Grão-Mestre e Desafiante aparecem sem divisão;
  - `—` para jogador sem ranqueada ou falha.

## Testes adicionados

- `lcu/tests/test_lcu_api_ranked.py`: endpoint, codificação do `puuid`,
  jogador ausente e fachada.
- `tests/test_assistant_service.py` (`RankedTeamTests`): preferência solo/flex,
  cache, limite de 5 por lado, falha, adversário sem `puuid` e troca de sessão.
- `tests/test_assistant_plugin.cjs`: formatação do elo, tiers e `—`.
- `threads/tests/test_assistant_roster_event.py`: deduplicação do evento de
  elenco e mudança de jogador/campeão.
- `tests/fixtures/lcu/ranked-stats-representative.json`: resposta simulada do
  LCU com `queueMap` e `queues`.

## Verificação

- `python scripts/run_tests.py -q`: **800 testes, OK** (1 skip).
- `node --test tests/test_*.cjs`: **42 testes, OK**.
- `ruff check .`: **OK**.
- `ruff format --check .`: **388 arquivos formatados**.

Durante uma execução completa, um teste não relacionado de
`injection/tests/test_game_monitor.py` falhou por timing. Isolado, passou 5/5;
a suíte completa passou na repetição.

## Pendente de confirmação no cliente real

1. Se o `theirTeam` realmente expõe `puuid` durante uma seleção de campeões.
2. Layout da aba com até 10 linhas e rolagem.
3. Divisão devolvida pelo cliente para Mestre, Grão-Mestre e Desafiante.

## Commits

- `54c5a09` — Add LCU ranked-stats read and team elo state for D-140
- `0c90067` — Show team elo in the assistant Equipe tab
- `0d62619` — Document D-140 and its protected behavior

Branch: `sexoatividade`.
