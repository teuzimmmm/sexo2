"""Check compiled implementation matches source without launching Rose or LoL."""
import types,sys
from pathlib import Path
from PyInstaller.archive.readers import CArchiveReader

root=Path(__file__).resolve().parent
bundle=root/(sys.argv[1]if len(sys.argv)>1 else 'dist-r6-release/Rose')
archive=CArchiveReader(str(bundle/('SEXO2.exe'if(bundle/'SEXO2.exe').exists()else 'Rose.exe')))
pyz=archive.open_embedded_archive('PYZ.pyz')
def signature(code):
    if isinstance(code,types.CodeType):
        return(code.co_code,tuple(signature(x)for x in code.co_consts),code.co_names,code.co_varnames,code.co_freevars,code.co_cellvars)
    return code
for name in ['main','main.setup.initialization','sexo2.update.lifecycle','main.runtime.loop','injection.mods.zip_resolver','sexo2.version','state.core.app_status','utils.integration.tray_manager','friends.room','friends.arena_bravery','threads.core.phase_thread','threads.websocket.websocket_event_handler','injection.overlay.overlay_manager','friends.auto_accept','friends.preferences','friends.service','friends.selection_guard','lcu.core.client','party.hosting.controller','utils.download.verified_file','utils.core.atomic_file','config','injection.game.game_monitor','party.core.party_manager','pengu.communication.message_handler','sexo2.services.work_queue','sexo2.services.settings','sexo2.update.engine','sexo2.update.client','sexo2.update.trust','utils.download.hash_updater','injection.mods.storage','launcher.core.launcher','launcher.core.startup_policy','launcher.sequences.hash_check_sequence','launcher.sequences.skin_sync_sequence','utils.core.modpkg','party.discovery.custom_mods','sexo2.services.mod_library','pengu.core.skin_monitor','utils.core.safe_extract',
             'sexo2.services.draft','sexo2.services.builds','sexo2.services.loadouts',
             'sexo2.overlay.model','sexo2.overlay.runtime','sexo2.overlay.win32',
             'sexo2.overlay.arena','sexo2.overlay.processes',
             'sexo2.overlay.offers','sexo2.overlay.reader','sexo2.overlay.screen','sexo2.overlay.wire',
             'sexo2.install.identity','lolalytics.client','lolalytics.builds','lolalytics.matchups','lolalytics.risk']:
    source=root/'main/__init__.py' if name=='main' else root/(name.replace('.','/')+'.py')
    expected=compile(source.read_text(encoding='utf-8-sig'),str(source),'exec')
    actual=pyz.extract(name)
    assert signature(expected)==signature(actual),name
for file in (root/'Pengu Loader/plugins').rglob('*'):
    if file.is_file():
        packaged=bundle/'_internal/Pengu Loader/plugins'/file.relative_to(root/'Pengu Loader/plugins')
        assert packaged.read_bytes()==file.read_bytes(),str(file)
assert (bundle/'_internal/hosting-tools/cloudflared.exe').is_file()
print('PASS: compiled modules and every plugin match source; integrated tunnel binary exists.')

for name in ['galo.png','galo.ico','bork-black-v3.png','sexo2.ico','golden_rose.png','update-source.json']:
    assert (bundle/'_internal/assets'/name).read_bytes()==(root/'assets'/name).read_bytes(),name
print('PASS: release visual assets and update source match.')

if (bundle/'sexo2-test-build.json').exists():
    helper=Path('sexo2/overlay/bin/sexo2-offer-reader.exe')
    assert (bundle/'_internal'/helper).read_bytes()==(root/helper).read_bytes(),'OCR helper differs from compiled source output'
    notices=root/'sexo2/overlay/licenses'
    assert notices.is_dir() and any(notices.iterdir()),'OCR dependency notices missing'
    for notice in notices.iterdir():
        assert (bundle/'_internal/sexo2/overlay/licenses'/notice.name).read_bytes()==notice.read_bytes(),notice.name
    for source,target in [('LICENSE','LICENSE-Rose.txt'),
                          ('vendor/PenguLoader-1.1.6/LICENSE','LICENSE-PenguLoader.txt'),
                          ('hosting-tools/LICENSE-cloudflared.txt','_internal/hosting-tools/LICENSE-cloudflared.txt'),
                          ('hosting-tools/provenance.json','_internal/hosting-tools/provenance.json')]:
        assert (bundle/target).read_bytes()==(root/source).read_bytes(),target
    print('PASS: test package includes Rose, Pengu and cloudflared notices/provenance.')
