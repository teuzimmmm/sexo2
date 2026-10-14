"""Own portable library and serial bulk importer; originals remain in the inbox."""
import copy,hashlib,json,logging,re,shutil,tempfile,threading,time,unicodedata,zipfile
from pathlib import Path
from utils.core.atomic_file import write_text_atomic
from utils.core.modpkg import ModPackage
from utils.core.safe_extract import list_mod_archive,MOD_ARCHIVE_SUFFIXES
from sexo2.update.engine import digest
from party.discovery.custom_mods import mod_hashes


def normalized(value):
    return re.sub(r'[^a-z0-9]+',' ',unicodedata.normalize('NFKD',str(value)).encode('ascii','ignore').decode().lower()).strip()


def display_name(source,metadata=None):
    metadata=metadata or {}
    name=metadata.get('display_name',metadata.get('Name',metadata.get('name')))
    if not isinstance(name,str) or not name.strip():name=re.sub(r'^[0-9a-f]{12}-','',source.stem)
    return name.strip()[:128]


def identify(source,champions):
    """Explicit metadata, then WAD/character paths, then complete name tokens."""
    paths=list_mod_archive(source)
    metadata={}
    if source.suffix.lower()=='.modpkg':
        with ModPackage.open(source) as package:metadata=package.metadata()
    else:
        with zipfile.ZipFile(source) as archive:
            names=[n for n in archive.namelist() if re.search(r'(?:^|/)meta/info\.json$',n.replace(chr(92),'/'),re.I)]
            name=next((n for n in names if n.lower()=='meta/info.json'),names[0] if len(names)==1 else None)
            if name and archive.getinfo(name).file_size<=1024*1024:
                metadata=json.loads(archive.read(name))
    if not isinstance(metadata,dict):metadata={}
    known={int(c['id']):c for c in champions}
    aliases={normalized(value):cid for cid,c in known.items() for value in (c.get('name'),c.get('alias')) if value}
    def resolve(value):
        if isinstance(value,dict):value=value.get('id',value.get('championId',value.get('name')))
        if type(value)is int or isinstance(value,str) and value.isdigit():return int(value) if int(value) in known else None
        return aliases.get(normalized(value))
    explicit=metadata.get('champions',metadata.get('Champions',metadata.get('champion',metadata.get('Champion',[]))))
    values=list(explicit.keys()) if isinstance(explicit,dict) else explicit if isinstance(explicit,list) else [explicit]
    ids={cid for cid in map(resolve,values) if cid}
    path_ids=set()
    for path in paths:
        for match in re.finditer(r'(?:^|/)(?:wad/|characters/)([a-zA-Z0-9_-]+)',path.replace('\\','/'),re.I):
            cid=aliases.get(normalized(match.group(1)))
            if cid:path_ids.add(cid)
    title=' '+normalized(source.stem)+' '
    named={cid for alias,cid in aliases.items() if ' '+alias+' ' in title}
    candidates=ids or path_ids or named
    contradictory=bool(ids and path_ids and ids!=path_ids)
    cid=next(iter(candidates)) if len(candidates)==1 and not contradictory else None
    targets=metadata.get('target_skin_ids',metadata.get('TargetSkinIds',[]))
    if not isinstance(targets,list):targets=[]
    targets=[sid for sid in targets if type(sid)is int and cid and sid//1000==cid]
    return {'championId':cid,'candidates':sorted(candidates|path_ids if contradictory else candidates),
            'targets':targets or ([cid*1000] if cid else []),'displayName':display_name(source,metadata),'reason':'metadados' if ids else 'arquivos' if path_ids else 'nome' if named else 'não identificado'}


class DuplicatePackage(Exception):
    def __init__(self,row):self.row=row


class ModLibrary:
    def __init__(self,storage,directory,champions,busy=lambda:False,publish=lambda data:None):
        self.storage=storage;self.directory=Path(directory);self.champion_provider=champions
        self.busy=busy;self.publish=publish;self.lock=threading.RLock();self.cancel=threading.Event()
        self.inbox=self.directory/'mod-inbox';self.exports=self.directory/'mod-exports'
        self.inbox.mkdir(parents=True,exist_ok=True);self.catalog=[];self.mods=[];self.incoming={}
        self.message='';self.watching=False;self.category='skins';self.stamps={};self.worker=None;self.last_import_path=None;self.watch_deadline=0
        self.index_path=self.directory/'sexo2-mod-library.json'
        try:self.index=json.loads(self.index_path.read_text(encoding='utf-8'))
        except (OSError,ValueError):self.index={}
        if not isinstance(self.index,dict):self.index={}
        saved=self.index.get('_inbox',{})
        self.incoming={key:row for key,row in saved.items() if isinstance(row,dict) and re.fullmatch(r'[0-9a-f]{24}',str(row.get('id') or '')) and isinstance(row.get('file'),str) and isinstance(row.get('stamp'),list)} if isinstance(saved,dict) else {}
        for row in self.incoming.values():
            if row.get('status')=='analisando':row['status']='aguardando'
        self.stamps={row['file']:tuple(row['stamp']) for row in self.incoming.values()}
        self.content_cache={entry['path']:(entry.get('stamp'),entry.get('contentHash')) for entry in self.index.values() if isinstance(entry,dict) and entry.get('path')}

    def save_index(self):
        self.index['_inbox']=copy.deepcopy(self.incoming)
        try:write_text_atomic(self.index_path,json.dumps(self.index))
        except OSError:logging.getLogger(__name__).warning('[MOD_LIBRARY] Local index could not be saved; files retained')

    def file_digest(self,path):
        checksum=hashlib.sha256()
        with Path(path).open('rb') as stream:
            while True:
                self.check_idle();block=stream.read(1024*1024)
                if not block:break
                checksum.update(block)
        return checksum.hexdigest()

    def copy_file(self,source,destination):
        while True:
            self.check_idle();block=source.read(1024*1024)
            if not block:break
            destination.write(block)

    def metadata_path(self,relative):
        folder=self.directory/'mod-metadata';folder.mkdir(exist_ok=True)
        return folder/(hashlib.sha256(relative.encode()).hexdigest()+'.json')

    def capture_metadata(self,source):
        if source.suffix.lower()!='.modpkg':return None
        with ModPackage.open(source) as package:
            result=package.metadata()
            for name,key in ((b'_meta_/license','license_text'),(b'_meta_/readme.md','readme')):
                record=package._meta_file(name)
                if record and record.uncompressed_size<=1024*1024:result[key]=package.read(record).decode('utf-8',errors='replace')
        return json.loads(json.dumps(result,default=lambda value:value.decode('utf-8',errors='replace') if isinstance(value,bytes) else str(value)))

    def save_metadata(self,relative,metadata):
        if not isinstance(metadata,dict):return
        path=self.metadata_path(relative)
        try:write_text_atomic(path,json.dumps(metadata,ensure_ascii=False))
        except OSError:logging.getLogger(__name__).warning('[MOD_LIBRARY] Creator metadata could not be saved; source retained')

    def emit(self,message=None):
        if message is not None:
            self.message=message
            if not message.startswith('Aguardando'):self.watch_deadline=time.monotonic()+600
        self.publish(self.snapshot())

    def snapshot(self):
        with self.lock:return {'type':'sexo2-library-state','mods':copy.deepcopy(self.mods),'incoming':copy.deepcopy(list(self.incoming.values())),
                             'champions':copy.deepcopy(self.catalog),'message':self.message,'watching':self.watching}

    def load_catalog(self):
        if self.catalog:return self.catalog
        raw=self.champion_provider()
        if isinstance(raw,list) and raw:
            self.catalog=[{'id':int(c['id']),'name':str(c.get('name') or c['id']),'alias':str(c.get('alias') or c.get('name') or '')} for c in raw if isinstance(c,dict) and type(c.get('id'))is int and c['id']>0][:700]
            try:write_text_atomic(self.directory/'sexo2-mod-champions.json',json.dumps(self.catalog))
            except OSError:logging.getLogger(__name__).warning('[MOD_LIBRARY] Champion cache could not be saved')
        if not self.catalog:
            try:
                cached=json.loads((self.directory/'sexo2-mod-champions.json').read_text(encoding='utf-8'))
                self.catalog=[c for c in cached if isinstance(c,dict) and type(c.get('id'))is int and c['id']>0 and isinstance(c.get('name'),str)] if isinstance(cached,list) else []
            except (OSError,ValueError):pass
        self.catalog.sort(key=lambda c:c['name'].casefold())
        return self.catalog

    def refresh(self):
        self.load_catalog();rows=[];ids=set()
        for folder in self.storage.skins_dir.iterdir():
            if folder.is_dir() and folder.name.isdigit():ids.add(int(folder.name)//1000)
        for cid in sorted(ids):
            for entry in self.storage.list_mods_for_champion(cid):
                rel=entry.path.relative_to(self.storage.mods_root).as_posix()
                rows.append({'id':hashlib.sha256(rel.encode()).hexdigest()[:24],'path':rel,'name':entry.display_name or entry.mod_name,
                             'storedName':entry.mod_name,'category':'skins','championId':cid,'targets':list(entry.target_skin_ids)})
        for category in self.storage.MOD_CATEGORIES:
            for entry in self.storage.list_mods_for_category(category):
                path=Path(entry['path']);rel=path.relative_to(self.storage.mods_root).as_posix() if path.is_absolute() else path.as_posix()
                rows.append({'id':hashlib.sha256(rel.encode()).hexdigest()[:24],'path':rel,'name':entry.get('displayName') or entry['name'],
                             'storedName':entry['name'],'category':category,'championId':None,'targets':[]})
        with self.lock:self.mods=rows
        return self.snapshot()

    def check_idle(self):
        if self.cancel.is_set():raise ValueError('Importação interrompida após o arquivo atual.')
        if self.busy():raise ValueError('Aguardando sair da seleção ou da partida para preparar os mods.')

    def source(self,row):
        path=self.inbox/row['file']
        if path.is_symlink() or path.is_junction() or not path.resolve().is_relative_to(self.inbox.resolve()) or not path.is_file():raise ValueError('Arquivo de entrada indisponível.')
        if self.file_digest(path)!=row['sha']:raise ValueError('O arquivo mudou; aguarde a cópia terminar.')
        return path

    @staticmethod
    def validate_package(source):
        paths=list_mod_archive(source)
        if not any(re.search(r'(?:^|/)wad/[^/]+\.wad(?:\.client)?(?:/|$)|(?:^|/)raw/.+',p.replace(chr(92),'/'),re.I) or p.lower().endswith(('.wad','.wad.client')) for p in paths):
            raise ValueError('O arquivo não contém dados de um mod compatível. Cole o .fantome ou .modpkg baixado, não imagens nem o atualizador.')

    @staticmethod
    def normalize_layout(root):
        for _ in range(4):
            if (root/'WAD').is_dir() or (root/'RAW').is_dir():break
            children=[p for p in root.iterdir() if p.is_dir()]
            if len(children)!=1:break
            child=children[0]
            if len(list(root.iterdir()))!=1 and not ((child/'WAD').is_dir() or (child/'RAW').is_dir()):break
            files=list(child.iterdir())
            if any((root/file.name).exists() for file in files):raise ValueError('O pacote mistura duas estruturas de mod. Revise o arquivo original.')
            for file in files:file.replace(root/file.name)
            child.rmdir()
        loose=[p for p in root.iterdir() if p.is_file() and p.name.lower().endswith(('.wad','.wad.client'))]
        if loose:
            (root/'WAD').mkdir(exist_ok=True)
            for file in loose:file.replace(root/'WAD'/file.name)
        if not ((root/'WAD').is_dir() or (root/'RAW').is_dir()):raise ValueError('Não foi encontrada a estrutura de arquivos do mod.')

    @staticmethod
    def folder_stamp(path):
        return [[file.relative_to(path).as_posix(),file.stat().st_size,file.stat().st_mtime_ns] for file in sorted(path.rglob('*')) if file.is_file()]

    def duplicate(self,row,targets):
        self.last_import_path=row['path']
        if row['category']=='skins' and targets and not set(targets).issubset(row['targets']):
            self.targets(row['id'],sorted(set(row['targets'])|set(targets)))
        return 'duplicado'

    def import_one(self,source,category,cid=None,targets=None,name=None):
        self.check_idle();self.validate_package(source)
        source_stamp=(source.stat().st_size,source.stat().st_mtime_ns);raw_hash=self.file_digest(source)
        def before_commit():
            self.check_idle()
            if (source.stat().st_size,source.stat().st_mtime_ns)!=source_stamp:raise ValueError('A cópia ainda está mudando; tente novamente quando terminar.')
        previous=self.index.get(raw_hash)
        if isinstance(previous,dict) and previous.get('path'):
            existing=next((row for row in self.mods if row['path']==previous['path'] and row['category']==category and row.get('championId')==cid),None)
            path=self.storage.mods_root/previous['path']
            if existing and path.is_dir() and previous.get('stamp')==self.folder_stamp(path):return self.duplicate(existing,targets)
        if category=='skins':
            if type(cid)is not int or cid not in {c['id'] for c in self.catalog}:raise ValueError('Escolha o campeão deste mod.')
            if not targets or any(type(sid)is not int or sid//1000!=cid for sid in targets):raise ValueError('Escolha uma skin-base válida para o campeão.')
        elif category not in self.storage.MOD_CATEGORIES:raise ValueError('Categoria inválida.')
        source_metadata=self.capture_metadata(source);prepared={}
        def prepare(root):
            self.check_idle();self.normalize_layout(root)
            hashes=self.storage._hash_mod_folder(root,check_continue=self.check_idle);prepared['hashes']=hashes
            for row in self.mods:
                if row['category']!=category or row.get('championId')!=cid:continue
                path=self.storage.mods_root/row['path']
                if not path.is_dir():continue
                stamp=self.folder_stamp(path);cached=self.content_cache.get(row['path'])
                current=cached[1] if cached and cached[0]==stamp and cached[1] else self.storage._hash_mod_folder(path,check_continue=self.check_idle)[0]
                self.content_cache[row['path']]=(stamp,current)
                if current==hashes[0]:raise DuplicatePackage(row)
                if category=='skins' and path.parent==self.storage.get_champion_dir(cid):
                    _,metadata=self.storage._load_target_manifest(cid)
                    previous_meta=next((value for value in metadata.values() if isinstance(value,dict) and value.get('name')==row['storedName']),None)
                    if previous_meta and previous_meta.get('folderHash')!=current:
                        self.check_idle();self.storage.set_champion_target_ids(cid,row['targets'],mod_name=row['storedName'],mod_path=path)
            return hashes
        try:
            if category=='skins':
                folder,_,stored=self.storage.import_mod_file(cid,source,targets,before_commit=before_commit,prepare_extracted=prepare)
                if name:self.storage.set_champion_mod_display_name(cid,name,mod_name=stored)
            else:
                folder,stored=self.storage.import_category_mod_file(category,source,before_commit=before_commit,prepare_extracted=prepare)
                if name:self.storage.set_category_mod_display_name(category,stored,name)
        except DuplicatePackage as duplicate:
            result=self.duplicate(duplicate.row,targets)
            if source_metadata and not self.metadata_path(duplicate.row['path']).exists():self.save_metadata(duplicate.row['path'],source_metadata)
            return result
        relative=folder.relative_to(self.storage.mods_root).as_posix();stamp=self.folder_stamp(folder)
        self.index[raw_hash]={'path':relative,'stamp':stamp,'contentHash':prepared['hashes'][0]}
        self.content_cache[relative]=(stamp,prepared['hashes'][0]);self.last_import_path=relative
        if source_metadata:self.save_metadata(relative,source_metadata)
        self.save_index()
        self.refresh()
        return 'importado'

    def unpack_packages(self,source,category):
        if source.suffix.lower()!='.zip':return False
        with zipfile.ZipFile(source) as z:
            members=z.infolist()
            if any(re.search(r'(?:^|/)(?:wad|raw)/',member.filename.replace(chr(92),'/'),re.I) for member in members):return False
            packages=[member for member in members if not member.is_dir() and Path(member.filename).suffix.lower() in ('.fantome','.modpkg')]
            if not packages:return False
            if len(packages)>1000 or sum(member.file_size for member in packages)>8*1024**3:raise ValueError('O ZIP contém muitos pacotes ou excede o limite.')
            if shutil.disk_usage(self.inbox).free<sum(member.file_size for member in packages)+50*1024*1024:raise ValueError('Não há espaço para preparar os pacotes do ZIP.')
            folder=self.inbox/category;folder.mkdir(exist_ok=True)
            with tempfile.TemporaryDirectory(prefix='.sexo2-packages-',dir=folder) as temp:
                prepared=[]
                for index,member in enumerate(packages):
                    self.check_idle();payload=Path(temp)/(str(index)+Path(member.filename).suffix.lower())
                    with z.open(member) as src,payload.open('wb') as dst:self.copy_file(src,dst)
                    name=Path(member.filename.replace(chr(92),'/')).name
                    # Use a content-based prefix to avoid overwriting another pasted file.
                    name=self.file_digest(payload)[:12]+'-'+name
                    prepared.append((payload,folder/name))
                self.check_idle()
                for payload,target in prepared:
                    if not target.exists():payload.replace(target)
        return True

    def retry(self,key):
        with self.lock:self.incoming.pop(key,None)
        self.cancel.clear();self.scan()

    def scan(self):
        if not self.catalog:self.load_catalog()
        if self.busy():self.emit('Aguardando sair da seleção ou da partida para preparar os mods.');return
        self.cancel.clear()
        sources=[(p,'skins') for p in self.inbox.iterdir() if p.is_file()]
        for category in self.storage.ROOT_CATEGORIES:
            folder=self.inbox/category
            if folder.is_dir() and not folder.is_symlink() and not folder.is_junction():sources.extend((p,category) for p in folder.iterdir() if p.is_file())
        for source,source_category in sorted(sources,key=lambda item:str(item[0]).casefold()):
            if self.cancel.is_set():break
            if not source.is_file() or source.is_symlink() or source.suffix.lower() not in MOD_ARCHIVE_SUFFIXES:continue
            stat=source.stat();stamp=(stat.st_size,stat.st_mtime_ns)
            filename=source.relative_to(self.inbox).as_posix()
            old=self.stamps.get(filename);self.stamps[filename]=stamp
            if old!=stamp:continue
            if any(row['file']==filename and row.get('stamp')==list(stamp) and row.get('status')!='aguardando' for row in self.incoming.values()):continue
            raw_hash=self.file_digest(source);key=hashlib.sha256((filename+raw_hash).encode()).hexdigest()[:24]
            row={'id':key,'file':filename,'sha':raw_hash,'stamp':list(stamp),'category':source_category,'status':'analisando','displayName':display_name(source)}
            with self.lock:
                for old_key,item in list(self.incoming.items()):
                    if item['file']==filename and old_key!=key:self.incoming.pop(old_key)
                self.incoming[key]=row
            self.emit('Analisando '+display_name(source))
            try:
                if source.suffix.lower()=='.zip' and self.is_export(source):
                    self.restore(source);row['status']='restaurado'
                elif self.unpack_packages(source,source_category):row['status']='preparado'
                else:
                    found=identify(source,self.catalog)
                    if source_category!='skins':found.update({'championId':None,'targets':[],'candidates':[]})
                    row.update(found)
                    if source_category=='skins' and not row['championId']:row['status']='revisar'
                    else:row['status']=self.import_one(source,source_category,row.get('championId'),row.get('targets'),row.get('displayName'))
            except Exception as error:
                row['status']='aguardando' if self.busy() and not self.cancel.is_set() else 'erro';row['error']=str(error)
            self.save_index()
            self.emit('Entrada processada. Arquivos originais preservados.')

    def resolve(self,key,cid,targets):
        row=self.incoming.get(key)
        if not row:raise ValueError('Entrada não encontrada. Atualize a lista.')
        self.cancel.clear();result=self.import_one(self.source(row),row['category'],cid,targets,row.get('displayName'))
        row.update({'status':result,'championId':cid,'targets':targets});row.pop('error',None);self.save_index();self.emit('Mod '+result+'.')

    def delete(self,key):
        self.check_idle();row=next((m for m in self.mods if m['id']==key),None)
        if not row:raise ValueError('Mod não encontrado.')
        if row['category']=='skins':ok=self.storage.delete_champion_mod(row['championId'],row['storedName'],row['path'])
        else:ok=self.storage.delete_category_mod(row['category'],row['storedName'])
        if not ok:raise ValueError('Não foi possível remover o mod.')
        self.refresh();self.emit('Mod removido; a cópia original de entrada foi preservada.');return row['path']

    def rename(self,key,name):
        if not isinstance(name,str) or not name.strip():raise ValueError('Digite um nome para o mod.')
        self.check_idle();row=next((m for m in self.mods if m['id']==key),None)
        if not row:raise ValueError('Mod não encontrado.')
        if row['category']=='skins':self.storage.set_champion_mod_display_name(row['championId'],name,mod_name=row['storedName'],relative_path=row['path'])
        else:self.storage.set_category_mod_display_name(row['category'],row['storedName'],name)
        self.refresh();self.emit('Nome atualizado.')

    def targets(self,key,targets):
        self.check_idle();row=next((m for m in self.mods if m['id']==key),None)
        if not row or row['category']!='skins':raise ValueError('Mod de campeão não encontrado.')
        cid=row['championId']
        if not isinstance(targets,list) or not targets or any(type(s)is not int or s//1000!=cid for s in targets):raise ValueError('Escolha ao menos uma skin-base do campeão.')
        self.storage.set_champion_target_ids(cid,targets,mod_name=row['storedName'],mod_path=self.storage.mods_root/row['path'])
        self.refresh();self.emit('Skins-base atualizadas.')

    @staticmethod
    def is_export(source):
        with zipfile.ZipFile(source) as z:return 'sexo2-library.json' in z.namelist()

    def export(self):
        self.cancel.clear();self.check_idle();self.refresh();self.exports.mkdir(exist_ok=True)
        filename='SEXO2-mods-'+time.strftime('%Y-%m-%d_%H-%M-%S')
        output=self.exports/(filename+'.zip');counter=2
        while output.exists():output=self.exports/(filename+f' ({counter}).zip');counter+=1
        rows=[]
        with tempfile.TemporaryDirectory(prefix='.sexo2-export-',dir=self.exports) as temp:
            staged=Path(temp)/'library.zip'
            with zipfile.ZipFile(staged,'x',zipfile.ZIP_STORED) as outer:
                try:
                    for index,row in enumerate(self.mods):
                        self.check_idle();path=self.storage.mods_root/row['path'];self.emit('Exportando '+row['name'])
                        if path.is_symlink() or path.is_junction():raise ValueError('Um mod contém um link; exportação interrompida.')
                        suffix=path.suffix if path.is_file() else '.fantome';name=f'mods/{index:05d}'+suffix
                        if path.is_file():payload=path
                        else:
                            payload=Path(temp)/(str(index)+'.fantome')
                            with zipfile.ZipFile(payload,'w',zipfile.ZIP_DEFLATED,compresslevel=1) as z:
                                for file in sorted(path.rglob('*')):
                                    if file.is_symlink() or file.is_junction():raise ValueError('Um mod contém um link; exportação interrompida.')
                                    if file.is_file() and file.name not in {self.storage.TARGET_METADATA,self.storage.CATEGORY_METADATA,self.storage.LEGACY_TARGET_METADATA}:
                                        with file.open('rb') as src,z.open(file.relative_to(path).as_posix(),'w') as dst:self.copy_file(src,dst)
                        with payload.open('rb') as src,outer.open(name,'w') as dst:self.copy_file(src,dst)
                        rows.append({k:row[k] for k in ('name','category','championId','targets')}|{'file':name,'sha256':self.file_digest(payload)})
                        metadata=self.metadata_path(row['path'])
                        if metadata.is_file() and not metadata.is_symlink():
                            if metadata.stat().st_size>8*1024*1024:raise ValueError('Metadados do mod excedem o limite de exportação.')
                            meta_name=f'meta/{index:05d}.json'
                            with metadata.open('rb') as src,outer.open(meta_name,'w') as dst:self.copy_file(src,dst)
                            rows[-1].update({'metadataFile':meta_name,'metadataSha256':self.file_digest(metadata)})

                    outer.writestr('sexo2-library.json',json.dumps({'schema':1,'app':'SEXO2-mods','mods':rows},ensure_ascii=False))
                except Exception:
                    outer.close();raise
            self.check_idle();staged.replace(output)
        self.emit('Biblioteca exportada. Abra a pasta de exportações.');return output

    def restore(self,source):
        self.check_idle()
        with zipfile.ZipFile(source) as z:
            info=z.getinfo('sexo2-library.json')
            if info.file_size>4*1024*1024:raise ValueError('Manifesto da biblioteca muito grande.')
            data=json.loads(z.read(info));rows=data.get('mods')
            if data.get('schema')!=1 or data.get('app')!='SEXO2-mods' or not isinstance(rows,list) or len(rows)>10000:raise ValueError('Biblioteca incompatível.')
            total=sum(i.file_size for i in z.infolist())
            if len(z.namelist())!=len(set(z.namelist())) or total>32*1024**3:raise ValueError('Biblioteca excede limites ou contém arquivos duplicados.')
            if shutil.disk_usage(self.inbox).free<total+50*1024*1024:raise ValueError('Não há espaço para preparar a restauração da biblioteca.')
            with tempfile.TemporaryDirectory(prefix='.sexo2-restore-',dir=self.inbox) as temp:
                prepared=[]
                for i,row in enumerate(rows):
                    name=row.get('file','');suffix=Path(name).suffix.lower()
                    if not re.fullmatch(r'mods/[0-9]{5}\.(?:zip|fantome|modpkg)',name) or suffix not in MOD_ARCHIVE_SUFFIXES:raise ValueError('Caminho de mod inválido na biblioteca.')
                    payload=Path(temp)/(str(i)+suffix)
                    with z.open(name) as src,payload.open('wb') as dst:self.copy_file(src,dst)
                    if self.file_digest(payload)!=row.get('sha256'):raise ValueError('Biblioteca corrompida. Nenhum mod foi importado.')
                    category=row.get('category');cid=row.get('championId');targets=row.get('targets')
                    if category not in ('skins',*self.storage.MOD_CATEGORIES) or category=='skins' and (type(cid)is not int or not isinstance(targets,list) or not targets or any(type(s)is not int or s//1000!=cid for s in targets)):raise ValueError('Alvos inválidos na biblioteca.')
                    metadata=None
                    if row.get('metadataFile'):
                        meta_name=row['metadataFile']
                        if not re.fullmatch(r'meta/[0-9]{5}\.json',meta_name) or z.getinfo(meta_name).file_size>8*1024*1024:raise ValueError('Metadados do mod inválidos na biblioteca.')
                        raw=z.read(meta_name)
                        if hashlib.sha256(raw).hexdigest()!=row.get('metadataSha256'):raise ValueError('Metadados corrompidos. Nenhum mod foi importado.')
                        metadata=json.loads(raw)
                        if not isinstance(metadata,dict):raise ValueError('Metadados inválidos na biblioteca.')
                    prepared.append((payload,row,metadata))
                for payload,row,metadata in prepared:
                    self.check_idle();self.import_one(payload,row['category'],row.get('championId'),row.get('targets'),str(row.get('name') or '')[:128])
                    if metadata and self.last_import_path:self.save_metadata(self.last_import_path,metadata)
        self.emit('Biblioteca restaurada; mods existentes foram preservados.')
