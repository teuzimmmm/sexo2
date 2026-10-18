# Auditoria de design e proposta de padronização

Proposta. Nada aqui é decisão: os itens novos entram como **PENDENTE** até o usuário aprovar
(`docs/produto/decisoes.md`). Nenhum plugin, overlay ou tela foi alterado. O catálogo visual está em
`design/propostas/padrao/index.html` ("hoje" ao lado de "proposto").

Referência do que já vale: D-007 (Oswald + Inter), D-014/D-101 (escala B compactada), D-017 (visual do
protótipo `design/propostas/sexo2-v1` aprovado). Pendentes que esta proposta toca: D-102 (cores), D-103
(componentes), D-112 (Galo/BORK). As decisões D-119 (overlay de ouro, visual Blitz), D-120 e D-121 (ícone)
foram citadas na tarefa, mas **não constam** deste `decisoes.md`; esta proposta não as assume.

## 1. Fonte de verdade hoje

`design/tokens.json` só contém fontes e `tabular-nums`. Cores, escala, espaçamento e raio estão
**copiados à mão** em quatro lugares, sem gerador:

| Cópia | Onde |
|---|---|
| Protótipo | `design/propostas/sexo2-v1/css/styles.css:8-33` |
| Plugin compartilhado | `Pengu Loader/plugins/SEXO2-Style/index.js:19-27` |
| Overlay de ouro | `sexo2/overlay/gold_overlay.py:27-30` |
| Overlay de aprimoramentos | `sexo2/overlay/augment_overlay.py:30-33` |

Só três plugins usam `var(--s2-*)`: `ROSE-Hub` (25 usos), `SEXO2-Assistant` (18) e `SEXO2-Style` (23). Os
outros 16 têm cores e fontes fixas no código. (Contagens por busca de texto em cada `index.js`; linha =
primeira ocorrência.)

## 2. Inventário por superfície

### 2.1 Superfícies já no padrão aprovado

| Superfície | Arquivo | Cores | Fontes | Tamanhos | Raio / borda |
|---|---|---|---|---|---|
| Assistente | `SEXO2-Assistant/index.js:162-217` | tokens; fixas: `#3a3e44` (174), `#202327` (183, 211), `#22252a` e `#1b1d21` (217) | Oswald/Inter via tokens | 12; 10 (contador, 215); 22 (nome, 166) | 2px (165), 50% (196-203); borda 1px `--s2-line`; sombra `0 8px 30px` (162) |
| Hub | `ROSE-Hub/index.js:9-50` | tokens | Oswald 20/18/13, Inter 13-14 | 13 base, 14 menu, 11 detalhes | `border-radius:0` (21, 44); borda 1px `--s2-line`; sombra igual à do assistente (9) |
| Base e tooltip | `SEXO2-Style/index.js:19-57` | tokens; fixas `#111` (41), `#fff`, `#0b0c0d`/`#2a2d32`/`#ddd` (57) | tokens | 13, 12 | 2px, 50% |

Observações:
- O Hub tem 69 `!important` (`ROSE-Hub/index.js:7-50`): repinta painéis legados em vez de os painéis usarem o
  padrão (linhas 44-45 forçam botão, campo e fonte; 34-41 desmontam o layout de Amigos, Pins, Party e Settings).
- Paddings fora da grade 4/8/12/16: `5px 10px` (Hub:21), `8px 16px` (Hub:14), `12px 16px` (Hub:23),
  `14px 0 8px` (Hub:27). A aba `7px 12px 6px` (Hub:25) é igual à do protótipo (`styles.css:112`).
- Título de seção do Hub usa 13px; o token `--t-category` é 12px (Hub:27 contra `styles.css:24`).

### 2.2 Superfícies próprias do SEXO2 com visual antigo

