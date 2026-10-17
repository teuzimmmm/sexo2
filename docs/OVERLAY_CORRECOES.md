# Correções após uso real da edição 2.0.0.3

Relato: overlay ausente em Arena; demais modos ainda não confirmados pelo usuário.
Autorizado iniciar correções. A janela de boas-vindas inadequada, o texto de
desbloqueio e o Discord inválido ficam registrados como outro problema; esta
rodada se concentra no overlay.

## Causas confirmadas e investigação

- O runtime habilita apenas Ranked/ARAM. Arena nunca chegaria à janela.
- O reconhecimento de Arena exige queue 1700, embora CHERRY já seja um modo
  observado por outros componentes do projeto. Conferir ambos sem mapear Mayhem.
- A resolução de janela exige abrir o processo e ler seu caminho. Essa permissão
  pode falhar; não foi comprovado que falhou no computador do usuário.
- O smoke anterior substituiu toda a resolução da janela por um retângulo falso;
  não validou o encadeamento processo/PID/janela de produção.
- Erros de leitura LCU apenas ocultam a janela, sem diagnóstico utilizável.
- Tela cheia exclusiva continua uma limitação de uma janela externa; o modo usado
  pelo usuário foi perguntado, sem alterar configurações do jogo automaticamente.

O usuário confirmou a falha tanto em tela cheia quanto sem bordas, na versão
`2.0.0.3 (teste)`. Portanto, não atribuir o relato somente à tela cheia nem a um
atalho para executável antigo. O ambiente não permite observar seu LoL real.

## Plano e critérios

1. Habilitar Arena somente durante a partida, sem restaurar painel de seleção.
   Consultar popularidade por campeão com a API existente: pick rate e jogos,
   sem WR de itens/aprimoramentos. Identificar o campeão próprio por estado já
   observado ou seleção própria na sessão, sem escolher um jogador arbitrário.
2. Separar consulta Arena da thread de desenho; máximo uma consulta por contexto,
   cache existente, resposta de partida/campeão anterior descartada. Falhas visíveis
   e sem loop de scraping. Nomes do catálogo com fallback explícito para IDs.
3. Usar enumeração pública de processos para reconhecer o PID da janela, sem
   depender de abrir o processo do jogo. Verificar visibilidade/primeiro plano,
   tamanho e resultado das chamadas de exibição. Não contornar proteção do jogo.
4. Adicionar estado de diagnóstico seguro e prévia nativa acionada explicitamente
   nas configurações. Uma prévia não comprova sobreposição sobre o LoL.
5. Testes offline de Arena/isolamento/falhas, browser para preservar ausência de
   painel de seleção em Arena, smoke Windows com enumeração real de processos e
   geometria de janela real, além do empacotamento e instalação.

Não prometer detecção automática das três cartas oferecidas: não há fonte atual
confirmada para essas escolhas. Não converter dados de ARAM em dados de Mayhem.
Manter skins, importações e atualizador sem mudanças de comportamento.

## Implementação 2.0.0.4

- Arena é reconhecido por queue 1700 ou modo `CHERRY`, já usado pelo mecanismo
  existente. Só habilita esta janela em InProgress/Reconnect; o painel Pengu de
  seleção continua excluído de Arena.
- `ArenaFeed` usa um worker limitado e uma consulta por contexto partida/campeão,
  com o transporte/cache existentes. Falha não vira repetição a cada polling;
  **Reconsultar Arena** permite nova tentativa com intervalo mínimo de 30 s.
  A identificação de Bravura aceita somente a seleção própria correlacionada ao
  invocador local; IDs/nome/PUUID de jogadores não entram no resultado ou logs.
- Listas de aprimoramentos geral e posições 1–4, itens prismáticos e popularidade
  de itens. F9 muda a lista e F10 percorre seus textos. Mostra PR/jogos, nomes do
  catálogo ou ID explícito. Não lê nem projeta WR de itens/aprimoramentos.
- `ProcessCatalog` usa Toolhelp32 para correlacionar o PID do HWND com o nome do
  executável, reutilizando o snapshot por um segundo. Nenhum `OpenProcess`, leitura
  de memória ou tentativa de obter acesso negado ao processo do LoL.
- F8 ocupado não suprime a janela: ela fica expandida, com o conflito identificado.
  Falhas de enumeração/exibição têm diagnóstico e não viram sucesso presumido.
- As configurações mostram estado do runtime/janela e oferecem **Testar janela
  (20 s)**. A prévia é explícita, temporária, passa cliques e funciona sem partida;
  não equivale a comprovar o LoL. Dados da partida continuam vinculados ao gameId.

## Evidências da fonte atual

O componente público `https://lolalytics.com/build/q-BDN2fHIE.js` foi obtido por
HTTP 200 a partir do HTML Arena. Ele mapeia `augment0` a All Augments e
`augment1..4` a Augment 1..4. Esses nomes não indicam raridade. A inspeção foi
complementada com consulta real, não tomada como prova de funcionamento da fonte:

```sh
python scripts/overlay_arena_probe.py --champion jinx --output docs/overlay-arena-live.json
```

Resultado: HTTP 200, Jinx/222, Arena, Emerald+, região all, patch 16.20; sete listas,
214 observações na tabela geral de aprimoramentos. O
[relatório sanitizado](overlay-arena-live.json) registra URL/filtros, contagens e
amostras de PR/jogos. WR restrita permanece removida. Não é teste de uma partida.

## Testes

```sh
PYSTRAY_BACKEND=dummy python -m unittest tests.test_overlay_arena tests.test_game_overlay tests.test_build_bridge tests.test_settings_service tests.test_build_https -q
node --test tests/test_settings_ui.cjs
SEXO2_TEST_BROWSER_PATH=/usr/bin/chromium node tests/browser_builds.cjs
```

No Windows descartável, `SEXO2_TEST_NATIVE_OVERLAY=1` habilita o smoke específico.
Além da pintura/atalhos, o teste novo enumera processos reais, confirma o PID Python
do teste, lê PID e geometria de um HWND real e verifica que os nomes de produção
rejeitam esse processo. Só a escolha do HWND e do executável permitido é controlada
nesse cenário. Outro teste reserva F8 de propósito e exige janela visível.
Isso melhora a cobertura do caminho de produção, sem declarar que há LoL no runner.
