# Desenvolvimento funcional da 2.0

Plano de execução registrado em 16/10/2026 antes das alterações de implementação.
Instalador, mudança das raízes de dados e limpeza do legado ficam na fase final.
O workflow atual prioriza execução direta; Luna atingiu a cota anteriormente.

## Contratos desta rodada

- `sexo2/services/draft.py`: ler LCU com timeout, produzir contexto sem nomes,
  contas ou credenciais; campeão, modo suportado, rota, inimigos e finalização.
  Identidade muda ao trocar campeão, alvo, modo, risco, filtros ou sessão.
- `sexo2/services/builds.py`: coordenar consultas sob demanda, reutilizar Client,
  guardar somente resultados da sessão atual; substituir pedidos antigos.
  WR/Common mantêm origem e escopo; matchup só após finalização do draft.
- `sexo2/services/loadouts.py`: adaptar páginas do coletor aos contratos LCU,
  preservar páginas pessoais, validar catálogos, reler contexto antes de escrever
  e verificar o resultado. Nenhuma importação automática ou sucesso presumido.
- Bridge: três ações explícitas, `sexo2-build-context`, `sexo2-build-query`,
  `sexo2-build-import`; filas pequenas, execução fora do loop WebSocket,
  payloads sem URLs/IDs de conta vindos do plugin e encerramento definido.
- `SEXO2-Builds`: painel específico para ChampSelect, recolhível, somente exibido
  com uma raiz de seleção reconhecida; sem painel na navegação normal. O nó fica
  no `body` para evitar recorte por carrosséis/ancestrais transformados do cliente.
  Fonte de contexto é o backend; plugin não faz scraping nem decide importação.

## Critérios

1. Contexto e opções mudam corretamente ao entrar/sair e trocar campeão/adversário.
2. Consulta antiga não aparece nem pode ser importada depois de mudança de contexto.
3. Matchup é explícito, limitado aos adversários atuais e fontes confirmadas.
4. Modo sem fonte não cai silenciosamente em Ranked/ARAM; Arena preserva política.
5. Importação verifica schema e IDs atuais e não remove páginas pessoais para caber.
   Uma página de runas gerenciada reutilizável e até dois conjuntos de itens por conta,
   reassociados ao campeão escolhido sem acumular conjuntos a cada partida,
   com blocos identificados por sugestão/alvo, sem inferir sequência conjunta.
6. Falhas de rede, capacidade ou escrita não aparecem como sucesso; sem logs pessoais.
7. Testes offline do serviço e browser isolado da interface; integração no bridge.
8. Testes de cliente simulado não comprovam o LCU/Pengu real. Registrar esse limite;
   sem criar instalador, alterar versão, publicar ou limpar instalações nesta rodada.

## Fontes e situação

- Código atual já usa `.champion-select` e o hook `rcp-fe-lol-champ-select` em
  `Pengu Loader/plugins/ROSE-UI/index.js`; isso é evidência de código, não validação
  do encaixe visual atual do cliente instalado.
- LCU: `/lol-gameflow/v1/gameflow-phase`, `/lol-gameflow/v1/session`,
  `/lol-champ-select/v1/session` são consumidos pelo programa atual.
- Contratos de escrita de runas/itens constam em https://lcu.kebs.dev/ e
  https://hextechdocs.dev/how-to-set-runes-using-lcu/; são interfaces internas,
  sem garantia de estabilidade. A reprodução de escrita no LCU real depende de
  cliente Windows disponível, ausente neste ambiente. Validar por leitura antes
  e depois de cada importação no runtime.

## Progresso

- [x] Reconhecimento e contratos iniciais.
- [x] Contexto e coordenação de consultas.
- [x] Importação e painel de seleção implementados; validação real pendente.
- [x] Revisão, testes isolados, fontes reais e limites documentados.


## Implementação entregue nesta rodada

- Leitura fresca do draft sem nomes de jogadores, PUUIDs ou credenciais. Exige
  identidade válida da partida e não combina sessões em transição. Contextos
  são observados/publicados em ordem entre os dois workers.
- Uma fila curta para contexto e outra para consulta/importação. O bridge não
  aguarda HTTP do LoLalytics; um novo pedido invalida o resultado anterior.
  Não interrompemos à força uma requisição HTTP já iniciada: seus timeouts e
  retries são limitados e sua resposta é descartada se o contexto tiver mudado.
- General prepara WR ajustada ao risco e Common a partir das fontes da primária.
  Matchup usa somente o filtro de adversário, na finalização, e permite manter
  duas preparações anteriores deste contexto. Trocar risco, rota, elo, campeão,
  patch efetivo ou sessão impede misturar dados incompatíveis.
- Interface `SEXO2-Builds` específica da seleção, com nomes do catálogo atual,
  rota automática/manual, Emerald+/todos, alvo e sugestão. As requisições à fonte
  começam quando o painel é aberto; erro não inicia um loop automático de retries.
  O polling de contexto pausa durante GameStart/InProgress/Reconnect.
