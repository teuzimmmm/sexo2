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

Confirmado: launcher/ui/update_dialog.py já usa SEXO2 e galo.png. ROSE-UI corrige
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