| Superfície | Arquivo | Cores | Fontes | Tamanhos | Raio / borda |
|---|---|---|---|---|---|
| Configurações | `SEXO2-Settings/index.js:21-35` | `#a09b8c` (21, 25, 32), `#cdbe91` (22), `#c8aa6e` (28, 35), `#1e282d` (24, 34), `#78796d` (30), `#d9a796` (33) | `'Spiegel',Arial` (21); `'Beaufort for LOL',Georgia` (22) | 13, 18, 11, 12 | sem raio; linha 1px `#1e282d` |
| Biblioteca de mods | `SEXO2-ModLibrary/index.js:13` | `#25343d` (azul-petróleo, bordas), `#f0e6d2`, `#a09b8c` | herda do contêiner | herda | linha 1px `#25343d` |
| Tela de carga | `SEXO2-Startup/index.js:8,17-18` | `#010a13`, `#e2e1e1` | `Inter,sans-serif` (18), sem garantir o arquivo | `1rem` | `0` |

Dentro do Hub, Configurações e Biblioteca recebem as sobreposições `!important` do Hub (linhas 44-50): o
resultado é uma mistura (fundo e botão novos, títulos Beaufort e linhas `#1e282d`).

### 2.3 Painéis herdados do Rose (visual do cliente LoL)

| Superfície | Arquivo | Cores principais | Fontes | Tamanhos | Raio / borda |
|---|---|---|---|---|---|
| Amigos / Sala | `ROSE-Amigos/index.js:19-25` | `#071d25`, `#07151d`, `#10252e` (fundos), `#c89b3c`, `#725f32` (bordas), `#f0e6d2`, `#a8aaa2`, `#7bd5a7` (ok), `#f3a090` (erro), `#36474b` | `Arial` (19, 21), `Georgia` (25) | 13, 12, 21, 16 | 4, 5, 6, 10px; borda ouro 1px; sombra `0 15px 50px #000a` |
| Pins do Swiftplay | `ROSE-SwiftplayPins/index.js:40-58` | `#07151d`, `#081e29`, `#010a10`, `#c89b3c`, `#f0e6d2`, `#cdbe91`, `#0ac8b9`, `#f4a58a`, `#a88948`, `#463e2c` | `Arial` (40), `Georgia` (50, 53) | 13, 12, 11, 16, 20 | 8px; gradiente 145deg; sombra `0 8px 30px #000a` |
| Party | `ROSE-PartyMode/index.js:156-366` | `#c8aa6e`, `#f0e6d2`, `#5b5a56`, `#a09b8c`, `#463714`, `#0acbe6`, `#4ade80`, `#1e2328`, `#3c3c41`, `#785a28` | `var(--font-display)`, `var(--font-body), Arial`, `monospace` (344) | 10, 11, 12, 14, 18 | 2, 3px, 50% |
| Painel de configurações Rose | `ROSE-SettingsPanel/index.js:88-2144` | 34 cores distintas: `#c8aa6e` (35×), `#cdbe91` (33×), `#1e2328`, `#463714`, `#010a13`, `#f0e6d2`, `#ff6b6b` (773) | `Beaufort for LOL` (33 declarações, `@font-face` em 88) | 10 a 18 | 0, 2, 3, 4, 10px, 50% |
| Roda de skins e cromas | `ROSE-ChromaWheel/index.js:146-334`, `ROSE-FormsWheel/index.js:422` | `#f0e6d2`, `#27211c`, `#463714`, `#010a13`, `#be1e37`, `#c89b3c`, `#c8aa6e`, `#df9117` | `LoL Display`, `LoL Body` (fontes do cliente) | 24 (título) | 50% |
| Seletor de skins e botão-roda | `ROSE-CustomSkinSelector/index.js:305-669`, `ROSE-CustomWheel/index.js:479-863` | `#c8aa6e`, `#3c3c41`, `#5b5a56`, `#a09b8c`, `#5c5c61`, `#8b8b8b`, 16 `rgba()` | `Spiegel`, `LoL Body` (CustomWheel:545) | 10, 11, 12, 13 | 0, 2, 3px; borda esquerda 3px ouro na linha ativa |
| Modo histórico | `ROSE-HistoricMode/index.js:43-687` | marrons do cliente (`#81602b`, `#423828`, `#fcf0d7`, `#857a72`), 48 `rgba()` | do cliente | — | 2px, 50% |
| Sorteio, monitor, i18n, UI base | `ROSE-RandomSkin`, `ROSE-SkinMonitor`, `ROSE-I18n`, `ROSE-UI/index.js:254-276` | sem UI própria relevante, salvo o botão ouro de `ROSE-UI` (`#c8aa6e`, `#a07b32`, `#785a28`, `#3c3c41`) | do cliente | — | herdado |

