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
