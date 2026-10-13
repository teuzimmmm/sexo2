from pathlib import Path
import shutil,json,hashlib
root=Path.cwd();target=root.parent/'rose-amigos-r5'/'Rose';target.mkdir(parents=True,exist_ok=True)
shutil.copytree(root/'dist-r5-final/Rose',target,dirs_exist_ok=True)
shutil.copytree(root/'dist-sala-r5/Rose Sala',target/'Sala',dirs_exist_ok=True)
for name in ['ltk_patcher_host.exe','ltk_patcher_dll.dll']:shutil.copy2(root/'injection/tools'/name,target/'_internal/injection/tools'/name)
shutil.copy2(root/'LICENSE',target/'LICENSE-Rose.txt')
readme='''ROSE DOS AMIGOS r5 — base 1.4.7

INSTALAR
Depois da partida, feche o Rose antigo, o módulo Rose Sala antigo e o cliente do LoL.
Instale o pacote r5. Seus amigos também precisam atualizar Rose e Sala.
Reabra o cliente para carregar o plugin ROSE-Amigos.
O botão ROSE Amigos aparece à esquerda, no lobby, seleção ou busca de partida.
As versões anteriores foram preservadas. Skins, histórico e pins do Swiftplay permanecem no mesmo local.

1. PREPARO — TUDO PRONTO PARA JOGAR
Confere conexão com o cliente, campeões, confirmação do campeão, aplicador/compatibilidade,
ferramentas, arquivos das skins próprias, dos amigos no mesmo lobby e mod escolhido.
Conferir novamente lê os arquivos atuais. Arquivos ZIP incompletos não contam como disponíveis.
Seu Rose pronto é diferente de todo o grupo pronto: o painel também verifica o servidor e
as confirmações dos demais participantes. Os estados NÃO confirmam aplicação em partida.
Esta verificação não cancela sua busca nem impede que você entre numa partida.
Na fila comum, escolhas de campeão/skin só podem ser conferidas depois de existir seleção.

2. PERFIS
Abra Perfis, nomeie o conjunto e escolha as skins dos campeões atuais.
Salvar inclui as escolhas atuais, pins e histórico de skins oficiais; cromas também são preservados.
Usar perfil aplica a escolha dos campeões atuais ou aguarda que o campeão seja confirmado.
O perfil ativo também serve para campeões seguintes que tenham uma entrada no conjunto.
Em Swiftplay, o perfil usa os dois slots. Não altera skins depois de começar a partida.
Os mods manuais são verificados no preparo, mas não fazem parte dos conjuntos oficiais.
Os perfis e exclusões ficam em LocalAppData\\Rose\\friends-preferences.json, com gravação atômica.
Arquivo ilegível é preservado; escolhas automáticas ficam bloqueadas até resolver o arquivo.

3. SORTEIO COORDENADO
No painel Sorteio, entre para participar. Isso desliga o perfil automático.
Escolha uma temática e clique Sortear grupo. Cada participante no mesmo lobby recebe uma
skin disponível para seus próprios campeões. Quem não entrou no sorteio mantém sua escolha.
Sortear só para mim não altera a escolha dos outros jogadores.
Marque Excluir nas skins indesejadas; as exclusões são salvas para sessões futuras.
Os sorteios usam skins oficiais, sem escolher a skin padrão nem cromas como alternativas aleatórias.
Se não houver uma skin disponível do tema, o painel informa; não troca silenciosamente de temática.
Temas: Qualquer, Arcane, PROJETO, Fliperama, Guardiãs das Estrelas, Curtindo o Verão,
Velho Oeste e Florescer Espiritual. O catálogo vem do cliente instalado, em português/inglês.
Os pedidos de sorteio expiram em 2 minutos e só são aceitos de participantes do lobby identificado.

4. SALA
Veja conexão, mesmo lobby, escolhas recebidas, preparo informado e participação no sorteio.
Participantes antigos ou um módulo Sala antigo não confirmam os novos recursos: atualize todos.
Pronto é o diagnóstico do Rose daquele participante; não é confirmação da injeção no jogo.

5. DIAGNÓSTICO
Gerar diagnóstico sem chave da sala cria um ZIP em LocalAppData\\Rose\\diagnosticos.
Abrir pasta do relatório facilita localizar o arquivo para compartilhar por conta própria.
O relatório contém resumo de preparo e trecho limitado do log, com links/chaves, autorização,
dados de participante, e-mails e caminhos pessoais removidos. Não inclui config.ini, lockfile,
perfis, arquivos das skins nem dados completos da conta. Não envia o relatório automaticamente.

HOSPEDAR SEM VPN OU ABRIR PORTA
Um amigo abre Sala\\Rose Sala.exe e clica Hospedar uma sala.
Compartilha o endereço com os amigos; cada um o cola no módulo e clica Usar este endereço no Rose.
O anfitrião mantém o módulo e o computador ligados. Ao criar outra sessão, compartilhe o endereço novo.
O conector Cloudflare faz conexões de saída; o servidor local só escuta em 127.0.0.1.
Não precisa de domínio, conta Cloudflare, VPN ou regra no roteador/firewall.
TryCloudflare não tem garantia de disponibilidade. Capacidade: 10 conexões por sessão.
O endereço contém a chave de acesso; compartilhe apenas com o grupo.

VALIDAÇÃO
Testes Python e JavaScript aprovados; painel testado em navegador com os botões e seus dados.
Sorteio e saída do sorteio testados entre dois clientes reais do protocolo, em ambiente de teste.
Módulo empacotado testado pela internet, incluindo metadados de preparo e sorteio.
Não foi realizada uma partida real e não foi alterada sua instalação ativa nesta sessão.
Aplicador: mesma cópia LTK do usuário, sem alteração; EOL de build em 18/10/2026 às 04:00 de São Paulo.
O verificador usa o build do jogo para conferir suporte, não apenas a data do calendário.
'''
(target/'LEIA-ME.txt').write_text(readme,encoding='utf-8')
manifest={}
for name in ['Rose.exe','Sala/Rose Sala.exe','Sala/_internal/hosting-tools/cloudflared.exe','_internal/injection/tools/ltk_patcher_host.exe','_internal/injection/tools/ltk_patcher_dll.dll','_internal/Pengu Loader/plugins/ROSE-Amigos/index.js','_internal/Pengu Loader/plugins/ROSE-PartyMode/index.js','_internal/Pengu Loader/plugins/ROSE-SwiftplayPins/index.js']:
 p=target/name;manifest[name]={'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
(target/'manifesto.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print(target)
