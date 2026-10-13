"""One-time branding migration; retain old data paths and relay protocol identity."""
from pathlib import Path
import shutil
from PIL import Image
root=Path(__file__).resolve().parent
image=Path(r'C:/Users/mathe/.codex/generated_images/01a12151-2be8-7022-b3fe-64beb18f1217/exec-92afed7d-de04-491b-a012-da851f655e7e.png')
shutil.copy2(image,root/'assets/bork-blue.png')
# Format conversion for Windows icon resources; artwork created by imagegen.
with Image.open(image)as icon:
    icon.save(root/'assets/sexo2.ico',format='ICO',sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)])
for name in ['icon.png','tray_ready.png','tray_starting.png']:shutil.copy2(image,root/'assets'/name)
shutil.copy2(root/'assets/sexo2.ico',root/'assets/icon.ico')
for path in [root/'config.py',root/'utils/integration/tray_manager.py',root/'main/core/initialization.py',root/'main/__init__.py',*list((root/'Pengu Loader/plugins').rglob('*.js'))]:
    text=path.read_text(encoding='utf-8-sig')
    for old,new in [('Rose r6 · perfis, sorteios e diagnóstico','SEXO2'),('Rose -','SEXO2 -'),('Rose failed','SEXO2 failed'),('Rose crashed','SEXO2 crashed'),('Close Rose','Close SEXO2'),('Rose could not','SEXO2 could not'),('Rose needs','SEXO2 needs'),('Parar Rose','Parar SEXO2'),('Rose parado','SEXO2 parado'),('do Rose','do SEXO2'),('o Rose','o SEXO2'),('ROSE ·','SEXO2 ·'),('ROSE SEM RESPOSTA','SEXO2 SEM RESPOSTA'),('SEXO PARTY r5','SEXO2')]:text=text.replace(old,new)
    if path.name=='tray_manager.py':text=text.replace('f"Rose {FORK_LABEL}', 'f"{FORK_LABEL}').replace('"Rose", image','"SEXO2", image')
    path.write_text(text,encoding='utf-8')
spec=(root/'Rose.spec').read_text().replace("name='Rose'","name='SEXO2'").replace("icon='assets/icon.ico',","icon='assets/sexo2.ico',\n    version='assets/sexo2-version.txt',")
(root/'SEXO2.spec').write_text(spec,encoding='utf-8')
installer=(root/'installer-r6.iss').read_text().replace('#define MyAppName "Rose"','#define MyAppName "SEXO2"').replace('1.4.7.7','1.4.7.8').replace('AppVerName=Rose r6 - painel integrado','AppVerName=SEXO2').replace('DefaultDirName={localappdata}\\Rose Teste 0.3','DefaultDirName={localappdata}\\SEXO2').replace('DefaultGroupName=Rose dos Amigos','DefaultGroupName=SEXO2').replace('..\\rose-r6\\Rose','..\\SEXO2\\SEXO2').replace('OutputDir=..\\rose-r6','OutputDir=..\\SEXO2').replace('OutputBaseFilename=Rose r6 - Instalador','OutputBaseFilename=SEXO2 - Instalador').replace('assets\\icon.ico','assets\\sexo2.ico').replace('{app}\\Rose.exe','{app}\\SEXO2.exe').replace('Name: "{group}\\Rose dos Amigos"','Name: "{group}\\SEXO2"').replace('Name: "{autodesktop}\\Rose dos Amigos"','Name: "{autodesktop}\\SEXO2"').replace('Description: "Abrir Rose"','Description: "Abrir SEXO2"').replace('Name="Rose.exe" OR','Name="SEXO2.exe" OR Name="Rose.exe" OR')
# Preserve backup detection when upgrading a directory that still contains Rose.exe.
installer=installer.replace("FileExists(AddBackslash(AppDir) + 'Rose.exe')", "(FileExists(AddBackslash(AppDir) + 'Rose.exe') or FileExists(AddBackslash(AppDir) + 'SEXO2.exe'))")
installer=installer.replace('[InstallDelete]','[InstallDelete]\nType: files; Name: "{autodesktop}\\Rose dos Amigos.lnk"\nType: files; Name: "{userprograms}\\Rose dos Amigos\\Rose dos Amigos.lnk"')
(root/'installer-sexo2.iss').write_text(installer,encoding='utf-8-sig')
print('SEXO2 branding prepared')
