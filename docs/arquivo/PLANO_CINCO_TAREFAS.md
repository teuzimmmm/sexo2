> Arquivado em 18/10/2026: plano e avanços até a 1.6.4, superados por `docs/ROADMAP.md`. Mantido como histórico; caminhos e versões são os da época.

# Plano das cinco tarefas — 13/10/2026

Estado: investigação e planejamento. Não iniciar importação em lote nem AirDrop
antes de estabilizar preparação de partida e abertura. Não alterar a instalação
ativa durante esse diagnóstico. Mudanças pequenas só após identificar a causa e
verificar o resultado. A screenshot da abertura ainda mostra ROSE e a flor.

## 1. Estabilidade dos mods em PC fraco — prioridade máxima

Confirmado no código: preparação de overlays e monitoramento de suspensão do
processo fazem parte da entrada em partida. O tempo de runoverlay inclui a
partida inteira; não tratá-lo como tempo de travamento. Relato de falhas com mods
é real, mas causa ainda não comprovada.

- [ ] Separar encerramento do jogo, processo suspenso, UI sem resposta e saturação
      de memória/disco. Correlacionar logs por aplicação sem registrar credenciais.
- [ ] Medir importação, leitura/hash, extração, mkoverlay, liberação do jogo e pico
      de memória; comparar sem mod, um mod e conjunto de mods.
- [ ] Validar pacote e conflitos de alvos antes da partida; falha aponta o arquivo
      responsável, sem apagar o original nem desativar tudo silenciosamente.
- [ ] Preparar em fila limitada fora da interface; reutilizar resultado por hash
      do conteúdo + versão do jogo + alvos, invalidando quando qualquer um mudar.
- [ ] Limitar tarefas pesadas concorrentes; não importar/extrair/receber e aplicar
      overlays ao mesmo tempo. Baixa prioridade para transferências em partida.
- [ ] Auditar cancelamento, exceções, limpeza de temporários e liberação do processo
      em todos os caminhos; nenhum cache autoriza ignorar validação de segurança.

Aceite: UI responde durante preparação, falha identifica etapa/mod, cancelamento
libera o processo, cache não aplica overlay incompatível após atualização do LoL.
Teste real em PC fraco ainda necessário; testes simulados não comprovam desempenho.

## 2. Abertura rápida

Confirmado: launcher/core/launcher.py executa HashCheckSequence e SkinSyncSequence
sequencialmente antes de encerrar a janela inicial. Hash check consulta rede;
repo_downloader consulta commit com timeout de 10 s e pode baixar/extrair arquivos.
Não há medida atual que permita prometer quantos segundos serão economizados.

- [ ] Registrar duração de cada etapa e comparar abertura fria/quente/offline.
- [ ] Mostrar interface usando biblioteca local validada; mover manutenção de rede
      para fila de fundo, com estado visível e sem bloquear sala/configurações.
- [ ] Se arquivos essenciais estiverem ausentes/incompatíveis, bloquear somente
      aplicação de skins dependente deles e apresentar progresso/repetição.
- [ ] Índice persistente e cache de versão; evitar varrer biblioteca inteira e
      recalcular hashes sem mudança. Não confundir existência com integridade.
- [ ] Publicar nova biblioteca atomicamente; manter anterior até validação terminar.
- [ ] Não iniciar download, limpeza ou reindexação pesada durante entrada em partida.

Aceite: rede lenta/offline não prende a interface quando há biblioteca válida;
primeiro uso permanece guiado; atualização de dados não mistura versões.

## 3. Abertura SEXO2 + escudo do Galo

Confirmado: launcher/ui/update_dialog.py já usa SEXO2 e galo.png. SEXO2-UI corrige
um welcome modal no shadowRoot de pengu-root. A screenshot é uma tela fullscreen;
a origem exata dessa superfície ainda não foi localizada. Não considerar a troca
do modal como correção comprovada da screenshot.

- [ ] Rastrear recurso/tela no componente realmente carregado e conferir se a
      instalação ativa recebeu o pacote correto; distinguir recurso antigo de cache.
- [ ] Trocar nome e flor na origem por SEXO2 e assets/galo.png, sem depender de
      substituição tardia de texto na tela. Preservar licenças e créditos técnicos.
