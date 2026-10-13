"""Assemble update and baseline; no installer is produced."""
import argparse,json,shutil,zipfile
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--base',required=True);p.add_argument('--new',required=True);p.add_argument('--helper',required=True);p.add_argument('--version',required=True);p.add_argument('--output',required=True);a=p.parse_args()
base=Path(a.base);new=Path(a.new);output=Path(a.output);output.mkdir(parents=True,exist_ok=True)
shutil.copy2(a.helper,new/'SEXO2 Update.exe')
for name in ['ltk_patcher_host.exe','ltk_patcher_dll.dll']:
    shutil.copy2(base/'_internal/injection/tools'/name,new/'_internal/injection/tools'/name)
(new/'sexo2-release.json').write_text(json.dumps({'version':a.version.removeprefix('v'),'app':'SEXO2'}),encoding='utf-8')
for source,dest in [('LICENSE','LICENSE-Rose.txt'),('hosting-tools/LICENSE-cloudflared.txt','_internal/hosting-tools/LICENSE-cloudflared.txt'),('hosting-tools/provenance.json','_internal/hosting-tools/provenance.json')]:
    shutil.copy2(source,new/dest)
with zipfile.ZipFile(output/'SEXO2-baseline.zip','w',zipfile.ZIP_DEFLATED,compresslevel=3)as z:
    for file in new.rglob('*'):
        if file.is_file()and file.name not in {'hashes.game.txt','manifesto.json'}:z.write(file,file.relative_to(new))
shutil.copy2(new/'SEXO2 Update.exe',output/'SEXO2 Update.exe')
