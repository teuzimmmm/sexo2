"""Generate locally signed direct updates for every supported baseline."""
import argparse, json, re, sys, zipfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.build_patch import build
from sexo2.update.engine import digest


def generate(registry, new, output, version, key):
    project=Path(__file__).resolve().parents[1]
    bases=json.loads(Path(registry).read_text(encoding='utf-8'))
    resolved={}
    for label, folder in bases.items():
        if label == version:
            continue
        if not re.fullmatch(r'(?:r[0-9]+|[0-9]+\.[0-9]+\.[0-9]+)',label):
            raise ValueError('Invalid baseline label')
        root=(project/folder).resolve()
        if not (root/'SEXO2.exe').is_file():
            raise ValueError('Missing supported baseline: '+label)
        resolved[label]=root
    output=Path(output); output.mkdir(parents=True,exist_ok=True)
    entries=[]
    for label, root in resolved.items():
        name='SEXO2-update-from-'+label+'.zip'
        count=build(root,new,output/name,version,key)
        entries.append({'base':label,'executableSha256':digest(root/'SEXO2.exe'),'asset':name,'changedFiles':count})
    (output/'compatibility-report.json').write_text(json.dumps({'version':version,'bases':entries},indent=2),encoding='utf-8')
    helper=Path(new)/'SEXO2 Update.exe'
    if not helper.is_file(): raise ValueError('Updater helper missing')
    with zipfile.ZipFile(output/('SEXO2-Atualizacao-'+version+'.zip'),'w',zipfile.ZIP_DEFLATED,compresslevel=3) as archive:
        archive.write(helper,'SEXO2 Update.exe')
        for entry in entries: archive.write(output/entry['asset'],entry['asset'])
        archive.writestr('LEIA-ME.txt','Extraia este ZIP inteiro em uma pasta. Feche apenas SEXO2; o LoL pode permanecer aberto. Abra SEXO2 Update.exe e escolha a pasta instalada. O pacote compativel e escolhido automaticamente. Nao extraia os ZIPs internos. Nao reinstala nem apaga seus mods/configuracoes.')
    # Preserve the canonical new baseline for all subsequent releases.
    try:
        baseline=Path(new).resolve().relative_to(project).as_posix()
    except ValueError:
        baseline=str(Path(new).resolve())
    bases[version]=baseline
    Path(registry).write_text(json.dumps(bases,indent=2)+'\n',encoding='utf-8')
    return entries

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--registry',default='scripts/compatibility_bases.json');parser.add_argument('--new',required=True);parser.add_argument('--output',required=True);parser.add_argument('--version',required=True);parser.add_argument('--key-file',required=True);args=parser.parse_args()
    if not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+',args.version): raise ValueError('Invalid version')
    entries=generate(args.registry,args.new,args.output,args.version,Path(args.key_file).read_bytes())
    print('Supported direct updates:',len(entries))