Essas telas imitam o cliente do LoL (ouro, azul-marinho, Beaufort/Spiegel). O protótipo aprovado (D-017)
usa cinza neutro e Oswald/Inter. Hoje o jogador vê duas linguagens; dentro do Hub, os painéis herdados
aparecem repintados por cima.

### 2.4 Overlays sobre o jogo (Tk)

| Superfície | Arquivo | Cores | Fonte | Tamanho |
|---|---|---|---|---|
| Ouro (placar) | `sexo2/overlay/gold_overlay.py:27-30,156-165` | aliado `#4f8cff`, inimigo `#e5484d`, neutro `#a4a9b0` (iguais aos do protótipo); chave de transparência `#010203` | `Segoe UI` bold | 15 (totais), 12 (linhas) |
| Aprimoramentos | `sexo2/overlay/augment_overlay.py:30-33,108-116` | texto `#ececec`, apagado `#a4a9b0`, destaque `#f2d27a` (não existe nos tokens) | `Segoe UI` (bold no texto principal) | `max(10, 1,3% da altura)`; nome, 3 a menos |
| Atualizador | `updater_main.py:122` | padrão do Tk | `Segoe UI` 18 bold | 18 |
| Aviso (toast) | não há toast próprio no código. O protótipo define `.s2-toast` (`styles.css:141`), que não foi levado ao `SEXO2-Style`. `ROSE-HistoricMode` usa o toast nativo do cliente (439-548) | — | — | — |

D-007 só autoriza Segoe UI em componentes nativos do Windows. Os textos dos overlays são desenhados em canvas
Tk, não são componentes nativos: **PENDENTE** decidir se ficam em Segoe UI (Tk não carrega WOFF2) ou passam a
Inter. O visual do overlay de ouro (D-119) não é tocado aqui.

## 3. Divergências (as principais)

1. **Duas linguagens visuais.** 16 de 19 plugins não usam tokens: ouro `#c8aa6e`/`#c89b3c`, azul-marinho
   `#071d25`/`#010a13` e bordas ouro, enquanto o protótipo aprovado é neutro com acento branco.
2. **Fontes fora de D-007.** Beaufort for LoL (`SEXO2-Settings:22`, `ROSE-SettingsPanel` 33×), Georgia
   (`ROSE-Amigos:25`, `ROSE-SwiftplayPins:50,53`), Arial (`ROSE-Amigos:19`, `ROSE-SwiftplayPins:40`), Spiegel e
   `LoL Display`/`LoL Body`. `SEXO2-Startup` usa Inter sem carregá-la.
3. **Raio.** Aprovado: 2px (e 50% para ícone redondo). Em uso: 3, 4, 5, 6, 8 e 10px (`ROSE-Amigos:19-23`,
   `ROSE-SwiftplayPins:47`, `ROSE-SettingsPanel`).
4. **O Hub repinta com `!important`** (69 ocorrências) em vez de os painéis adotarem o padrão; qualquer mudança
   de DOM num plugin legado quebra o visual do Hub sem erro.
5. **Cores soltas e sem papel.** Linha interna `#202327` (`SEXO2-Assistant:183,211`; tabela do protótipo,
   `styles.css:135`), borda de hover `#3a3e44` (Assistant:174), fundos `#0b0c0d`, `#111`, `#fff`, `#1a1c20`;
   estados com verdes e vermelhos todos diferentes: ok `#7bd5a7`, `#4ade80`; erro `#f3a090`, `#ff6b6b`,
   `#d9a796`, `#f4a58a`, `#e5484d`.