- Fonte de Ranked global para SR (inclusive como referência de jogos normais),
  ARAM padrão da queue 450 e popularidade de Arena da queue 1700. Variantes
  desconhecidas não são convertidas em modos suportados por aproximação.
- Arena exibe itens/aprimoramentos por popularidade, sem recuperar WR proibida.
  Registros sem ID positivo não viram sugestões. Nomes dos aprimoramentos vêm
  de `cherry-augments.json`. Não há importação de páginas de Arena nesta rodada.

### Importação e propriedade

Os botões de runas e itens são ações explícitas e separadas. O plugin manda
somente referência ao resultado e escolha; o servidor usa as páginas que ele
próprio preparou. Não aceita IDs de runas, caminhos ou URLs fornecidos pelo plugin.
Antes das escritas, confere novamente draft, campeão, revisão e conta.

A importação de runas descobre os estilos pelo catálogo `perkstyles.json` atual:
valida as quatro posições primárias, as duas secundárias em linhas distintas e
os três fragmentos. Os índices `page.pri/sec` do LoLalytics não são tratados como
IDs de estilos do LCU. A página tem nome legível `SEXO2 · WR/Common/vs ...`.
A propriedade é registrada pelo ID nativo, vinculada à conta; o nome sozinho
não autoriza sobrescrever uma página. Sem espaço, não apaga páginas pessoais.

Os itens preservam blocos iniciais, core de três itens e alternativas, validando
IDs no catálogo do cliente. `plan_item_pages` organiza até 20 blocos por conjunto
em no máximo dois conjuntos próprios; isso é nosso orçamento de apresentação,
não uma afirmação sobre o limite oficial de páginas do LoL. IDs são estáveis por
instalação/conta e os slots são reutilizados ao trocar o campeão. Títulos de bloco
usam somente suas próprias métricas; a WR do core não é copiada para itens 4–6.

O pequeno registro `sexo2-loadouts.json` fica no diretório de dados vigente e
não contém credenciais. Deve ser preservado na migração final. As escritas LCU
aceitam somente rotas permitidas em loopback, têm limite de resposta de 4 MiB,
timeouts, sem redirects nem repetição automática de POST/PUT. Sucesso exige
releitura compatível. Divergência após uma escrita é informada como não confirmada;
não há rollback cego que possa apagar uma edição concorrente do usuário.

A atualização em lote de conjuntos depende de GET/PUT internos do LCU, sem
transação compartilhada com outros programas. A releitura anterior recusa
conflitos já observáveis, mas não elimina a janela de uma edição externa entre
essa leitura e o PUT. Esse comportamento precisa de validação no cliente real.

## Como exercitar

No ambiente Windows de desenvolvimento já preparado para o SEXO2 (Python,
dependências e componentes Pengu/LTK existentes), o ponto de entrada continua:

```sh
python main.py --dev
```

Este comando inicia o programa real; não foi executado neste Linux. Não basta
copiar o JavaScript para um executável antigo: a versão do backend também precisa
conter os novos serviços/rotas. No draft, abrir **SEXO2 · Builds**, escolher a rota
ou manter automática, consultar e selecionar WR/Common. Na finalização, escolher
um adversário. **Importar runas** aplica a sugestão selecionada; **Importar itens**
reúne as opções preparadas em até dois conjuntos. As configurações existentes
continuam fornecendo o nível de risco. Não há nova janela externa ou overlay
sobre a partida.

Se o programa reutilizar um Pengu externo já registrado, ele preserva essa
instalação e não sincroniza automaticamente os novos plugins para ela. Nesse
ambiente de desenvolvimento, o Pengu ativo também precisa conter a pasta
`plugins/SEXO2-Builds` desta revisão, além do bridge existente. A distribuição
consistente dos componentes será tratada com o instalador na fase final.

## Verificações reproduzidas

```sh
PYSTRAY_BACKEND=dummy python -m unittest tests.test_build_workflow tests.test_build_bridge tests.test_build_https -q
PYSTRAY_BACKEND=dummy python -m unittest discover -s tests -q
PYSTRAY_BACKEND=dummy python -m unittest discover -s lcu/tests -q
PYSTRAY_BACKEND=dummy python -m unittest discover -s pengu/tests -q
SEXO2_TEST_BROWSER_PATH=/usr/bin/chromium node tests/browser_builds.cjs
python scripts/build_workflow_probe.py --live-source --output docs/build-workflow-live-2026-10-16.json
```

`SEXO2_TEST_BROWSER_PATH` é opcional quando o navegador do Playwright já estiver
instalado. O teste usa navegador isolado, nunca o navegador pessoal do usuário.
O ambiente `PYSTRAY_BACKEND=dummy` é para testes Linux, não execução normal.

