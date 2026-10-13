"""Publish locally signed release artifacts using Git Credential Manager."""
from pathlib import Path
import json,os,subprocess,requests
from urllib.parse import urlparse,quote
result=subprocess.run(['git','credential','fill'],input='protocol=https\nhost=github.com\n\n',text=True,capture_output=True,check=True,env={**os.environ,'GIT_TERMINAL_PROMPT':'0','GCM_INTERACTIVE':'never'})
credential=dict(line.split('=',1)for line in result.stdout.splitlines()if '='in line)
session=requests.Session();session.headers.update({'Authorization':'Bearer '+credential['password'],'Accept':'application/vnd.github+json'})
import argparse,re,sys
parser=argparse.ArgumentParser();parser.add_argument('--version',required=True);parser.add_argument('--folder',required=True);args=parser.parse_args()
version=args.version.removeprefix('v')
if not re.fullmatch(r'\d+\.\d+\.\d+',version):raise ValueError('Invalid version')
project=Path(__file__).resolve().parents[1]
repository=json.loads((project/'assets/update-source.json').read_text(encoding='utf-8'))['repository']
if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',repository):raise ValueError('Invalid repository')
api='https://api.github.com/repos/'+repository+'/releases'
response=session.get(api+'/tags/v'+version,timeout=15)
if response.status_code==404:
    body='SEXO2 '+version+' — atualização na instalação existente.\n\nPacote compilado e assinado localmente. A chave privada permanece no PC. Baixe pelo painel Configurações > Atualizações e feche SEXO2 e LoL antes de aplicar. Dados pessoais são preservados e somente a última recuperação é mantida.'
    notes=Path(args.folder)/'release-notes.md'
    if notes.exists(): body=notes.read_text(encoding='utf-8')
    response=session.post(api,json={'tag_name':'v'+version,'target_commitish':'main','name':'SEXO2 '+version+' — atualização','body':body,'draft':True,'prerelease':False},timeout=20)
response.raise_for_status();release=response.json();upload=release['upload_url'].split('{')[0]
if urlparse(upload).hostname!='uploads.github.com':raise ValueError('Unexpected upload destination')
folder=Path(args.folder);names=['SEXO2-update.zip','SEXO2-baseline.zip','SEXO2 Update.exe']
names += [f.name for f in sorted(folder.glob('SEXO2-update-from-*.zip'))]
names += [f.name for f in sorted(folder.glob('SEXO2-Atualizacao-*.zip'))]
existing={a['name']for a in release.get('assets',[])}
for name in names:
    if name in existing or name.replace(' ','.') in existing:continue
    file=folder/name
    with file.open('rb')as stream:
        response=session.post(upload+'?name='+quote(name),data=stream,headers={'Content-Type':'application/octet-stream','Content-Length':str(file.stat().st_size)},timeout=(10,120))
    response.raise_for_status();print('Uploaded:',name,flush=True)
response=session.patch(api+'/'+str(release['id']),json={'draft':False},timeout=20);response.raise_for_status()
response=session.get(api+'/'+str(release['id']),timeout=20);response.raise_for_status();data=response.json()
assert not data['draft']
import hashlib
actual={a['name']:a for a in data['assets']}
for name in names:
    final=name.replace(' ','.')
    asset=actual.get(name)or actual.get(final)
    assert asset is not None,name
    file=folder/name
    assert asset['size']==file.stat().st_size
    assert asset['digest']=='sha256:'+hashlib.sha256(file.read_bytes()).hexdigest()
(folder/'github-release-verification.json').write_text(json.dumps({'url':data['html_url'],'tag':data['tag_name'],'assets':[{k:a[k]for k in ['id','name','size','digest']}for a in data['assets']]},indent=2),encoding='utf-8')
print('Verified private release:',data['html_url'],flush=True)
