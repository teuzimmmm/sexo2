# SEXO2 — evolução dos processos e estabilidade

Plano registrado antes de iniciar novas alterações de código, em 13/10/2026.
O usuário autorizou começar o projeto após documentá-lo.

## Objetivo

Assumir o controle dos processos herdados para entendê-los, corrigir travamentos
e melhorar o uso. Não reescrever por estética de autoria nem apenas substituir
nomes. Reutilizar o que funciona e manter créditos/licenças numa seção própria.

## Problemas relatados

- Aplicativo trava durante o uso.
- Há travamentos ao entrar na partida.
- Painel é visualmente estranho e não parece parte do cliente LoL. A composição
  de painéis antigos com estilos sobrepostos é uma solução intermediária.

## Ordem de trabalho

1. Investigar e estabilizar aplicativo e entrada na partida.
2. Separar os processos em serviços com interfaces explícitas e comportamento
   testável; substituir componentes herdados por etapas quando houver ganho.
3. Reconstruir o painel com proporções, tipografia, espaçamento, controles e estados
   compatíveis com a interface real do cliente, sem embutir o painel antigo.
4. Atualizar a identidade e preparar a distribuição/atualização recuperável.

## Etapa 1 — estabilidade

- Correlacionar logs com lobby, confirmação, preparo, início da partida e aplicação.
- Medir duração e frequência de leitura de arquivos, downloads, preparo/injeção,
  chamadas LCU, consultas da sala e respostas do painel.
- Identificar operações repetidas, trabalho desnecessário e tarefas que bloqueiam
  a interface; mover trabalho demorado para execução apropriada e controlada.
- Definir limites de tempo, cancelamento e erros compreensíveis; não declarar
  sucesso de aplicação apenas porque uma preferência ou arquivo foi preparado.
- Reduzir atividade durante partidas. Preservar stop de emergência e recuperação.
- Distinguir travamento do app, pausa do jogo durante preparo e fechamento/crash;
  não atribuir uma causa sem evidência.

Critério: reprodução/medição documentada, correções testadas nos pontos encontrados
e validação posterior pelo usuário em partida real. Testes isolados não substituem
a observação real. Não abrir/fechar o jogo do usuário para reproduzir sem necessidade.

## Etapa 2 — serviços

Componentes: conexão/estado do LoL, catálogo e dados persistentes, seleção de skins,
preparo/aplicação, sala/hospedagem, atualização/recuperação e diagnóstico.

A interface solicita ações e recebe estados desses serviços. Implementações antigas
saem somente após o substituto preservar suas funções e passar pelos testes.
Sem duplicar serviços ou mecanismos de atualização concorrentes.

## Etapa 3 — painel

- Um ponto de entrada no HUD; sem botões flutuantes extras.
- Construir nossa tela de configurações ligada aos serviços, em vez de transportar
  o formulário herdado para dentro de outro painel.
- Usar controles e referências reais do cliente; verificar no tamanho e ambiente
  reais, incluindo componentes com Shadow DOM e fases do jogo.
- Preservar favoritas de qualquer campeão, Swiftplay, perfis, escolha manual,
  sorteio opcional, sala, recuperação na seleção, autoaceite opcional e diagnóstico.
- Preservar busca, foco, rolagem e alterações durante atualizações de estado.

## Identidade aprovada

- Nome: SEXO2.
- Windows: BORK preto com legibilidade em fundos claros/escuros.
- HUD: BORK no tom nativo do cliente.
- Tela de abertura/carregamento: escudo do Atlético Mineiro (Galo), substituindo
  o ícone Rose. Verificar também carregamento e boas-vindas gerados pelo Pengu.
- Créditos da base permanecem separados da experiência principal.

## Distribuição e dados

- Manter código no Git atual; branches/commits para mudanças, sem novas cópias do
  projeto a cada alteração. GitHub depende de definir conta/nome/visibilidade.
- Atualizador por patch deve verificar instalação/versão, integridade, processos
  abertos e espaço; preservar arquivos anteriores e recuperar após falhas.
- Skins, favoritas, perfis e configurações permanecem fora dos arquivos substituídos.
- Não publicar ou incluir dados pessoais, credenciais, logs ou links de sala no Git.

## Registro da execução