- [ ] Conferir binários/plugins empacotados, inicialização e retorno ao client.
- [ ] Manter BORK preto no desktop e tom nativo no HUD; Galo só na abertura.

Aceite: não aparece flor/ROSE nessa abertura, mesmo antes de conectar o bridge;
confirmar no client real, além da inspeção dos arquivos do pacote.

## 4. Biblioteca própria: lote, favoritos e exportação

Detalhes em MODS_E_AIRDROP.md. Substituir os diálogos legados atrás do painel.

- [ ] Pasta de entrada para múltiplos arquivos, detectar término da cópia.
- [ ] Ler metadados/caminhos antes de extrair; campeão e skin-base com revisão
      de casos ambíguos; nomes de arquivo são último recurso.
- [ ] Fila com progresso, cancelar, deduplicação por conteúdo e recuperação de falha.
- [ ] Biblioteca única no painel: buscar, adicionar, remover e marcar favoritas.
- [ ] Exportar todos com manifesto/alvos/créditos e reimportar preservando escolhas;
      nunca incluir credenciais ou configurações particulares na exportação.

Aceite: lote misto/duplicado/corrompido não perde arquivos nem bloqueia a interface;
exportação reimportável e nenhum seletor Rose sobreposto ao painel.

## 5. AirDrop pela sala

Hoje a sala transmite seleções/hashes, não arquivos; frame limitado a 64 KiB.
Reutilizar túnel e autenticação, com canal de transferência separado dos eventos.

- [ ] Envio manual de um mod para participante/sala, progresso e aceite do receptor.
- [ ] Blocos limitados, SHA-256 final, limites de tamanho/banda/concorrência,
      cancelamento, temporários e retomada após queda do túnel.
- [ ] Enviar apenas conteúdo ausente; importar pelo mesmo serviço da biblioteca.
- [ ] Não aplicar nem extrair em entrada de partida; preservar reconexão/seleções.
- [ ] Depois: sincronização seletiva e recebimento automático opcional por sala.

Aceite: desconexão não cria mod parcial, biblioteca não importa arquivo inválido,
sala continua respondendo; sem VPN nem abertura de porta no roteador.

## Entrega obrigatória: atualizações retroativas

- [ ] Toda release tem caminho da instalação de cada base suportada à versão atual.
      Não exigir que o amigo aplique cada versão intermediária manualmente.
- [ ] Registrar versão/hash das bases r1/r2/r3/1.5.0/1.5.1 e futuras; gerar deltas
      diretos quando houver baseline disponível. Alternativa: pacote cumulativo de
      arquivos gerenciados com migrações, preservando dados pessoais.
- [ ] Selecionar pacote compatível automaticamente; rejeitar base desconhecida com
      explicação clara, sem sobrescrever arquivos incompatíveis.
- [ ] Testar cada caminho suportado: configurações, favoritos, mods, perfis e sala
      preservados; falha retorna à instalação anterior.
- [ ] Assinar somente neste PC, verificar integridade e publicar no GitHub privado.
- [ ] Distribuir atualização em lugar, sem novo instalador/pastas residuais. Caso
      um updater muito antigo exija transição, fornecer helper externo compatível.

## Ordem de execução e verificações

1. Instrumentar e fechar diagnóstico de estabilidade/abertura; localizar splash.
2. Corrigir ciclo de preparação e abrir UI sem depender da manutenção de rede.
3. Corrigir a abertura na origem e conferir visual real.
4. Biblioteca em lote/exportação, usando os limites e cache definidos antes.
5. AirDrop manual; depois sincronização seletiva.

Para cada etapa: checks dirigidos ao comportamento alterado, pacote retroativo e
rollback. Não recompilar/publicar versão só para declarar o plano concluído.

## Avanço concreto — entrega 1.5.2

Implementado: substituição dirigida do splash por plugin sem bridge, consultas de
hashes com concorrência limitada, métricas de abertura e limpeza de importação
incompleta. Core DLL tem o CSS da tela; primeiro frame/ordem de plugin ainda exigem
conferência no LoL. Logs reais mostraram 9–11 segundos em skin sync, portanto
abertura rápida não está concluída.

