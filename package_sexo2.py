from pathlib import Path
import hashlib,json,shutil,subprocess,zipfile
root=Path(__file__).resolve().parent;delivery=root.parent/'SEXO2-r3';target=delivery/'SEXO2'
shutil.copytree(root/'dist-sexo2-r3/SEXO2',target,dirs_exist_ok=True)
for name in ['ltk_patcher_host.exe','ltk_patcher_dll.dll']:
    shutil.copy2(root/'injection/tools'/name,target/'_internal/injection/tools'/name)
shutil.copy2(root/'LICENSE',target/'LICENSE-Rose.txt')
for name in ['LICENSE-cloudflared.txt','provenance.json']:
    shutil.copy2(root/'hosting-tools'/name,target/'_internal/hosting-tools'/name)
readme=(root.parent/'rose-r6/Rose/LEIA-ME.txt').read_text(encoding='utf-8').replace('ROSE r6','SEXO2').replace('o Rose','o SEXO2').replace('do Rose','do SEXO2').replace('no Rose','no SEXO2').replace('Rose.exe','SEXO2.exe')
readme += '\nFAVORITAS: abra Skins > Favoritas, busque qualquer campeao e marque as skins. Nao precisa selecionar o campeao numa partida. As escolhas sao salvas automaticamente.\n'
readme += '\nSEXO2 r3 (1.4.7.10): melhorias de recuperacao do jogo, conexao da sala e fila das skins fixadas. O novo formulario e os novos icones ainda nao fazem parte desta versao.\n'
(target/'LEIA-ME.txt').write_text(readme,encoding='utf-8')
manifest={str(p.relative_to(target)):hashlib.sha256(p.read_bytes()).hexdigest()for p in target.rglob('*')if p.is_file()and p.name!='manifesto.json'}
(target/'manifesto.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
subprocess.run([r'Z:\mathe\Arquivos de Programas\Inno Setup 6\ISCC.exe',str(root/'installer-sexo2.iss')],check=True,stdout=(root/'installer-sexo2.log').open('w'))
exe=delivery/'SEXO2 - Instalador.exe';digest=hashlib.sha256(exe.read_bytes()).hexdigest()
(delivery/'Instalador.sha256.txt').write_text(digest+'  '+exe.name+'\n',encoding='utf-8')
instructions='SEXO2\n\nExtraia o ZIP e execute SEXO2 - Instalador.exe.\nFeche Rose/SEXO2 e o cliente LoL antes de instalar.\nDepois abra SEXO2 e reabra o cliente LoL.\nClique no BORK da barra superior para acessar o painel.\nEm Sala, crie a sala ou cole o link recebido.\nO anfitriao precisa manter SEXO2 aberto e o PC ligado.\nAutoaceite fica desligado por padrao.\nDados anteriores sao preservados; nenhuma configuracao pessoal foi incluida neste ZIP.\n'
(delivery/'COMO-INSTALAR.txt').write_text(instructions,encoding='utf-8')
archive=delivery/'SEXO2 - Instalador para compartilhar.zip'
with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_STORED)as z:
    for file in [exe,delivery/'COMO-INSTALAR.txt',delivery/'Instalador.sha256.txt']:z.write(file,file.name)
with zipfile.ZipFile(archive)as z:
    assert z.testzip()is None
    assert hashlib.sha256(z.read(exe.name)).hexdigest()==digest
print(archive);print('ZIP verified:',archive.stat().st_size)