Nesta etapa inicial: registrar o plano, analisar evidências e abrir a primeira
investigação de estabilidade. Registrar causas comprovadas, mudanças e limites
dos testes antes de preparar uma entrega. A versão SEXO2 r2 permanece disponível.


### 2026-10-13 — primeira correção de estabilidade

Branch: `stability/entry-performance`, criada após o registro do plano.

- Logs mostram falhas repetidas de reconexão da sala, respostas duplicadas de
  configurações e timeouts da conexão local do cliente. São pistas, não causas
  comprovadas dos travamentos. Links de sala e credenciais não foram registrados
  neste documento.
- O tempo total de `runoverlay` inclui a duração da partida; não deve ser tratado
  como tempo de preparação ou congelamento.
- Falha comprovada por teste: `resume_game()` descartava a referência do processo
  mesmo quando todas as tentativas de retomada falhavam. A limpeza também perdia
  a referência após uma falha. Agora ambos preservam o processo para nova tentativa
  de liberação; processos encerrados podem ser esquecidos normalmente.
- Validação: 45 testes de injeção e 116 testes gerais passaram. Dois testes novos
  simulam falhas de permissão e recuperação posterior. Testes de processos usam
  um processo substituto, nunca uma partida real.
- Limite: ainda existem outros caminhos de suspensão/retomada para auditar,
  incluindo o timeout automático. Esta correção não resolve nem identifica todos
  os travamentos relatados.
- Próximas etapas: medir fila de pedidos e reconexão; auditar o restante do monitor;
  separar os serviços antes de substituir o painel. Ícones, instalador e atualização
  por patch ainda não foram alterados nesta etapa.


### Continuação — estabilidade sem depender de partida real

O usuário informou que não pode testar agora. A execução prossegue com cenários
isolados; observação em partida real permanece uma validação futura, não um
bloqueio para implementar e testar os componentes.

- Recuperação por timeout passa a verificar se o jogo saiu do estado suspenso.
  Duas tentativas são limitadas; se falharem, a referência continua disponível
  para limpeza/emergência. Uma nova monitorização não substitui essa referência.
- O relógio da pausa usa tempo monotônico, sem depender de ajustes do relógio do PC.
- Pedidos simultâneos para entrar na sala compartilham uma tentativa. Cancelar
  apenas um pedido do painel não cancela os demais; sair da sala cancela o início
  pendente. Encerramentos são serializados.
- As consultas síncronas de identidade ao LCU deixam o loop de mensagens e passam
  a executar em uma thread. Teste reproduz consulta bloqueada enquanto o loop
  continua atendendo outra tarefa.
- A fila do bridge registra espera, execução e quantidade pendente somente em
  operações lentas (>= 0,5 s), sem registrar conteúdo dos pedidos ou links.
  Isso permite distinguir fila congestionada de operação demorada na próxima
  execução instalada.
- Validação: 48 testes de injeção, 120 gerais, 42 de sala, 15 de Pengu e 36 de
  threads passaram (261 no conjunto). Após ajustar a serialização de encerramento,
  os 13 cenários de sala fixa foram executados novamente e passaram.
- Não houve instalação, abertura de partida ou alteração dos dados pessoais.
  Estas mudanças estão no código; a instalação r2 existente ainda não as recebe.
- Próxima etapa do projeto: separar a execução dos pedidos do painel em um serviço
  próprio, com fila controlada e medições, antes de reconstruir suas telas.


### Serviço próprio de execução do painel

- Criado `sexo2/services/work_queue.py`: execução serial em uma única thread,
  fila limitada, envio sem espera e encerramento que drena ações aceitas.
- Integrado ao processamento de skins fixadas. Substitui uma nova thread para
  cada pedido por um único trabalhador com no máximo 16 pedidos pendentes.
- Salvamentos aceitos mantêm ordem. Sobrecarga responde pelo protocolo existente
  `swiftplay-pins-error`; o painel mantém o rascunho após erro de salvamento.
- Falha em uma ação ou em sua resposta não interrompe os pedidos seguintes.
  A fila não cancela uma chamada HTTP em execução: os limites dessa chamada
  continuam sendo responsabilidade do serviço/LCU.
