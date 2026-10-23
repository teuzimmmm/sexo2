# Ícone do SEXO2 (D-154: o galo; substitui o “2 · Degrau” da D-123)

Fonte única: `assets/sexo2.svg` (galo busto, variação “Mais fluido” de `design/propostas/icone/galo-r3`, sha256
`db86f234ed2a5c0f946def080dfdc3d72c370a7a98c72a4328aeac3fda54a1a6`). Até 24 px o desenho usa o corte `assets/sexo2-small.svg` (sha256 `956f6671dffe105312421591adbeb52745a4cf8b2a3d33670f5f94318402539e`), com fresta e barbela mais
grossas. A abertura animada usa o mesmo arquivo (`SEXO2-Startup/icone-final.svg`, cópia byte a byte). Derivados:
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
| Janela do atualizador, diálogo de bandeja | `update_dialog.py`, `tray_settings.py` -> `icon.png`/`icon.ico` | `galo.png` trocado por `icon.png` |
| Bandeja | `tray_manager.py` -> `tray_starting.png`, `tray_ready.png`, `icon.png` | PNG 256 novo (sem variação de estado) |
| Aviso de boas-vindas do Pengu | `sexo2-toast.png` (64) embutido em core.dll por `restore_build_binaries.py` | PNG novo |
| Logo no aviso do Pengu | `ROSE-UI/index.js` -> `/asset/galo.png` -> `/asset/icon.png` |
| Item de menu do cliente | `ROSE-UI/index.js` | usa `icon.png` como imagem (era máscara de `golden_rose.png`) |
| Pacote | `create_installer.py` gera `icon.ico` a partir de `tray_ready.png` | já coerente |
| Duplicatas | `icon.ico`, `sexo2.ico`, `sexo2-v2.ico`, `sexo2-black-v3.ico` | mesmo ico; mantidas (referenciadas) |

## Removidos (D-112: Galo e BORK sem papel de marca)
`galo.svg/png/ico`, `bork-black-v3/blue/desktop-v2/hud-v2.png`, `golden_rose.png`, `visual-provenance.json`
(sem referência no código, specs, instalador, testes ou `compatibility_bases.json`; `audit_frozen.py` ajustado).

## Pendente
- Bandeja: `tray_starting.png` e `tray_ready.png` são idênticos; o código só escolhe o arquivo. Diferença visual é decisão nova.
- Texto de créditos (`SEXO2-Settings`, linha 204) ainda cita BORK e o escudo: texto visível, exige aprovação.

## Não aplicado
| Item | Motivo |
|---|---|
| `SEXO2-Startup/index.js` | coberto pela abertura (outro agente) |
| `ROSE-Jade/assets/logo.png` | logo do plugin Jade, não do app |
| Ícones de campeões, itens, runas, skins, cromas, botões de skin | conteúdo do jogo mantém as cores |
| `Rose.spec` | legado (aponta `icon.ico`, agora novo) |
| `scripts/apply_icon.py`, `design/propostas/icone/` | propostas históricas (D-121); não rodar `apply_icon.py` |
| `vendor/PenguLoader-1.1.6` | código de terceiros |
| `docs/` antigos (`arquivo/`, PREPROJETO) citando o galo | histórico das decisões |

## Verificações de compatibilidade
- `compatibility_bases.json`: sem hash de ícone. `restore_build_binaries.py` só lê `sexo2-toast.png`.
- Rendering no Windows real (barra de tarefas, bandeja, item de menu do cliente) não validado.
