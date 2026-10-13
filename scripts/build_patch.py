"""Signed file delta builder; private signing key never enters the payload."""
import argparse,json,os,sys,zipfile
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from sexo2.update.engine import digest,PROTECTED,target

def build(base,new,output,version,key):
    base=Path(base).resolve();new=Path(new).resolve();files={}
    for path in sorted(new.rglob('*')):
        if not path.is_file()or path.name.lower()in PROTECTED or path.name=='manifesto.json':continue
        name=path.relative_to(new).as_posix()
        if name.lower().startswith('unins')or name.startswith('.sexo2-update/'):continue
        target(new,name);previous=base/name;old=digest(previous)if previous.is_file()else None;current=digest(path)
        if old!=current:files[name]={'old':old,'new':current}
    raw=json.dumps({'schema':1,'app':'SEXO2','version':version,'files':files},sort_keys=True,separators=(',',':')).encode()
    signature=Ed25519PrivateKey.from_private_bytes(key).sign(raw);output=Path(output);output.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED,compresslevel=3)as z:
        z.writestr('manifest.json',raw);z.writestr('manifest.sig',signature)
        for name in files:z.write(new/name,'payload/'+name)
    with zipfile.ZipFile(output)as z:assert z.testzip()is None
    return len(files)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--base',required=True);p.add_argument('--new',required=True);p.add_argument('--output',required=True);p.add_argument('--version',required=True);p.add_argument('--key-file');a=p.parse_args()
    key=Path(a.key_file).read_bytes()if a.key_file else bytes.fromhex(os.environ['SEXO2_SIGNING_KEY_HEX'])
    print('Changed files:',build(a.base,a.new,a.output,a.version,key))
