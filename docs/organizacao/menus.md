# Padronização dos menus

Conferência de cada menu contra as regras aprovadas (D-007 fontes, D-017 protótipo `sexo2-v1`, tokens de
`SEXO2-Style`). Detalhes e catálogo em `docs/organizacao/design.md`. Sem alterar textos, estrutura,
comportamento, ids ou mensagens da ponte. D-128 (ouro Blitz) e o ícone não foram tocados.

## Conforme

| Menu | Arquivo | Observação |
|---|---|---|
| Hub (casca, abas, seções) | `ROSE-Hub/index.js` | tokens, Oswald/Inter, raio 0 |
| Assistente | `SEXO2-Assistant/index.js` | tokens; linhas `#3a3e44`/`#202327` fixas (ver design.md §3.5) |
| Estilo compartilhado | `SEXO2-Style/index.js` | referência |
| Overlay de aprimoramentos, atualizador | `sexo2/overlay/augment_overlay.py`, `updater_main.py` | Segoe UI em componente nativo (D-007); cores já iguais aos tokens |

## Alinhado nesta rodada

| Menu | Arquivo | O que mudou |
|---|---|---|
| Amigos (Skins, Sala, Diagnóstico no Hub) | `ROSE-Amigos/index.js:19-25` | Arial/Georgia por Inter/Oswald; ouro e azul-marinho por `--s2-*`; raio 0 |
| Configurações | `SEXO2-Settings/index.js:21-35` | Spiegel/Beaufort por Inter/Oswald; cores por `--s2-*` |
| Biblioteca de mods | `SEXO2-ModLibrary/index.js:13` | `#25343d`, `#f0e6d2`, `#a09b8c` por tokens |
| Tela de carga | `SEXO2-Startup/index.js:8,17` | fundo e texto pelos valores de `--s2-bg` e `--s2-fg` (sem depender do Style) |

## Precisa de decisão do usuário

Não recoloridos (pedido do auditor: decisão pendente se migram para o estilo neutro):

- `ROSE-SwiftplayPins` (Automático no Hub): ouro `#c89b3c`, Georgia/Arial, gradiente, raio 8.
- `ROSE-PartyMode`, `ROSE-SettingsPanel`: legados, inalcançáveis pelo Hub atual; ouro e Beaufort.
- Rodas sobre a seleção nativa: `ROSE-ChromaWheel`, `ROSE-FormsWheel`, `ROSE-CustomSkinSelector`,
  `ROSE-RandomSkin`, `ROSE-HistoricMode` (visual do cliente: LoL Display/Body).
- Cores de estado sem equivalente aprovado (D-102): ok `#7bd5a7`, erro `#f3a090` (Amigos) e `#d9a796`
  (Configurações).
- `ROSE-CustomWheel` (painel de mods): não alterado; ouro/Spiegel.
- Realce `#f2d27a` do overlay de aprimoramentos e fonte Segoe UI no canvas (pendente alinhar à Inter).
- Remover as sobreposições `!important` do Hub só depois de migrar os painéis restantes.
