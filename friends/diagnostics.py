import json,re,zipfile
from datetime import datetime
from pathlib import Path
from utils.core.atomic_file import atomic_write

def sanitize(text,secrets=()):
    text=str(text)
    for secret in sorted((str(s)for s in secrets if s),key=len,reverse=True):text=text.replace(secret,'<removido>')
    text=re.sub(r'(?:https?|wss?)://[^\s<>"\']+','<endereço removido>',text,flags=re.I)
    text=re.sub(r'#rose=[A-Za-z0-9_-]+','#rose=<removido>',text,flags=re.I)
    text=re.sub(r'(?i)(authorization[\"\']?\s*[:=]\s*[\"\']?)(?:basic|bearer)\s+[^\"\'\s,}]+',r'\1<removido>',text)
    text=re.sub(r'(?i)((?:password|passwd|token|secret|relay_access|room_key)\s*["\']?\s*[:=]\s*["\']?)[^\s,"\'}]+',r'\1<removido>',text)
    text=re.sub(r'(?i)([?&](?:access|key|token|auth|password)=)[^&\s]+',r'\1<removido>',text)
    text=re.sub(r'(?i)(?:LeagueClient|RiotClientServices):\d+:\d+:[^:\s]+:https?', '<credencial do cliente removida>', text)
    text=re.sub(r'(?i)\broom\s+\S+','room <removido>',text)
    text=re.sub(r'(?i)(?:[A-Z]:[\\/]|/Users/|/home/)[^\r\n]*','<caminho removido>',text)
    text=re.sub(r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}','<email removido>',text)
    lines=[]
    for line in text.splitlines():
        if re.search(r'(?i)\[PARTY\]|summoner|puuid|username|riot.?id|account.?name|player.?name',line):lines.append('<evento de participante removido>')
        else:lines.append(line)
    return '\n'.join(lines)

def export_report(directory,snapshot,log_dir,secrets=()):
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    name='Rose-diagnostico-'+datetime.now().strftime('%Y%m%d-%H%M%S-%f')+'.zip'
    target=directory/name
    # Report deliberately excludes player names, IDs, preferences and server links.
    summary={k:snapshot.get(k)for k in ('version','phase','queueId','readiness')}
    summary['participants']=[{'participant':i+1,'connected':p.get('connected',False),'sameLobby':p.get('sameLobby',False),'skinReceived':p.get('skinReceived',False)}for i,p in enumerate(snapshot.get('members',[]))]
    files=sorted(Path(log_dir).glob('rose_*.log'),key=lambda p:p.stat().st_mtime,reverse=True)[:1]
    recent='Nenhum log disponível.'
    if files:
        with files[0].open('rb')as f:
            size=files[0].stat().st_size;f.seek(max(0,size-256000));recent=f.read().decode('utf-8',errors='replace')
        recent='\n'.join(recent.splitlines()[-1500:])
    with atomic_write(target,mode='wb')as stream:
        with zipfile.ZipFile(stream,'w',compression=zipfile.ZIP_DEFLATED)as archive:
            def clean(value):
                if isinstance(value,str):return sanitize(value,secrets)
                if isinstance(value,list):return [clean(v)for v in value]
                if isinstance(value,dict):return {key:clean(val)for key,val in value.items()}
                return value
            archive.writestr('resumo.json',json.dumps(clean(summary),ensure_ascii=False,indent=2))
            archive.writestr('log_recente.txt',sanitize(recent,secrets))
            archive.writestr('LEIA-ME.txt','Relatório local sanitizado. Não inclui config.ini, lockfile, chave da sala ou arquivos de skins. A verificação de preparo não confirma aplicação em partida.')
    return target
