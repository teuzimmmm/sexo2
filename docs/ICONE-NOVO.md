# Novo ícone do SEXO2 (D-122, pendente de confirmação)

Fonte única: `assets/sexo2.svg` (cópia byte a byte de `icone-final.svg`, sha256
`ee8a0d414846af736215fbbf3690f5101348d1770b27bd907a05d1fe6f9ebb31`). Derivados:
`python scripts/render_icon.py` (Chromium headless; ICO com entradas PNG de 16, 24, 32, 48, 64,
128 e 256). Testes: `tests/test_icon.py`. Nomes de arquivo antigos mantidos (o código já os usa).

## Aplicado
| Local | Arquivo | Ação |
|---|---|---|
| Executável SEXO2.exe | `SEXO2.spec` -> `assets/sexo2.ico` | ico novo |
| Atualizador SEXO2 Update.exe | `SEXO2-Updater.spec` -> `assets/sexo2.ico` | ico novo |
| Instalador/desinstalador | `installer-sexo2.iss` SetupIconFile `sexo2.ico`; UninstallDisplayIcon = exe | ico novo |
| Atalhos (menu, área de trabalho) | `.iss` IconFilename `sexo2-v2.ico` | ico novo |
| Atalho criado pelo atualizador | `updater_main.py` -> `sexo2-black-v3.ico` | ico novo |
| Janela de erro (TaskDialog) | `main/__init__.py` -> `icon.ico` | ico novo |
| Janela do atualizador, diálogo de bandeja | `update_dialog.py`, `tray_settings.py` -> `galo.png`/`tray_ready.png`/`icon.ico` | arquivos trocados |
| Bandeja | `tray_manager.py` -> `tray_starting.png`, `tray_ready.png`, `icon.png` | PNG 256 novo (sem variação de estado) |
| Aviso de boas-vindas do Pengu | `sexo2-toast.png` (64) embutido em core.dll por `restore_build_binaries.py` | PNG novo |
| Logo no aviso do Pengu | `ROSE-UI/index.js` -> `/asset/galo.png` | arquivo trocado |
| Item de menu do cliente | `ROSE-UI/index.js` | usa `icon.png` como imagem (era máscara de `golden_rose.png`) |
| Pacote | `create_installer.py` gera `icon.ico` a partir de `tray_ready.png` | já coerente |
| Duplicatas | `icon.ico`, `sexo2.ico`, `sexo2-v2.ico`, `sexo2-black-v3.ico`, `galo.ico` | mesmo ico; mantidas (referenciadas) |

## Não aplicado
| Item | Motivo |
|---|---|
| `SEXO2-Startup/index.js` | coberto pela abertura (outro agente) |
| `golden_rose.png` | sem uso no plugin agora; mantido por `audit_frozen.py` |
| `galo.svg`, `bork-*.png`, `visual-provenance.json` | papel do Galo/BORK pendente (D-112) |
| `ROSE-Jade/assets/logo.png` | logo do plugin Jade, não do app |
| Ícones de campeões, itens, runas, skins, cromas, botões de skin | conteúdo do jogo mantém as cores |
| `Rose.spec` | legado (aponta `icon.ico`, agora novo) |
| `scripts/apply_icon.py`, `design/propostas/icone/` | propostas históricas (D-121); não rodar `apply_icon.py` |
| `vendor/PenguLoader-1.1.6` | código de terceiros |
| `docs/` e README antigos citando o galo | histórico das decisões |

## Verificações de compatibilidade
- `compatibility_bases.json`: sem hash de ícone. `restore_build_binaries.py` só lê `sexo2-toast.png`.
- Rendering no Windows real (barra de tarefas, bandeja, item de menu do cliente) não validado.