- Incluído o pacote `sexo2` na configuração de empacotamento do SEXO2.
- Validação: 3 cenários novos (fila saturada e ordem de salvamentos, falha seguida
  de recuperação, integração de erro de salvamento com leitura posterior).
  Conjunto geral agora tem 123 testes, todos aprovados; os 15 de Pengu passaram
  após integração. O teste de navegador do HUD passou (favoritas, rolagem,
  perfis, sorteio, sala em ChampSelect, escolha manual, configurações/diagnóstico).
- O teste do navegador usa serviços simulados e não confirma aparência ou
  funcionamento dentro do cliente LoL real.
- Próximos itens: ampliar separação dos serviços e reconstruir o painel sem
  embutir os formulários antigos. Não foi produzido instalador/patch nesta etapa.


### Entrega de teste r3 — prioridade solicitada pelo usuário

O usuário voltou a poder testar e pediu rapidez. A entrega r3 é um ponto de
estabilidade verificado, com as correções até `9f34db6`. A migração de configurações
em andamento foi guardada em dois stashes identificados como WIP, incluindo o
novo módulo não rastreado, para não incluir código incompleto no executável.

- Versão Windows: 1.4.7.10. Protocolo da base continua 1.4.7.
- Pasta de entrega: `novo/SEXO2-r3`; versões anteriores preservadas.
- Visual do painel/ícones permanece o da r2. Ainda falta a reconstrução solicitada.
- Não abrir/fechar o LoL nem executar o instalador automaticamente. O usuário
  fará a instalação e observação em partida real quando puder.

Validação da entrega: auditoria do executável compilado e de todos os plugins
aprovada; compilação do instalador concluída; ZIP verificado por CRC e SHA-256
do instalador. ZIP: 95.584.773 bytes. Instalador: 95.583.872 bytes. Não instalado
automaticamente.


### Decisão do usuário — somente atualizações daqui em diante

O usuário não quer reinstalar a cada entrega nem acumular resíduos. Próximas
entregas para uma instalação existente devem ser atualizações/patches, sem novo
cadastro de instalação ou atalhos. Instalador completo fica restrito ao primeiro
uso em outro PC.

A entrega r3 atual ainda é um instalador completo. Mantém o AppId e usa a pasta
anterior quando reconhecida, mas cria uma cópia completa `.backup-<data>` a cada
atualização e não a remove após sucesso. Portanto pode acumular espaço; não deve
ser apresentada como patch.

Requisito do atualizador: localizar a instalação existente, verificar versão e
integridade, trocar apenas arquivos necessários, preservar dados pessoais e
limitar a recuperação à última atualização. Arquivos temporários e backups
administrados pelo atualizador devem ter retenção controlada. Não apagar cópias
antigas do usuário ou backups legados automaticamente nesta etapa.


### 1.5.0 — configurações próprias e atualização por delta

- Formulário próprio `SEXO2-Settings`: tempos, autostart, categorias vazias, pasta,
  idioma, mods (todas as categorias), diagnóstico e atualizações/GitHub.
- Substituído o formulário antigo; controladores maduros de mods e diagnóstico
  permanecem como adaptadores. Removido o painel de sala legado duplicado no HUD.
- Gravação conjunta de opções, validação antes de salvar, erro com rascunho
  preservado. Falha de gravação tenta reverter autostart quando alterado.
- BORK preto no Windows; máscara BORK do HUD mantém o tom herdado do cliente.
  Galo oficial na abertura. Apresentação do welcome do core recebe marca local
  sem modificar o binário assinado. Créditos/licenças preservados.
- Patch Ed25519/SHA-256 com helper independente, sem nova instalação/cadastro,
  guarda apenas última recuperação. Preserva dados pessoais e hashes.game.txt.
- Consulta automática ao abrir app e cliente, aviso na bandeja quando disponível;
  Configurações contém Verificar atualização, Atualizar e Abrir GitHub do projeto.
- Git remoto confirmado por comando e API: `teuzimmmm/sexo2`, privado e inicialmente
  vazio. Navegador não será usado para publicação, conforme pedido do usuário.
- Token compartilhado de leitura foi autorizado conceitualmente, mas ainda não
  fornecido/configurado. Credencial do Git permite publicar, não será embutida.
