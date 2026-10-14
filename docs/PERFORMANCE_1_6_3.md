# SEXO2 1.6.3 — investigação e alterações

## Pontos encontrados no código

1. FriendsService.archive abria cada ZIP e testzip descompactava o conteúdo inteiro
na primeira consulta. Snapshot/seleção automática usam available para dezenas de
skins. Consulta do painel agora só verifica existência/formato; a skin realmente
aplicada continua recebendo CRC completo, com cache por caminho/tamanho/mtime.
Arena Bravura também verifica a skin escolhida antes de fechar a partida.

2. ZipResolver montava listas de todos os resultados de rglob mesmo usando só o
primeiro. Busca por nome/formas agora para no primeiro resultado, sem mudar ordem
ou os caminhos de fallback existentes.

3. Main loop executava processamento de UI/seleção e escolhia ritmo rápido por
flags antigas durante GameStart/InProgress/Reconnect. Agora somente consome
operações pendentes de ocultar/destruir; não cria UI nem consulta catálogo nesses
estados. Ritmo durante partida: no máximo 4 ciclos/s, em lugar de 20 ou 62,5.
Não altera FPS nem processamento do aplicador, LCU, Arena ou sala em suas threads.

4. initialize_tray_manager ainda esperava 0,2 s mesmo após bandeja não bloqueante
na 1.6.2. Retirada essa espera. Inicialização também respeita state.stop enquanto
aguarda o websocket, permitindo sair sem cliente conectado.

## Atualizador

Validar assinatura, arquivos, compatibilidade e espaço antes de pedir saída.
Reparação de transação anterior só aceita manifesto assinado. Trava de atualização
é adquirida antes dessa fase; pode existir uma pasta auxiliar mesmo se o pacote
for recusado, mas arquivos instalados não são substituídos e o app não é fechado.

Fechamento restrito ao executável SEXO2.exe/Rose.exe dentro da instalação
selecionada. Versões novas atendem a um evento Win32 nomeado por caminho/PID,
sem polling de disco. Tempo de saída limitado; para versão antiga/sem resposta,
terminar apenas esse processo e esperar. Encerrar ferramentas-filhas de mods/túnel
somente quando pertencem a esse processo e seus arquivos estão na instalação
selecionada; evitar órfãos, sem atingir ferramentas externas ou League. Se o jogo ficou pausado pela saída
forçada do antigo aplicador, liberar a pausa; nunca encerrar League/Riot.

Após sucesso, reabrir o executável da mesma pasta, sem shell ou dupla instância.
Após falha com rollback concluído, reabrir a versão anterior. Se o diário de
recuperação ainda existir, não abrir uma instalação parcialmente restaurada.
Se a versão atualizada não abrir, informar separadamente que a atualização já
terminou e orientar o atalho. Dados pessoais, favoritos e mods preservados.

Transição: helpers antigos não ganham esse comportamento antes de ser atualizados.
Para já usar fechamento automático na primeira ida à 1.6.3, executar o helper
novo da pasta/pacote 1.6.3. Depois usar o botão normal no aplicativo.

## Verificações / limites

Testes: evento real do Windows, encerramento por caminho, timeout, jogo preservado,
reabertura sem shell/duplicação, rejeição de pacote antes de fechar, CRC escolhido,
UI ociosa sem perder limpeza, patches retroativos e módulos congelados.
Não atribuir os crashes reais exclusivamente a esses pontos; ainda é necessário
medir processo/jogo em uso real. Não prometer resolver todos os travamentos.

Próximos candidatos que ainda não foram alterados: custo de mkoverlay e merges de
mods grandes, tempo de sincronização inicial, scans do DOM pelos seletores
legados na seleção, catálogo/relatório completos em cada snapshot. Os observers
já param em InProgress; não remover recursos nem reescrever DLL para ganhar
velocidade sem uma medição e validação separadas.

Fontes primárias sobre o sinal Win32:
https://learn.microsoft.com/en-us/windows/win32/api/synchapi/nf-synchapi-createeventw
https://learn.microsoft.com/en-us/windows/win32/api/synchapi/nf-synchapi-openeventw

## Medições locais de conferência

Teste sintético: quatro ZIPs sem compressão, 64 MB descompactados no total.
CRC completo: 0,0458 s; leitura do formato: 0,0006 s. Não usar esses valores como
FPS ou velocidade esperada na biblioteca real. A nova lógica lê todos os bytes
somente do arquivo escolhido/validado, preservando a proteção contra corrupção.

Perfil de importação do código-fonte, sem iniciar app/LoL: import main total
849,78 ms. config consumiu 128,75 ms próprios (213,21 ms com dependências).
Não é medição do EXE congelado nem da sincronização inicial. Sugere que carregamento
de módulos contribui, mas não explica sozinho a abertura de vários segundos;
config/launcher/sincronização continuam candidatos para medir em execução real.
Relatórios locais em test-reports/performance-1.6.3.json e
import-performance-1.6.3.json, sem credenciais ou conteúdo de logs privados.