6. **`SEXO2-Style` incompleto.** O protótipo tem foco visível (`.s2-input:focus`, `styles.css:123`), `danger`
   (109), segmentado (115-118), switch (124-127), tabela (133-136), diálogo (137-140) e toast (141). O plugin
   compartilhado não leva nenhum deles (`SEXO2-Style/index.js:28-56`).
7. **Três versões do tooltip** (protótipo `.tip`, Style `.s2-tip`, tooltips nativos do cliente).

## 4. Componentes duplicados hoje

| Componente | Variantes encontradas |
|---|---|
| Botão | Style `.s2-btn` (28px, 1px `--s2-line`); Hub (`5px 10px`, mesma cor); Amigos (`#10252e`, borda `#725f32`, raio 4, `padding:8px`, linha 19); Swiftplay (`#07151d`, borda ouro, linha 40); Settings/ModLibrary (botão nativo sem estilo); CustomWheel (`#1e2328`/`#3c3c41`); Party (`#463714`) |
| Aba | Style `.s2-tabs`; Hub `.hub-subnav` (cópia com `!important`, linhas 24-26); Amigos `.ra-tabs` (oculta pelo Hub, 35); CustomWheel (abas com borda esquerda ouro) |
| Seletor / campo | Style `.s2-select`/`.s2-input`; Hub força o mesmo em todos (44); Amigos (`#10252e`, raio 4); ModLibrary `select[multiple]` nativo |
| Linha de lista | Assistente `.rec-row` (`6px 4px`, `#202327`); ModLibrary `.s2-mod-row` (`10px 0`, `#25343d`); CustomWheel `.rose-wheel-summary-row` (gradiente, borda esquerda ouro 3px); Swiftplay `.rsp-row` (`14px 0`, `#463e2c`) |
| Cartão | Assistente `.rec-card`; Amigos `.ra-card` (raio 6, `#36474b`); Hub reescreve `.ra-card` com raio 0 e `padding:8px` (38) |
| Painel | Assistente/Hub (`--s2-surface`, 1px, sombra `0 8px 30px`); Amigos (raio 10, sombra `0 15px 50px`); Swiftplay (gradiente, raio 8) |
| Chip / selo | Contador do Assistente (`.ip-count`, `rgba(0,0,0,.75)`, 10px); `.s3xo-room-badge` (Party, oculto pelo Hub); nenhum padrão |
| Vazio / erro / carregando | Assistente `.skeleton` (gradiente `#1b1d21`→`#22252a`) e spinner do Style; Amigos `.ra-muted/.ra-error`; ModLibrary só texto ("Nenhum mod nesta busca."); sem padrão para erro |

## 5. Padrão proposto

### 5.1 Tokens

Estado: **A** = aprovado; **P** = presente no protótipo aprovado (D-017) mas cores ainda sob D-102;
**NOVO** = não existe, PENDENTE.

| Papel | Token | Valor | Estado |
|---|---|---|---|
| Fonte de títulos | `--s2-font-display` | Oswald, Segoe UI | A (D-007) |
| Fonte de texto | `--s2-font-text` | Inter, Segoe UI | A (D-007) |
| Números de estatística | `--s2-numeric-stats` | `tabular-nums` | A (D-007) |
| Fundo da página/campo | `--s2-bg` | `#0d0e10` | P (D-102) |
| Superfície | `--s2-surface` | `#15171a` | P (D-102) |
| Superfície elevada | `--s2-surface-2` | `#1b1d21` | P (D-102) |
| Hover | `--s2-hover` | `#22252a` | P (D-102) |
| Linha / borda | `--s2-line` | `#2a2d32` | P (D-102) |
| Linha suave interna | `--s2-line-soft` | `#202327` | NOVO (hoje fixo em 2 lugares) |
| Texto | `--s2-fg`, `-2`, `-3` | `#ececec`, `#a4a9b0`, `#6e747b` | P (D-102) |
| Sobreposição (tooltip) | `--s2-overlay` | `#0b0c0d` | NOVO (fixo em Style:57 e no protótipo) |
| Time aliado | `--s2-ally` | `#4f8cff` | P (D-009, D-102) |
| Time inimigo | `--s2-enemy` | `#e5484d` | P (D-009, D-102) |
| Foco | `--s2-focus` | `#ececec` | P |
| Texto sobre fundo claro | `--s2-on-fg` | `#111111` | NOVO (hoje `#111` fixo) |
| Erro | `--s2-error` | igual a `--s2-enemy` ou cor própria | NOVO, junto com a cor de sinal (D-102) |
| Sucesso / aviso | `--s2-ok`, `--s2-warn` | sem valor proposto | NOVO, depende de D-102 |
| Destaque do overlay | `--s2-highlight` | `#f2d27a` (hoje em `augment_overlay.py:33`) | NOVO, D-112/D-119 |
| Ouro do cliente | — | `#c8aa6e` | sem lugar no padrão: decidir se sai dos painéis SEXO2 |

