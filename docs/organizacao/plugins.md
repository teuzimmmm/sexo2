# Inventário dos plugins Pengu

Fotografia do código em `Pengu Loader/plugins/*/index.js`. Só descreve; nada aqui muda comportamento.
Contagens por `grep` (aproximadas). `SEXO2-Jade` está desativado (`index.js_`) e fora do inventário.

## Plugins

| Plugin | Função | Linhas | Estilo | Ponte | Timers / observadores |
|---|---|---:|---|---|---|
| SEXO2-Amigos | Skins: preparo, perfis, sorteio, sala, diagnóstico | 707 | formatado (era 1 linha) | `__roseBridge` | 1 interval, 1 timeout |
| SEXO2-ChromaWheel | Roda de chromas | 4076 | formatado, linhas longas | `waitForBridge` | 1 interval, 11 timeouts, 1 MO, 2 rAF |
| SEXO2-CustomSkinSelector | Seletor de skin custom | 946 | formatado | `waitForBridge` | 1 interval, 2 timeouts, 1 MO |
| SEXO2-CustomWheel | Roda de mods por skin | 3060 | formatado | `waitForBridge` | 1 interval, 7 timeouts, 1 MO |
| SEXO2-FormsWheel | Roda de formas (assets) | 5527 | formatado | `waitForBridge` | 1 interval, 9 timeouts, 1 MO, 2 rAF |
| SEXO2-HistoricMode | Modo histórico | 1230 | formatado | `waitForBridge` | 6 timeouts, 1 MO |
| SEXO2-Hub | Entrada única de navegação | 250 | formatado (era 1 linha) | `__roseBridge` | 1 interval, 1 timeout |
| SEXO2-I18n | Idioma dos menus | 135 | formatado | `__roseBridge` | 1 timeout |
| SEXO2-PartyMode | Sala fixa automática (SEXO PARTY) | 1454 | formatado | WebSocket próprio (relay), sem `__roseBridge` | 2 intervals, 2 timeouts, 2 rAF |
| SEXO2-RandomSkin | Skin aleatória | 711 | formatado | `waitForBridge` | 4 timeouts, 1 MO |
| SEXO2-SettingsPanel | Painel de configurações | 5233 | formatado | `waitForBridge` | 3 intervals, 25 timeouts, 6 MO, 4 rAF |
| SEXO2-SkinMonitor | Dono do WebSocket da ponte; publica `__roseBridge` | 712 | formatado | cria a ponte | 1 interval, 2 timeouts, 1 MO |
| SEXO2-SwiftplayPins | Skins fixadas por campeão (Swiftplay) | 263 | formatado | via `__roseBridge` | 1 interval, 1 timeout |
| SEXO2-UI | Desbloqueio de interface | 995 | formatado | `waitForBridge` | 2 intervals, 4 timeouts, 6 MO, 2 rAF |
| SEXO2-Assistant | Assistente da seleção (Runas, Itens, Mods) | 734 | formatado | `__roseBridge` | 1 interval, 2 timeouts |
| SEXO2-ModLibrary | Biblioteca de mods no painel | 356 | formatado (era 1 linha) | `__roseBridge` | 1 interval |
| SEXO2-Settings | Configurações próprias no HUD | 326 | formatado (era 1 linha) | `__roseBridge` | 2 intervals |
| SEXO2-Startup | Abertura animada sobre a tela de carregamento (D-124) | ~330 | assets locais: ícone SVG e dois woff2 | nenhuma (independente) | 1 rAF durante 2,55 s; observadores só até achar/ver sair o loading |
| SEXO2-Style | Tokens, fontes e componentes compartilhados | 123 | formatado | `__roseBridge` (1 uso) | 1 interval, 2 timeouts |

Globais `window.__sexo2*` existentes: `__sexo2Style`, `__sexo2Assistant`, `__sexo2Mods`, `__sexo2AnchorDiagnostics`, `__sexo2ModLibrary`, `__sexo2Settings`. Não renomear.

## Duplicações

- **Espera da ponte**: `waitForBridge()` copiada em 8 plugins (ChromaWheel, CustomSkinSelector, CustomWheel, FormsWheel, HistoricMode, RandomSkin, SettingsPanel, ROSE-UI). Mesmo corpo: polling a cada 50 ms, limite 10 s, rejeita com "Bridge not available". Os plugins SEXO2-* e Amigos/Hub/Swiftplay/I18n usam leituras próprias de `window.__roseBridge`.
- **Injeção de CSS**: `injectCSS()` em 5 plugins (ChromaWheel, CustomSkinSelector, CustomWheel, FormsWheel, SettingsPanel), `injectStyles()` no PartyMode; Hub, Startup e Style montam `<style>` por conta própria.
- **Helpers de elemento / `escapeHtml`**: repetidos por plugin (ex.: `escapeHtml` no RandomSkin e em outros). Não há módulo compartilhado: o Pengu carrega cada `index.js` isolado.

## Cores e fontes

Tokens aprovados vivem em `SEXO2-Style` (`--s2-*`, `--t-*`, `--sp-*`; espelhados em `design/`).

| Usam tokens (`var(--`) | Hex fixo, sem tokens |
|---|---|
| Style (47), Assistant (58), Hub (42), PartyMode (15 de 84 hex), CustomWheel (5 de 27) | SettingsPanel (184 hex, 39 `font-family`), PartyMode (84 hex, 17 `font-family`), ChromaWheel (42), FormsWheel (41), SwiftplayPins (26), CustomSkinSelector (25), Amigos (23), HistoricMode (23), Settings (10) |

Migrar cores/fontes exige aprovação (aparência) e não foi feito.

## Padrão alvo (proposta)

1. Cabeçalho `/** @name <pasta> @description <resumo> */` em todo `index.js` (já presente em todos).
2. Código formatado (prettier: `--print-width 120 --single-quote --quote-props preserve`), sempre em commit separado, provado com `node scripts/js_ast_equal.cjs BASE HEAD arquivo`.
3. Um único IIFE com `'use strict'` e guarda contra dupla carga (`window.__sexo2<Nome>`) nos plugins novos.
4. Ponte: ler `window.__roseBridge`; sem criar novo canal. Mensagens da ponte não mudam sem migração.
5. Sem timers/observadores novos; preferir os eventos existentes. Reduzir os atuais só com medição (`docs/MEDICAO.md`).
6. Estilo visual: somente tokens do `SEXO2-Style`; hex/fontes novos precisam de aprovação.
7. Compartilhamento de helpers (`waitForBridge`, `injectCSS`, `escapeHtml`) só via `SEXO2-Style` ou um plugin utilitário, com teste; hoje é duplicação deliberada para isolar falhas.

## Pendências (não feitas)

- Renomear pastas `ROSE-*`: migração arriscada (nomes referenciados por Python, testes, instalador e Pengu); só reportado.
- Reformatar plugins grandes de origem Rose (linhas até ~380 caracteres): aumentaria o diff contra o upstream e conflitaria com ajustes paralelos de CSS.
- Código morto: sem varredura confiável de referências entre plugins/Python; nada removido.
- Unificar `waitForBridge`: refator de comportamento (polling de 50 ms), precisa de teste e medição.
