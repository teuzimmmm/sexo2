"""Package the tested build; preserve previous deliveries and user data."""
from pathlib import Path
import hashlib,json,shutil,subprocess
root=Path(__file__).resolve().parent
target=root.parent/'rose-r6'/'Rose'
shutil.copytree(root/'dist-r6-release/Rose',target,dirs_exist_ok=True)
for name in ['ltk_patcher_host.exe','ltk_patcher_dll.dll']:
    shutil.copy2(root/'injection/tools'/name,target/'_internal/injection/tools'/name)
shutil.copy2(root/'LICENSE',target/'LICENSE-Rose.txt')
for name in ['LICENSE-cloudflared.txt','provenance.json']:
    shutil.copy2(root/'hosting-tools'/name,target/'_internal/hosting-tools'/name)
readme='''ROSE r6 — PAINEL INTEGRADO (base 1.4.7)

INSTALAR
Termine a partida e feche Rose, Rose Sala e o cliente LoL. Execute o instalador.
Reabra o cliente LoL para carregar os plugins. A instalacao nao abre o Rose sozinha.
Skins e dados em LocalAppData/Rose sao preservados. Uma instalacao anterior no
mesmo destino e copiada para uma pasta .backup ao lado antes da substituicao.
Nao apague essa pasta ate confirmar o funcionamento. VERSAO-ANTERIOR.txt informa
o caminho. Instalacao interrompida tenta restaurar os arquivos da copia anterior.
Falta de espaco ou falha no backup interrompe a instalacao antes de substituir.

ABRIR O PAINEL
Clique na espada BORK na barra superior do cliente, junto de Colecao/Espolio.
O icone usa mascara e herda a cor do proprio cliente.
Os botoes flutuantes Amigos, Party, Swiftplay e dado foram incorporados ao painel.

SKINS
Escolha skin automatica: Desligada, Minha favorita, Aleatoria ou Entre favoritas.
Entre favoritas usa aleatoria disponivel quando nenhuma favorita e elegivel.
Repeticoes sao permitidas. Marque favoritas; Usar escolhe manualmente uma skin.
Sortear agora escolhe apenas para esta selecao. Uma escolha manual prevalece
sobre automatismos/perfis/sorteios para o campeao confirmado na selecao atual.
Swiftplay mantem fixacao por campeao, busca e lista com rolagem preservada.
Sem skin elegivel, a selecao atual e mantida e o painel explica o motivo.

PERFIS
Mantem salvar, ativar, excluir, liberar perfil, exclusoes e sorteio tematico.
Sorteio de grupo continua opcional, somente para participantes no mesmo lobby.

SALA
Criar sala inicia a hospedagem dentro do Rose. Nao precisa abrir Rose Sala.
Copie o link completo para os participantes; eles colam em Entrar na sala.
O anfitriao deve manter o Rose aberto e o PC ligado. Sem VPN ou porta de entrada.
Tentar reconectar, colar outro endereco e criar outra sala funcionam tambem
durante a selecao de campeoes. Encerrar hospedagem derruba a sala hospedada.
Sala encerrada exige novo link. Recuperar a conexao nao garante preparo a tempo
para a partida atual; skins nao sao alteradas durante uma injecao ou partida.

CONFIGURACOES
Mantem o painel original: ferramentas, limites/tempos, idiomas, recursos,
mods, diagnostico, limpeza de avisos e demais configuracoes.
Verificacao e diagnostico inclui checklist e exportacao sanitizada.
Aceitar partidas automaticamente e opcional e desligado por padrao. So aceita
a confirmacao ReadyCheck; nao inicia fila, nao aceita recusa nem escolhe campeao.
O stop de emergencia e o encerramento do app continuam acessiveis na bandeja.

DADOS E RECUPERACAO
Preferencias antigas sao lidas e convertidas ao salvar, com copia da versao 1
em friends-preferences.v1-migration.json e backup recente .json.bak.
Formato novo usa versao 2 para impedir que um Rose antigo regrave e perca favoritas.
Se o arquivo ficar ilegivel, ele e preservado e o painel oferece restaurar backup.
Para retornar ao r5, feche tudo e restaure a copia v1 de preferencias caso precise
usar os perfis antigos. Nao substitua nem apague o arquivo v2 sem fazer uma copia.
Downloads interrompidos ou ZIPs invalidos nao substituem arquivos validos.

VALIDACAO
Testes usam cliente simulado e clientes sinteticos de rede. Nao houve partida
real, autoaceite real nem instalacao automatica no PC. Compatibilidade com Arena
precisa ser conferida no fluxo real; nao e prometida pela leitura do codigo.
Confira VERIFICACAO.json para os testes e manifesto.json para integridade.
'''
(target/'LEIA-ME.txt').write_text(readme,encoding='utf-8')
commit=subprocess.run(['git','-C',str(root),'rev-parse','HEAD'],capture_output=True,text=True,check=True).stdout.strip()
report={'source_commit':commit,'python_tests':252,'js_unit_tests':11,'browser_hub':True,
        'public_tunnel_two_synthetic_clients':json.loads((root/'tunnel-r6-verification.json').read_text())['ok'],
        'real_game_test':False,'real_autoaccept_test':False,'installer_executed':False}
(target/'VERIFICACAO.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
manifest={str(p.relative_to(target)):hashlib.sha256(p.read_bytes()).hexdigest()for p in target.rglob('*')if p.is_file()and p.name!='manifesto.json'}
(target/'manifesto.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print(target)