Escala tipográfica (D-014/D-101; tamanho final ainda em avaliação): display 34 Oswald 600; heading 18 Oswald 500;
nome no assistente 22 Oswald 600 (NOVO como token); category 12 Oswald 500 caixa alta +.06em; body 14 Inter;
controle 13 Inter 600 (NOVO como token); small 12; micro 10-11 (contador/detalhe, NOVO); stat 14; stat-big 30.
Tamanhos soltos a eliminar: 16, 20, 21, 24 (fora do cliente), `1rem`.

| Grupo | Token | Valor | Estado |
|---|---|---|---|
| Espaçamento | `--sp-1`..`--sp-4` | 4, 8, 12, 16 | P (D-101) |
| Espaçamento extra | `--sp-5`, `--sp-6` | 20, 24 | NOVO (o `brand` do Hub usa 20) |
| Raio | `--radius` | 2px; 50% só para ícone redondo e switch | P; falta no `SEXO2-Style` |
| Borda | — | 1px `--s2-line`; seleção = barra interna de 2px (`inset 2px 0 0` em linha e menu, `inset 0 -2px 0` em aba) | P |
| Sombra | `--s2-shadow` | `0 8px 30px rgba(0,0,0,.55)`, só em elementos flutuantes | NOVO como token |
| Desabilitado | — | `opacity:.45` | P |
| Foco | — | `outline:1px solid var(--s2-focus); outline-offset:-1px` | P no protótipo; ausente no Style |
| Movimento | `--s2-dur` | `.12s` (switch); nenhuma outra transição | NOVO |

### 5.2 Componentes (um só visual cada)

Todos derivam do protótipo aprovado. A última coluna é o que `SEXO2-Style` precisa ganhar antes da migração.

| Componente | Visual proposto | Falta no `SEXO2-Style` |
|---|---|---|
| Botão | `.s2-btn` 28px, 1px linha, fundo `surface-2`, 13px 600; variantes `primary` (fundo claro), `ghost`, `danger`; desabilitado .45 | `danger` |
| Aba | `.s2-tabs`: Oswald 13 caixa alta, ativa com barra inferior de 2px | pronto |
| Segmentado | `.s2-seg`, ativo invertido | sim |
| Seletor e campo | `.s2-select`/`.s2-input` 28px; foco com contorno de 1px | foco |
| Switch | `.s2-switch` 30x16 | sim |
| Linha de lista | altura por conteúdo, borda inferior `line-soft`, hover `hover`, selecionada com barra interna de 2px | sim (unifica `.rec-row`, `.s2-mod-row`, `.rsp-row`, `.rose-wheel-summary-row`) |
| Cartão | `surface-2` + borda `line`; hover com borda mais clara (hoje `#3a3e44`, vira token) | token |
| Chip / selo | NOVO: texto 10-11, caixa `rgba(0,0,0,.75)` ou borda `line`, sem cor decorativa | sim, PENDENTE |
| Painel | `.s2-panel`, 1px, raio 2, `--s2-shadow` se flutuante | sombra |
| Vazio | `.s2-empty`, 13px `fg-3`, uma frase | pronto |
| Erro | texto `--s2-error` (hoje `--s2-enemy` no rodapé do assistente), mesma posição do vazio | PENDENTE (cor) |
| Carregando | `.s2-spinner` e `.skeleton` do assistente | skeleton |
| Tabela, diálogo, toast, tooltip | como no protótipo (`styles.css:133-148`) | tabela, diálogo, toast |

