# Organização do código Python

Inventário e padrão-alvo. Só descreve; nenhuma mudança de comportamento. Dados medidos com ruff e varredura do repositório.

## Pacotes e responsabilidades

| Pacote | Responsabilidade |
|---|---|
| `main/` (`core`, `runtime`, `setup`) | Entrada, argumentos, console, inicialização, loop principal, limpeza, sinais |
| `config.py` | Constantes e acesso à configuração (`get_config_*`, `get_config_file_path`) |
| `lcu/` (`core`, `data`, `features`) | Conexão e API do cliente (lockfile, REST), cache e scraping de skins, perks, itens, modos |
| `threads/` (`core`, `handlers`, `utilities`, `websocket`) | Threads de fase, injeção, lobby, WebSocket do LCU |
| `injection/` | Injetor, patcher, mods, overlay, detecção/recuperação de partida |
| `pengu/` | Ponte com os plugins (HTTP/WebSocket, `message_handler`, mapeamento de skins) |
| `ui/` | Seletor de cromas e exibição de skin (Python) |
| `party/` | Grupo: rede (STUN/UDP/relay), protocolo, hospedagem, descoberta |
| `friends/` | Amigos: sala, auto-aceite, loteria, preferências |
| `launcher/` | Atualizador e sequências de partida (hash, sync de skins) |
| `lolalytics/` | Cliente e parsing de dados de builds |
| `sexo2/` | Serviços novos (mod_library, update, augments, overlay) |
| `state/` | Estado compartilhado da aplicação |
| `utils/` | `core` (paths, logging, segurança, normalização), `download`, `system` (Win32), `integration` (tray, Pengu Loader), `threading` |

## Inconsistências observadas e padrão-alvo

- **Logs:** dezenas de prefixos entre colchetes (`[CHROMA]` 148 usos, `[INJECT]` 96, `[HISTORIC]` 68, `[PARTY]`, `[LCU]`...), mais os helpers `log_action/log_success/log_status` de `utils/core/logging.py`. Padrão: prefixo MAIÚSCULO por domínio, igual ao nome do pacote; helpers só para marcos de fluxo. Os textos aparecem em logs e podem ser lidos por testes: não renomear sem aprovação.
- **Caminhos:** `utils/core/paths.py` é a fonte (`get_user_data_dir`, `get_state_dir`, `get_skins_dir`...). `config.get_config_file_path` e `updater_main.py` (usa `LOCALAPPDATA` direto; o atualizador roda isolado) são exceções. Padrão: código novo usa `utils.core.paths`.
- **Configuração:** acesso por `config.get_config_*`. Padrão: nunca ler o arquivo de config direto.
- **Tratamento de erros:** mistura de `except Exception` com log e `except Exception: pass`; `except X as e` sem uso de `e` (F841) em `main/setup/console.py` e `injection/overlay/process_manager.py`. Padrão: capturar o tipo específico e registrar com o logger do módulo; silenciar só com comentário.
- **Docstrings de módulo:** 4 de 270 módulos sem docstring (fora `__init__.py`); `from __future__ import annotations` em 55 de 270. Padrão: docstring de uma linha em todo módulo; `__future__` só onde há referência adiante em anotações.
- **Imports:** 246 violações de ordem (I001) e a regra não está ativa (`pyproject.toml` seleciona só `E9,F63,F7,F82`). Ativar `I` e `F` é um commit à parte, com `ruff --fix` e execução completa verde.
- **Nomes legados:** chaves `rose_*`, `__roseBridge` e pastas `ROSE-*` são identificadores internos compatíveis; renomear exige migração (não feito).

## Variáveis atribuídas e não usadas (F841), não alteradas

`injection/game/game_monitor.py` (`status_before`), `injection/mods/storage.py` (`prepared_hashes`), `threads/handlers/injection_trigger.py` (`lcu_skin_id`, `has_any_mods`), `threads/utilities/loadout_ticker.py` (`final_label`), `threads/utilities/timer_manager.py` (`probe_used`), `ui/core/user_interface.py` (`prev_base_skin_id`), `ui/handlers/skin_display_handler.py` (`is_same_base_chroma`), `utils/download/hash_updater.py` (`total_size`), `utils/download/smart_skin_downloader.py` (`results`), `utils/system/admin_utils.py` (`exe_dir`), `utils/system/resolution_utils.py` (`lang_config`). A remoção pode esconder chamada com efeito colateral; revisar caso a caso.
