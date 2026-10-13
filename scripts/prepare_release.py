"""Restore build-only binaries from our previous release; never overwrite source plugins."""
import argparse,json,os,shutil,re
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--base',required=True);p.add_argument('--version',required=True);a=p.parse_args()
base=Path(a.base)/'_internal';version=a.version.removeprefix('v')
if not re.fullmatch(r'\d+\.\d+\.\d+',version):raise SystemExit('Invalid release version')
for folder in ['Pengu Loader','injection/tools','hosting-tools']:
    for file in (base/folder).rglob('*'):
        if file.is_file()and file.suffix.lower()in {'.exe','.dll','.bat'}:
            dest=Path(folder)/file.relative_to(base/folder);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(file,dest)
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding,PublicFormat
key=bytes.fromhex(os.environ['SEXO2_SIGNING_KEY_HEX']);pub=Ed25519PrivateKey.from_private_bytes(key).public_key().public_bytes(Encoding.Raw,PublicFormat.Raw)
Path('sexo2/update/trust.py').write_text('PUBLIC_KEY = bytes.fromhex('+repr(pub.hex())+')\n',encoding='utf-8')
repo=os.environ['GITHUB_REPOSITORY'];Path('assets/update-source.json').write_text(json.dumps({'repository':repo,'channel':'stable','private':True}),encoding='utf-8')
token=os.environ.get('SEXO2_DOWNLOAD_TOKEN','')
if token:Path('assets/update-access.json').write_text(json.dumps({'token':token}),encoding='utf-8')
p=Path('sexo2/update/client.py');s=p.read_text(encoding='utf-8');s=re.sub(r"RELEASE_VERSION = '[^']+'",'RELEASE_VERSION = '+repr(version),s);p.write_text(s,encoding='utf-8')
p=Path('assets/sexo2-version.txt');s=p.read_text(encoding='utf-8');s=re.sub(r'\(1,5,0,0\)','('+version.replace('.',',')+',0)',s);s=s.replace('1.5.0.0',version+'.0');p.write_text(s,encoding='utf-8')
