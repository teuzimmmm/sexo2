import json,threading,unicodedata
from pathlib import Path
from utils.core.atomic_file import atomic_write

class Preferences:
    def __init__(self,path):
        self.path=Path(path);self.lock=threading.RLock();self.error=None
        self.data={'version':2,'profiles':{},'active_profile':None,'excluded':[], 'favorites':{}, 'automatic':'off'}
        try:
            raw=json.loads(self.path.read_text(encoding='utf-8'))
            if not isinstance(raw,dict)or raw.get('version')not in (1,2) or not isinstance(raw.get('profiles'),dict):raise ValueError('Formato desconhecido')
            profiles={}
            for name,skins in raw['profiles'].items():
                name=self.name(name);profiles[name]=self.skins(skins)
            excluded=raw.get('excluded',[])
            if not isinstance(excluded,list)or any(type(x)is not int or x<=0 for x in excluded):raise ValueError('Lista de exclusões inválida')
            active=raw.get('active_profile')
            favorites=raw.get('favorites',{})
            if not isinstance(favorites,dict) or len(favorites)>500:raise ValueError('Favoritas inválidas')
            for cid,ids in favorites.items():
                if not isinstance(ids,list) or len(ids)>200 or any(type(s)is not int or s//1000!=int(cid) for s in ids):raise ValueError('Favoritas inválidas')
            mode=raw.get('automatic','off')
            if mode not in ('off','favorite','random','favorites'):raise ValueError('Modo automático inválido')
            self.data={'version':2,'profiles':profiles,'active_profile':active if active in profiles else None,'excluded':sorted(set(excluded)), 'favorites':favorites, 'automatic':mode}
        except FileNotFoundError:pass
        except (ValueError,TypeError,KeyError,OSError)as e:self.error='Não foi possível ler suas preferências. O arquivo foi preservado: '+str(e)

    @staticmethod
    def name(value):
        if not isinstance(value,str):raise ValueError('Dê um nome ao perfil')
        name=unicodedata.normalize('NFC',value).strip()
        if not 1<=len(name)<=50 or any(ord(c)<32 for c in name):raise ValueError('O nome deve ter de 1 a 50 caracteres')
        return name
    @staticmethod
    def skins(value):
        if not isinstance(value,dict)or len(value)>500:raise ValueError('Conjunto de skins inválido')
        result={}
        for key,pick in value.items():
            cid=int(key)
            if cid<=0 or not isinstance(pick,dict):raise ValueError('Campeão inválido')
            sid=pick.get('skinId')
            if type(sid)is not int or sid//1000!=cid:raise ValueError('A skin não pertence ao campeão')
            result[str(cid)]={'skinId':sid,'name':str(pick.get('name',sid))[:150]}
        return result
    def snapshot(self):
        with self.lock:return json.loads(json.dumps(self.data))
    def update(self,mutate):
        with self.lock:
            if self.error:raise ValueError(self.error)
            data=self.snapshot();mutate(data)
            self.path.parent.mkdir(parents=True,exist_ok=True)
            if self.path.exists():
                previous=self.path.read_bytes()
                if json.loads(previous).get('version')==1:
                    migration=self.path.with_suffix('.v1-migration.json')
                    if not migration.exists():
                        with atomic_write(migration,'wb')as backup:backup.write(previous)
                with atomic_write(self.path.with_suffix('.json.bak'),'wb') as backup:backup.write(self.path.read_bytes())
            with atomic_write(self.path)as f:json.dump(data,f,ensure_ascii=False,indent=2)
            self.data=data
            return self.snapshot()
    def save_profile(self,name,skins):
        name=self.name(name);skins=self.skins(skins)
        if not skins:raise ValueError('Escolha ao menos uma skin para salvar')
        def change(data):
            if name not in data['profiles']and len(data['profiles'])>=30:raise ValueError('Limite de 30 perfis atingido')
            data['profiles'][name]=skins
        return self.update(change)
    def activate(self,name):
        def change(data):
            if name is not None and name not in data['profiles']:raise ValueError('Perfil não encontrado')
            data['active_profile']=name
        return self.update(change)
    def delete(self,name):
        def change(data):
            if name not in data['profiles']:raise ValueError('Perfil não encontrado')
            del data['profiles'][name]
            if data['active_profile']==name:data['active_profile']=None
        return self.update(change)
    def exclusions(self,ids):
        if not isinstance(ids,list)or len(ids)>1000 or any(type(x)is not int or x<=0 for x in ids):raise ValueError('Exclusões inválidas')
        return self.update(lambda data:data.update(excluded=sorted(set(ids))))

    def automatic(self,mode):
        if mode not in ('off','favorite','random','favorites'):raise ValueError('Modo desconhecido')
        return self.update(lambda data:data.update(automatic=mode,active_profile=None))

    def favorite(self,cid,sid,enabled):
        if type(cid)is not int or type(sid)is not int or sid//1000!=cid:raise ValueError('Favorita inválida')
        def change(data):
            ids=set(data.setdefault('favorites',{}).get(str(cid),[]))
            if enabled:ids.add(sid)
            else:ids.discard(sid)
            data['favorites'][str(cid)]=sorted(ids)
        return self.update(change)

    def restore_backup(self):
        backup=self.path.with_suffix('.json.bak');restored=Preferences(backup)
        if restored.error or not backup.exists():raise ValueError('Não há backup válido para restaurar.')
        if self.path.exists():
            import time
            preserved=self.path.with_name(self.path.name+'.preservado-'+str(time.time_ns()))
            with atomic_write(preserved,'wb') as stream:stream.write(self.path.read_bytes())
        with atomic_write(self.path,'wb') as stream:stream.write(backup.read_bytes())
        self.data=restored.snapshot();self.error=None