- A revisão automática bloqueou enviar a chave privada para um secret do Actions.
  Usuário pediu explicação das implicações; ainda não autorizou esse armazenamento.
  Workflow fica preparado, assinatura local e entrega do patch prosseguem.
- Validação: 134 testes gerais e 15 de Pengu aprovados; navegador simulado aprovou
  favoritas, rolagem, perfis, sorteio, sala em seleção, escolha manual, formulário,
  erro com rascunho mantido, salvar, atualização/GitHub e limite de viewport.
  Executável e recursos foram auditados. Patch real de 34 arquivos aplicado numa
  instalação simulada, hashes conferidos e configuração pessoal preservada.
- Patches para r2 e r3: aproximadamente 37,7 MB cada; ZIP de transição inclui helper
  e ambas as bases para escolha automática. Não instalado no PC do usuário.

Publicação: GitHub recusou histórico com hashes.game.txt (219 MB). Arquivo
permanece no PC, fora do Git. O histórico antigo permanece na branch local
stability/entry-performance; main é um snapshot limpo para primeira publicação.


Decisão final: assinatura somente no PC, conforme anotação explícita do usuário.
Não enviar a chave privada ao GitHub. CI passa a validar apenas; releases são
preparadas pelo script local. A release privada v1.5.0 foi publicada com quatro
artefatos; GitHub normaliza espaços nos nomes. Hashes e tamanhos serão conferidos.


### 1.5.1 — acesso às atualizações privadas

Usuário forneceu e autorizou configurar o token de leitura compartilhado. Leitura
do repositório, consulta da última release e acesso ao download foram verificados
pela API. Token salvo apenas em assets/update-access.json, ignorado pelo Git.
Valor não registrado nos documentos ou logs. Pacote do grupo inclui o acesso
conforme autorização; a credencial de publicação não é distribuída.

Build local 1.5.1 executou 137 testes gerais, compilação e auditoria. Patch real
aplicado numa instalação simulada com configuração pessoal preservada. Transição
inclui bases r2/r3/1.5.0, para receber o token uma vez; próximas versões podem ser
consultadas e baixadas pelo aplicativo. Chave de assinatura permanece local.


### Correção da transição da instalação real

Screenshot mostrou ausência de update-source.json. O nome Rose Teste 0.3 não era
indício suficiente de instalação incorreta: o atalho SEXO2 aponta para essa pasta.
Executável real é 1.4.7.8 (r1), SHA-256 correspondente à primeira entrega SEXO2.
O pacote anterior só continha r2/r3/1.5.0, causando fallback online indevido.

- Gerado patch assinado r1 → 1.5.1 a partir da base original preservada.
- Todos os 39 arquivos anteriores conferidos na instalação real, sem gravar nela.
- Patch aplicado numa cópia simulada e resultado/arquivos pessoais verificados.
- Helper de transição agora faz preflight e informa necessidade de ZIP compatível
  em versões antigas; não tenta ler arquivo de atualização ausente.
- Três testes novos cobrem instalação ausente, base antiga sem pacote e uso local.
- Pacote adicional SEXO2-Transicao-r1.zip contém helper corrigido e somente o
  patch compatível. O helper instalado dentro de 1.5.1 mantém o build canônico,
  para corresponder à baseline e aos próximos deltas; a correção do helper no
  código entra no próximo build normal.

### Cinco tarefas e compatibilidade retroativa — 13/10/2026

Plano detalhado em PLANO_CINCO_TAREFAS.md. Importação em lote e AirDrop continuam
pendentes: primeiro investigar estabilidade dos mods, abertura lenta e splash
Rose remanescente. Confirmado bloqueio sequencial de hash check + skin sync no
launcher; causa das falhas de mods e origem da tela fullscreen não comprovadas.
Toda entrega deve incluir caminho de atualização para bases antigas suportadas,
preservação de dados e rollback, com assinatura local. Nenhuma instalação ativa
foi alterada nesta investigação.

### Primeira entrega dirigida — 1.5.2

- Origem da tela da screenshot localizada em CSS embutido no core.dll: seletor
  index_loading_div, profile-icons/7.jpg e content Rose. Novo plugin SEXO2-Startup
  substitui exatamente esse estilo usando Galo embutido, sem bridge/rede. Teste
  headless valida inclusive CSS antigo inserido depois. Não recompilar core nem
  prometer ausência de primeiro frame antigo: ordem real deve ser conferida no LoL.
