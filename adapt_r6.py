from pathlib import Path
root=Path(__file__).resolve().parent
def edit(name,old,new):
 p=root/name;text=p.read_text(encoding='utf-8-sig')
 if old not in text:raise RuntimeError('Missing target '+name+': '+old[:60])
 p.write_text(text.replace(old,new),encoding='utf-8')
edit('friends/service.py',"return {'type':'friends-state','version':APP_VERSION,", "return {'type':'friends-state','room':self.room.poll(),'automatic':data.get('automatic','off'),'favorites':data.get('favorites',{}),'manualChoice':is_manual(self.state),'version':APP_VERSION,")
edit('friends/service.py',"                self.preferences.activate(name)\n                release(self.state);self.preferences.automatic('off');self.preferences.activate(name)","                release(self.state);self.preferences.automatic('off');self.preferences.activate(name)")
edit('friends/service.py',"snapshot=self.snapshot()\n                from party.core", "snapshot=self.snapshot();snapshot.pop('room',None)\n                from party.core")
edit('friends/service.py',"'Abra Rose Sala e escolha um servidor disponível.'", "'Abra Sala neste painel para hospedar, entrar ou reconectar.'")
edit('friends/service.py',"'Preferências do Rose Amigos'", "'Preferências'")
edit('friends/service.py',"'Amigo'", "'Participante'")
edit('utils/download/skin_downloader.py',"            with open(local_path, 'wb') as f:\n                for chunk in response.iter_content(chunk_size=8192):\n                    if chunk:\n                        f.write(chunk)","            from .verified_file import write_download\n            try: write_download(response, local_path, 8192)\n            finally: response.close()")
edit('utils/download/smart_skin_downloader.py',"                with open(local_path, 'wb') as f:\n                    for chunk in response.iter_content(chunk_size=LOG_CHUNK_SIZE):\n                        if chunk:\n                            f.write(chunk)","                from .verified_file import write_download\n                try: write_download(response, local_path, LOG_CHUNK_SIZE)\n                finally: response.close()")
# Dedicated manual event is ordered on the same serialized worker as automation.
edit('pengu/communication/message_handler.py','    "friends-request",','    "friends-request",\n    "manual-skin-choice",')
edit('pengu/communication/message_handler.py','        if payload_type == "friends-request":','        if payload_type == "manual-skin-choice":\n            from friends.selection_guard import mark_manual\n            mark_manual(self.shared_state)\n            return\n        if payload_type == "friends-request":')
edit('pengu/communication/message_handler.py','        """Handle chroma selection from JavaScript"""','        """Handle chroma selection from JavaScript"""\n        from friends.selection_guard import mark_manual\n        mark_manual(self.shared_state)')
edit('pengu/communication/message_handler.py','        """Handle mod selection for injection over hovered skin"""','        """Handle mod selection for injection over hovered skin"""\n        from friends.selection_guard import mark_manual\n        mark_manual(self.shared_state)')
# Native color and dimensions are inherited from the client's own icon classes.
edit('Pengu Loader/plugins/ROSE-UI/index.js','    icon.style.webkitMaskImage =', '    icon.style.webkitMaskSize = "contain";\n    icon.style.webkitMaskRepeat = "no-repeat";\n    icon.style.webkitMaskPosition = "center";\n    icon.style.webkitMaskImage =')
# Stop tunnel before any normal quit/restart; atexit is additional protection.
edit('main/__init__.py','            state.stop = True','            service = getattr(state, "friends_service", None)\n            if service: service.room.host.stop()\n            state.stop = True')
# Prevent old Party UI from silently re-enabling a deliberately disconnected room.
edit('Pengu Loader/plugins/ROSE-PartyMode/index.js','      if (!bridgeReady || partyState.enabled || autoEnableInFlight || enableFailures > 6) return;', '      if (!bridgeReady || partyState.enabled || autoEnableInFlight || enableFailures > 6 || window.__roseRoomLeft) return;')
edit('config.py','Rose Amigos r5','Rose r6') if 'Rose Amigos r5' in (root/'config.py').read_text() else None
# In-process hosting needs its bundled transport and cloudflared binary.
edit('Rose.spec','datas = []',"datas = [('hosting-tools/cloudflared.exe','hosting-tools')]")
edit('Rose.spec','hiddenimports=hiddenimports,',"hiddenimports=hiddenimports + ['friends.room','friends.selection_guard','party.hosting.controller','party.hosting.friends_relay'],")
print('r6 adaptations complete')
