"""GitHub Releases transport. Shared read-only access can be bundled by owner."""
import json
import re
import sys
from pathlib import Path
import requests

RELEASE_VERSION = '1.5.0'

def assets_root():
    return Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parents[2]))/'assets'


def configuration():
    base=assets_root()
    source=json.loads((base/'update-source.json').read_text(encoding='utf-8'))
    access=base/'update-access.json'
    token=json.loads(access.read_text(encoding='utf-8')).get('token','') if access.exists() else ''
    repository=source.get('repository','')
    if repository and not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',repository):
        raise ValueError('Endereço do repositório inválido.')
    return repository, token


def headers(token='',binary=False):
    result={'Accept':'application/octet-stream' if binary else 'application/vnd.github+json',
            'X-GitHub-Api-Version':'2022-11-28','User-Agent':'SEXO2-Updater'}
    if token:result['Authorization']='Bearer '+token
    return result


def version(value):
    value=value.removeprefix('v')
    if not re.fullmatch(r'\d+\.\d+\.\d+',value):raise ValueError('Versão de atualização inválida.')
    return tuple(map(int,value.split('.')))


def check_release(repository=None,token=None,current=RELEASE_VERSION):
    if repository is None:repository,token=configuration()
    if not repository:return {'configured':False,'available':False,'version':current,'message':'O repositório do projeto ainda não foi conectado.'}
    url='https://api.github.com/repos/'+repository+'/releases/latest'
    response=requests.get(url,headers=headers(token),timeout=(3,8),allow_redirects=False)
    if response.status_code in (401,403,404):
        return {'configured':True,'available':False,'version':current,'github':'https://github.com/'+repository,'message':'Confira o acesso ao repositório privado e se há uma versão publicada.'}
    if response.status_code!=200:raise ValueError('Não foi possível consultar as atualizações agora.')
    release=response.json(); latest=release.get('tag_name','')
    if release.get('draft') or release.get('prerelease'):raise ValueError('A versão publicada não é uma atualização estável.')
    asset=next((a for a in release.get('assets',[]) if a.get('name')=='SEXO2-update.zip'),None)
    available=version(latest)>version(current) and bool(asset)
    return {'configured':True,'available':available,'version':current,'latest':latest,
            'github':'https://github.com/'+repository,'assetId':asset.get('id') if asset else None,
            'message':('Nova versão disponível: '+latest) if available else 'Você está usando a versão mais recente publicada.'}


def download_asset(repository,token,asset_id,destination):
    if type(asset_id) is not int or asset_id<=0:raise ValueError('Arquivo de atualização inválido.')
    url=f'https://api.github.com/repos/{repository}/releases/assets/{asset_id}'
    # requests drops Authorization on redirects to other hosts. Initial URL is
    # fixed to the GitHub API; no token is sent to an arbitrary manifest URL.
    with requests.get(url,headers=headers(token,True),timeout=(5,30),stream=True) as response:
        if response.status_code!=200:raise ValueError('Não foi possível baixar a atualização.')
        size=0
        try:
            with Path(destination).open('xb') as output:
                for block in response.iter_content(1024*1024):
                    size+=len(block)
                    if size>1024*1024*1024:raise ValueError('Atualização excede o limite.')
                    output.write(block)
        except Exception:
            Path(destination).unlink(missing_ok=True)
            raise
    return destination
