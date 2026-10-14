# Mods em lote e AirDrop pela sala

Pedido de 13/10/2026: reduzir o trabalho de adicionar mods do Runeforge, permitir
exportar toda a biblioteca e transferir mods pela sala usando o túnel existente.
A imagem mostra o seletor legado atrás do painel; substituir esse fluxo na tela
própria, não apenas reposicionar janelas.

## Importação e biblioteca

Um gerenciador próprio dentro do painel. Adicionar abre uma pasta de entrada;
usário pode colar vários .fantome/.modpkg/.zip. Leitura leve dos metadados e índice
do pacote antes de extrair, fila de importação fora da UI e progresso por arquivo.
Não analisar arquivo enquanto está sendo copiado; preservar original e ignorar
conteúdo duplicado. Nenhuma extração completa apenas para descobrir campeão.

Identificação: dados explícitos de campeões no pacote; alvos WAD e caminhos de
personagem; nomes do mod/arquivo como último recurso. Indexar IDs oficiais,
aliases internos e nomes exibidos. Exemplo de falso positivo a evitar: Vi em
Silver, Ashe em outras palavras. Múltiplos alvos ou sinais contraditórios devem
ir para revisão; não escolher um campeão silenciosamente. Detectar também a
skin-base/alvos quando disponíveis; o importador atual já guarda target_skin_ids.

Não há garantia de um identificador universal presente em todo download do
Runeforge. O formato modpkg possui campo de campeões; fantome estendido pode
incluí-lo em META/info.json, mas arquivos antigos podem omiti-lo.

Exportar todos: pacote portátil com arquivos, nomes, campeões, alvos, versões,
metadados/créditos e manifesto de integridade. Reimportação restaura a biblioteca,
sem exportar configurações do LoL, links de sala ou credenciais de atualização.

## AirDrop

Hoje a sala compartilha hashes/seleções e só encontra mods já existentes no PC
do destinatário. FriendsRelay usa frames limitados a 64 KiB; não é canal pronto
para enviar um arquivo grande inteiro. Preservar mensagens de seleção/reconexão.

Nova transferência autenticada separada, reutilizando o mesmo túnel/sessão.
Enviar mod específico para um participante ou sala; receber com progresso,
aceitação ou preferência explícita de recebimento automático nessa sala.
Transferir somente arquivos ausentes, identificar conteúdo por hash e conferir
SHA-256 do pacote completo. Blocos limitados, controle de pressão, cancelamento,
retomada e limite de banda/concorrência. O anfitrião encaminha; não precisa de VPN
ou porta aberta. Se ele fechar o app, a transferência é interrompida/retomada
quando possível; não prometer armazenamento permanente na Cloudflare.

Depois do recebimento, usar o mesmo importador. Não modificar skins/aplicação
em partida em andamento; preparar para próxima aplicação permitida.
Começar por envio manual de um mod, depois sincronizar os mods selecionados da
sala; sincronizar biblioteca inteira deve ser opção, não comportamento padrão.

## Ordem

1. Medir fluxo atual; biblioteca/importador em lote próprios e exportação.
2. AirDrop de um mod pela sala, sem degradar mensagens ou entrada em partida.
3. Recebimento automático opt-in e sincronização seletiva da biblioteca.

Referências:
- https://wiki.leaguetoolkit.dev/making-mods/mod-projects/
- https://github.com/LeagueToolkit/docs/blob/main/Mod-Package-Format.md
- https://developers.cloudflare.com/cloudflare-one/faq/cloudflare-tunnels-faq/

## Implementação da biblioteca — 1.6.0

Um único acesso Biblioteca de mods em Configurações. Os controles Adicionar e
Gerenciar legados deixam de abrir seletores sobrepostos. Dentro da biblioteca:
entrada por categoria, busca/paginação de 50 itens, revisão de campeão e skin-base,
renomeação, edição de múltiplos alvos, remoção com confirmação dentro do painel,
exportação e pasta de exportações. Favoritas de skins oficiais continuam no painel
Skins existente; não confundir skin-base de mod com favorita oficial.

Identificação sem extrair conteúdo completo: metadados, WAD/characters e tokens
inteiros no nome. Conflitos ficam para revisão. Campo de alvos explícito preservado;
sem esse campo, sugerir base padrão, com edição disponível no catálogo do client.
Não prometer detecção universal nem compatibilidade sem testar o mod no jogo.

Observador serial, arquivos estáveis em duas leituras, originais mantidos. Pastas
separadas para categorias; ZIP com .fantome/.modpkg dentro prepara esses arquivos
sem exigir descompactação manual. Pasta externa única normalizada para WAD/RAW;
ZIP sem dados de mod rejeitado. Interrupção por blocos de 1 MiB na seleção/partida;
retentativa, histórico persistente e pausa do observador após inatividade. Worker
usa processamento de fundo do Windows. Não alterar prioridade do LoL.

Hashes reaproveitados apenas com arquivos iguais; conteúdo editado reindexado sem
ocultar a cópia antiga. Alvos novos de mod idêntico são combinados. Temporários
não entram na listagem. Marcadores, nomes, alvos e arquivo de entrada não somem
quando um pacote falha. Um trabalho lento não bloqueia status do bridge.

Exportação: ZIP portátil com pacotes, manifesto de SHA-256, nomes, categorias e
alvos. META e créditos dos mods mantidos; autoria/licença do modpkg guardadas em
arquivos de metadados separados e exportadas junto. Sem config, preferências,
credenciais ou links de sala do aplicativo. Restauração verifica todos os pacotes
antes de importar, preserva os existentes e confere espaço livre.

AirDrop/transporte de arquivos pela sala ainda não implementado. Usará este mesmo
importador/manifesto; não transmitir o arquivo inteiro nos frames atuais da sala.

Fontes técnicas conferidas:
- https://github.com/LeagueToolkit/league-mod/blob/main/docs/design/modpkg.md
- https://wiki.leaguetoolkit.dev/making-mods/mod-projects/
- https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-setthreadpriority