Retroatividade: gerador exige todas as bases registradas e preserva a nova
baseline; seleção online por versão nos novos clientes. Helper externo identifica
bases antigas por hash. Não exigir sequência manual de releases intermediárias.

Outro ponto identificado: utils/core/modpkg.py lia arquivos/chunks associados a WADs
e montava seus bytes descomprimidos antes de gravar. Pacotes grandes podem gerar
pico de memória, hipótese relevante para PC fraco; não comprova a origem dos
crashes na partida. Planejar extração em fluxo para disco, mantendo verificação de
checksum/tamanho e remoção de saída parcial. Ainda não mudar esse parser junto
com o primeiro patch: precisa de testes próprios com pacotes reais/compressão.

## Avanço 1.5.4

Extração e hash de modpkg agora em fluxo com validação e saída atômica. Checkpoint
após sincronização permite abertura sem consultas de rede nas aberturas seguintes;
consulta remota só agenda manutenção, sem escrever biblioteca durante uso.
Primeiro uso e novidades ainda exigem preparação. A investigação dos crashes em
partida continua; testes de memória não substituem teste real. Tarefas 4/5 não
iniciadas nessa entrega. Retroatividade e regra de LoL aberto preservadas.

## Avanço 1.6.0

Tarefa 4 implementada e testada em serviço e painel simulado: biblioteca própria,
adição em lote, revisão, gerenciamento e exportação/restauração. Seletores legados
retirados do fluxo de Configurações. Interrupção em blocos e fila de fundo protegem
a entrada em partida; não é promessa de resolver todos os crashes do jogo.
Falta AirDrop (tarefa 5), teste visual no client e validação de desempenho real.

## Arena Bravura — 1.6.1

Rotina específica documentada em ARENA_BRAVURA.md: confirmação -3 do jogador
local, identificação após revelação, skin local e um único reinício/reconexão.
Cliente permanece aberto, proteção persistente por gameId e retorno sem skin
em falha. Validação em partida real continua pendente. Não altera as cinco
frentes anteriores nem promete resolver todos os travamentos.

## Avanço 1.6.2 — bandeja e abertura

Bandeja mostra versão própria, português, sem base de protocolo Rose exposta.
Versionamento próprio centralizado em sexo2/version.py; APP_VERSION antigo
continua apenas como compatibilidade do protocolo existente, sem renomear dados
pessoais ou perder configurações.

set_status não aguarda até cinco segundos pelo backend: guarda o estado e aplica
quando o ícone fica pronto. Estado do backend desacoplado da thread que somente
inicia run_detached; impede criação duplicada. Status repetido não redesenha.

AppStatus não materializa lista de todas as imagens e pastas: existência termina
na primeira imagem/pacote encontrado. Medição local única, consulta antiga seguida
da nova, portanto com diferença de cache de disco: 41 PNGs encontrados, 2,5242 s
na enumeração completa e 0,0147 s na consulta curta, mesmo resultado. Isso é tempo
da verificação, não benchmark da abertura completa ou prova dos crashes.

Testes de ciclo de vida e curto-circuito adicionados. Ainda faltam desempenho em
partida, primeira tela no LoL e AirDrop. Distribuir patches retroativos de todas
as bases, sem instalação nova.

## Avanço 1.6.3

Investigação detalhada em PERFORMANCE_1_6_3.md. Consulta leve de arquivos, CRC
somente na skin aplicada, busca curta, UI ociosa durante partida e sem espera
artificial pela bandeja. Atualizador fecha somente a instalação selecionada e
reabre após sucesso ou rollback completo. Primeiro uso automático exige helper
novo; helpers antigos mantêm comportamento anterior. Crash real ainda pendente.

## Correção 1.6.4 — reconexão do painel

Textos visíveis do painel de skins agora dizem SEXO2. Aviso transitório sai
quando chega uma resposta saudável, mesmo sem alteração dos dados. Consultas de
snapshot perdidas não seguram a reconexão por quinze segundos. Swiftplay retorna
após desconexão mesmo quando o catálogo não mudou; não aparece na aba Favoritas.
Teste integrado inclui queda/volta de conexão, funções existentes e rolagem.
Teste do atualizador normaliza caminhos do Windows (alias curto vs caminho real)
para passar no runner do GitHub; não era falha de reabertura do executável.