- Consultas de commits dos nove hashes limitadas a três simultâneas, cada uma com
  sessão própria. Correção da detecção de HTTP 403/429 com Response false.
- Medições das etapas de abertura. Logs anteriores mostraram 9–11 s na etapa de
  skins; a melhoria dos hashes não resolve sozinha esse gargalo. Mover manutenção
  para segundo plano continua pendente, exigindo publicação atômica/controle de uso.
- Importação de mod de campeão remove destino recém-extraído se o registro falha;
  teste simula disco cheio e preserva mods anteriores/original.
- Geração exige todas as bases registradas, cria deltas diretos e ZIP com helper.
  Novos clientes selecionam asset por versão; versões antigas sem essa lógica usam
  helper de transição externo uma vez se saltarem várias versões. Bases canônicas
  preservadas e nova versão registrada para as próximas entregas.
- Ainda pendentes: diagnóstico causal de crashes/RAM, abertura fora da manutenção,
  biblioteca/lote/exportação e AirDrop. Não aplicar atualização automaticamente no
  PC durante desenvolvimento; entrega é pacote em lugar, sem instalador.

### Atualização sem fechar LoL — 1.5.3

Pedido do usuário: retirar fechamento do LoL, como no Rose. Removidos os quatro
nomes de processos League da barreira de atualização; apenas SEXO2/Rose precisa
estar fechado para substituir seu executável. Textos do helper/pacote/release
ajustados. Testes verificam client e partida abertos, nenhuma chamada de kill ou
terminate, e proteção contra SEXO2/Rose ativo. Helper externo novo necessário uma
vez para superar a exigência presente no helper antigo; novas atualizações pelo
painel passam a permitir o LoL aberto. Não tocar na instalação ativa automaticamente.

### 1.5.4 — memória dos modpkg e abertura com biblioteca existente

- Extração de arquivos/chunks em blocos de até 1 MiB, sem materializar o conteúdo
  completo. Tamanho e XXH3-64 preservados; saída temporária só substitui destino
  depois de validada. Em caso de corrupção/disco cheio, preservar arquivo anterior.
- Hash de conteúdo da sala também usa blocos e mantém identidade entre pacote e
  pasta importada. iter_files continua disponível para compatibilidade.
- Ensaio de arquivo de 32 MiB: alocações Python de 32 MiB (raw) / 64 MiB (zstd)
  caíram para aproximadamente 2,1 MiB. Não representa todo o RSS nem prova que todos
  os crashes da partida foram resolvidos; Zstandard ainda usa memória nativa.
- Checkpoint da biblioteca somente após preparação bem-sucedida. Próximas aberturas
  usam marcadores/revisão/estatísticas locais; arquivo ausente/alterado invalida-o.
- Consulta em segundo plano somente lê revisões e agenda novidades para próxima
  abertura. Não extrai nem substitui skins durante uso. Hash probe sequencial e
  cancelável entre requisições, sem executor que atrase saída do aplicativo.
- Primeiro uso/preparação de novidades ainda pode levar tempo. Em partida ativa,
  manter biblioteca confirmada e adiar manutenção. UI/primeiro frame e desempenho
  no PC real ainda precisam conferência. Biblioteca em lote e AirDrop pendentes.

### 1.6.0 — biblioteca própria em lote e exportação

Implementada biblioteca no painel; detalhes em MODS_E_AIRDROP.md. Adicionar abre
pasta por categoria, com análise e importação serial. Revisão de campeão/skin-base,
alvos editáveis, nomes, remoção, exportação/restauração e originais preservados.
Interrupção por blocos durante seleção/partida, baixa prioridade de recursos no
Windows, histórico de entrada persistente e lista paginada. Corrigido registro de
mods editados para reimportação não esconder a cópia antiga. Autoria/licença de
modpkg guardadas separadamente sem mudar hash de conteúdo usado pela sala.

Não abrir o LoL nem aplicar atualização automaticamente. Sem necessidade de fechar
LoL para atualizar, como desde 1.5.3. Bases antigas continuam com deltas diretos;
chave de assinatura local. AirDrop, conferência visual real e investigação dos
crashes no PC real seguem pendentes.