- 43 testes do fluxo/bridge/gateway/HTTPS passaram: contexto, cancelamento lógico,
  finalização, consultas, IDs de catálogo, propriedade por conta, limites,
  preservação de páginas, corrupção e confirmação de escrita.
- Suíte geral: 424 testes, nenhuma falha de asserção, um erro preexistente ao
  importar `test_startup_policy` por `ctypes.windll` ausente no Linux e um teste
  nativo de Windows ignorado. LCU: um teste passou. Pengu: 15 testes, dois ignorados,
  sem falhas.
- Chromium isolado: tela normal sem painel, abertura sob demanda, importação pelo
  bridge simulado, finalização, descarte de resposta antiga, erro sem loop de
  retries, pausa em partida e dimensões 1024×576/1280×720. No cenário simulado,
  o painel não cobre as listas dos times ou o botão de confirmação. Os avisos
  persistem ao trocar a sugestão; um ancestral com transform/overflow não recorta
  os controles do painel.
- Probe do coordenador com **fonte HTTP real e draft sintético**: quatro GETs
  de fonte, Ahri middle WR/8992 e Common/8112, mais Ahri vs Annie/8112, patch16.20.
  O [relatório](build-workflow-live-2026-10-16.json) registra URLs, runas, blocos e
  métricas. Não houve acesso/escrita a um LCU real nesse probe.
- Catálogos atuais de runas, itens e aprimoramentos foram conferidos por HTTP no
  CommunityDragon 16.20. Projeções públicas e hashes estão em
  `tests/fixtures/loadouts/sources.json`. Sessões e contas dos testes são sintéticas.
- Sete testes usam sockets HTTPS reais em loopback, certificado efêmero verificado
  e o adaptador LCU do programa, com fonte LoLalytics offline. Cobrem WR/Common,
  dois matchups separados, importação/releitura em SR e ARAM, capacidade recusada,
  saída do draft, resposta perdida após aplicar a escrita e confirmação divergente.
  O teste comprova nosso fluxo HTTP/JSON, sem comprovar o cliente Riot real.

## O que ainda precisa ser comprovado

- Raiz e encaixe visual no cliente Pengu/LoL Windows atual; os seletores conhecidos
  `.champion-select`/`.skin-selection-carousel` vêm do código existente. Não há
  fallback para injetar o painel em qualquer tela se esses seletores mudarem.
- Leitura dos schemas e importação/ativação no LCU real, inclusive conta com
  páginas cheias, configurações de idioma e componentes nativos efetivamente usados.
- Aparência/percepção de tempo no draft e consumo total de CPU/RAM. Não foi feita
  comparação com Blitz nem promessa de consumo menor.
- Build e distribuição Windows. Não houve compilação de executável, instalação,
  mudança de versão, push ou release. Os arquivos do PC do usuário não foram tocados.
- Fase final de caminhos próprios, migração, limpeza e instalador continua pendente.

## Fechamento sem depender de validação manual

Autorizado pelo usuário em 16/10/2026. A ausência do cliente Windows não bloqueia
estes ajustes; não equivale à comprovação de uma partida real.

1. Usar transporte limitado e leitura fresca também nos endpoints do draft e
   catálogo de campeões, sem alterar os consumidores antigos do LCU.
2. Revisar invalidação e exibição de avisos no painel, mantendo consultas à fonte
   sob demanda e ações de importação explícitas.
3. Exercitar serviço, adaptador e importador por HTTPS real em loopback contra
   um servidor sintético isolado, com identidades fictícias e certificado efêmero.
   Cobrir aplicação, releitura e falhas, sem credenciais ou cliente pessoal.
4. Incluir testes pertinentes no workflow Windows existente, sem publicar,
   compilar instalador ou executar limpeza. Revisar e registrar commit local.

Conclusão: verificações reproduzíveis passam, falhas não viram sucesso, páginas
pessoais são preservadas e limites do teste sintético continuam explícitos.

### Resultado do fechamento

Os quatro itens acima foram implementados e revisados. O adaptador captura
sessão e endereço sob o lock da conexão e usa leituras frescas de draft com
timeout de conexão/leitura de 1/2 segundos, limite de 4 MiB e sem retries ou
redirects. O transporte antigo dos outros recursos não foi alterado.

O painel traduz os avisos relevantes e mantém o escopo das métricas visível;
não mostra códigos internos da biblioteca. A montagem no `body` depende sempre
da fase ChampSelect e dos seletores reconhecidos, e desaparece na saída.

O workflow Windows existente agora inclui regressões de LCU/Pengu e o browser
isolado. A configuração foi revisada; o job remoto não foi executado nesta rodada,
pois não houve push. Esse workflow também usa servidor sintético, sem LoL instalado.
Não é necessário aguardar uma ação do usuário para concluir estes itens de código.
