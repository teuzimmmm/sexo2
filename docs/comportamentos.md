# Comportamentos protegidos

Funções que nenhuma refatoração pode quebrar. Antes de mexer numa área, confira
a cobertura: "sem teste" significa que a regressão só aparece no cliente real.
Todos os testes rodam com `python scripts/run_tests.py` e `node --test tests/test_*.cjs`.

| Função | Onde está | Cobertura automatizada |
|---|---|---|
| Injeção de skin no início da partida | `threads/handlers/injection_trigger.py`, `injection/core/` | `injection/tests` (overlay, patcher, EOL, parada), `test_classic_injection`; **sem teste** da injeção real |
| Disparo pelo cronômetro da seleção | `threads/utilities/loadout_ticker.py` | `test_loadout_ticker` (falhas e liberação); **sem teste** de precisão do disparo |
| Jogo suspenso sempre retomado | `injection/game/game_monitor.py` | `test_game_monitor`, `test_game_ended` |
| Parada de emergência | `injection/game/match_recovery.py`, bandeja | `test_match_recovery` |
| Favoritas, sorteio e seleção automática | `friends/service.py`, `friends/lottery.py`, `friends/skin_selector.py` | `test_r6_protections`, `test_friends_features`, `test_skin_selector` |
| Perfis | `friends/preferences.py` | `test_friends_features` (aplicação de perfil) |
| Escolha manual prevalece | `friends/selection_guard.py` | `test_r6_protections` |
| Preferências v2, migração v1 e backup | `friends/preferences.py` | `test_friends_features` (arquivo corrompido preservado, gravação falha) |
| Autoaceite opcional | `friends/auto_accept.py` | `test_r6_protections` |
| Sala privada (relay, túnel, reconexão) | `party/`, `friends/room.py` | `party/tests`, `test_private_relay`, `test_tunnel_dns`, `test_fixed_party`, `test_party_ui.cjs`, `test_friends_ui.cjs` |
| Biblioteca de mods, importação e exportação | `sexo2/services/mod_library.py` | `test_mod_library`, `test_mod_library_bridge`, `test_modpkg`, `test_safe_extract_limits` |
| Seleção de mods na seleção de campeões | `pengu/communication/message_handler.py`, `SEXO2-CustomWheel` | `test_custom_mod_monitor`, `test_mod_manifest`; **sem teste** por mensagem `mod-*` |
| Swiftplay e fixados | `threads/handlers/swiftplay_handler.py`, `pengu/processing/swiftplay_pins.py` | `test_quickplay`, `test_swiftplay_historic`, `test_swiftplay_pins`, `test_swiftplay_draw` (sorteio só para quem não escolheu, nunca gravado), `test_swiftplay_pins_ui.cjs` |
| Arena Bravura | `friends/arena_bravery.py` | `test_arena_bravery` |
| Ponte Pengu ↔ backend e reconexão | `pengu/core/`, `pengu/communication/` | `pengu/tests` (porta, watchdog, isolamento de mensagens) |
| Conexão e eventos do LCU | `lcu/`, `threads/websocket/` | `lcu/tests`, `test_ws_event_errors`, `test_ws_retry_logging`, `test_champ_lock_errors`, `test_late_lock_replay` |
| Atualização assinada e restauração em falha | `sexo2/update/` | `test_patch_update`, `test_update_client`, `test_update_lifecycle`, `test_updater_transition`, `test_compatibility_packages` |
| Inicialização rápida e verificação de hashes | `launcher/core/startup_policy.py`, `launcher/sequences/` | `test_startup_policy`, `test_startup_hash_checks` |
| Configurações e início com o Windows | `sexo2/services/settings.py`, `utils/integration/tray_settings.py` | `test_settings_service`, `test_config_consistency` |
| Bandeja | `utils/integration/tray_manager.py` | `test_tray_lifecycle` |
| Instância única (mutex novo e o antigo, tomados juntos) | `main/core/lockfile.py` | `tests/test_legacy_names.py` (núcleo com kernel simulado); **sem teste** no Windows real |
| Migração de nomes antigos: arquivos, tarefa agendada, plugins `ROSE-*`, sessão do Pengu, códigos e links | `utils/core/legacy_names.py`, `utils/system/admin_utils.py`, `utils/integration/pengu_loader.py`, `party/` | `test_legacy_names`, `test_plugin_rename`; **sem teste** em upgrade real |
| Dados do usuário em `%LOCALAPPDATA%\Rose` | `utils/core/paths.py` | **sem teste** de caminho; só de conteúdo |
| Diagnóstico sem segredos | `friends/diagnostics.py` | `test_friends_features` (sanitização) |
| Biblioteca LoLalytics | `lolalytics/` | `tests/test_lolalytics_*` (fixtures reais) |
| Importação de runas: só a página gerenciada, confirmação por leitura, sessão e campeão invalidam o pendente | `sexo2/services/rune_import.py`, `sexo2/services/rune_rules.py`, `lcu/features/lcu_perks.py` | `test_rune_import`, `test_rune_rules`, `lcu/tests/test_lcu_perks` (cliente simulado; **sem teste** no cliente real) |
| Conjuntos de itens: troca só os gerenciados do campeão, os demais ficam idênticos | `sexo2/services/item_sets.py`, `lcu/features/lcu_item_sets.py` | `test_item_sets` (cliente simulado; **sem teste** no cliente real) |
| Estatísticas do assistente (slug do campeão, runas por runa-chave) | `sexo2/services/stats.py` | `test_stats_service` (fixtures LoLalytics) |

Lacunas que os marcos devem cobrir antes de mexer na área: precisão do disparo
da injeção (M6b), mensagens `mod-*` (M7), caminhos de dados (pasta `Rose` mantida; ver `docs/PROGRESSO-M5B.md`).