Textos visíveis não mudam nesta proposta (D-107 pendente).

## 6. Plano de migração (somente plano)

Pré-requisitos: aprovação do usuário dos itens do catálogo; mover as cores e tokens para `tokens.json` (seção
`proposed` até aprovar), com `build_tokens.py` gerando também o bloco usado por `SEXO2-Style` e um módulo Python
para os overlays; `python design/build_tokens.py --check` no CI (`tests/test_design_tokens.py` já existe).

| Ordem | Alvo | Risco | Testes que precisam passar | Observação |
|---|---|---|---|---|
| 0 | `SEXO2-Style`: completar componentes (foco, danger, seg, switch, tabela, diálogo, toast, chip) | baixo | `tests/test_assistant_plugin.cjs`, `tests/test_design_tokens.py` | só acrescenta CSS; nada o usa ainda |
| 1 | `SEXO2-Settings` e `SEXO2-ModLibrary` (89 e 94 linhas, próprios) | baixo | `tests/browser_mod_library.cjs`, `tests/test_mod_library.py` | trocar Beaufort/Spiegel e `#1e282d`/`#25343d` por tokens; só depois remover do Hub as linhas 44-50 |
| 2 | `SEXO2-Startup` | baixo | `tests/browser_startup.cjs`, `tests/test_startup_policy.py` | a tela de carga é independente da ponte; manter essa independência (valores gerados, sem depender do Style) |
| 3 | `ROSE-Amigos` e `ROSE-SwiftplayPins` | médio | `tests/test_friends_ui.cjs`, `browser_friends.cjs`, `test_swiftplay_pins_ui.cjs`, `browser_swiftplay_scroll.cjs`, `browser_hub.cjs` | depois disso dá para apagar as sobreposições do Hub (34-41) |
| 4 | `ROSE-PartyMode` e `ROSE-SettingsPanel` | alto (5233 linhas; Beaufort 33×; hospedados no Hub) | `tests/test_party_ui.cjs`, `browser_hub.cjs` | aprovação do usuário por painel; mudanças em pedaços |
| 5 | Rodas e seletor de skins (`ChromaWheel`, `FormsWheel`, `CustomWheel`, `CustomSkinSelector`, `HistoricMode`) | alto | validação no cliente real | desenhadas sobre a seleção nativa; PENDENTE decidir se mantêm o visual do cliente de propósito |
| 6 | Overlays Tk (ouro, aprimoramentos) | médio | `tests/test_gold_overlay.py` | trocar constantes por módulo gerado, com os mesmos valores; fonte e destaque dependem de decisão; D-119 fica à parte |

Em cada passo: uma superfície por commit, formatação separada do comportamento (`scripts/ast_equal.py`) e
conferência no cliente real (teste simulado não substitui).

## 7. Decisões que o usuário precisa tomar

1. Cores finais, cor de sinal, erro/ok/aviso e destino do ouro `#c8aa6e` nos painéis SEXO2 (D-102, D-112).
2. Painéis herdados (Amigos, Pins, Party, Settings Rose): migram ao padrão neutro ou mantêm o visual do cliente
   LoL de propósito? As rodas sobre a seleção entram nessa pergunta (D-103/D-104).
3. Itens novos do padrão: `--s2-line-soft`, `--s2-overlay`, `--s2-shadow`, chip/selo, foco visível no Style,
   tamanhos 22/13/11 como tokens (D-101/D-103).
4. Fonte dos overlays Tk (Segoe UI ou Inter) e `--s2-highlight` (`#f2d27a`).
5. Aprovar a ordem e o formato (tokens gerados para JS e Python) do plano da seção 6.
