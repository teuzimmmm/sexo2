# Progresso da UX (branch ux/v0.9-prelaunch, base sexoatividade @2bf8607)

Origem: proposta A (sessão de design de 18/10/2026). Decisões D-115, D-116, D-117, D-119 e D-120 aprovadas pelo usuário em 19/10/2026; a antiga D-121 ("Hub"/"Atividades") foi encerrada ("é só tirar").
Nada foi validado no cliente real do LoL, no Windows nem em partida. Sem bump de versão.

| Item | Estado | Commit |
|---|---|---|
| 1 Painel: cantos retos, só "SEXO2" (Oswald), Inter no resto | feito | ae56a8d |
| 2 Menus Sala, Favoritas, Configurações, Suporte, Swiftplay; abre em Sala | feito | ae56a8d |
| 3 Favoritas (campeões, busca por skin, cromas separados, só Favoritar) | feito | ca9fccf |
| 4 Swiftplay (escolha de skin + sorteio de quem não escolheu) | feito, não validado em partida | ae56a8d + rodada 2 |
| 5 Assistente 452x492 | feito (ver limites) | b332320 |
| 6 Overlay de ouro (refeito pelo coordenador) | feito | 0d4fe6b |

## Testes
- `python scripts/run_tests.py -q`: 673 testes; as únicas falhas são as 7 da linha de base deste Mac
  (4 módulos de launcher/atualizador e 3 de `test_patcher_stop`, que dependem do Windows). Novos testes:
  `skin-index`, croma favoritável à parte, builds do assistente.
- JavaScript: sem node/ruff aqui. Sintaxe checada com Deno; fluxos do painel e do assistente exercitados em jsdom
  (script descartável, fora do repositório). `tests/browser_hub.cjs` foi atualizado, mas não executado (Playwright).

## Bloqueios e limites
- Item 4: quem não tem pin do SEXO2 nem skin escolhida na sessão recebe um sorteio ponderado (favoritas primeiro)
  ao iniciar a busca (`SwiftplayHandler._draw_candidates`). O sorteado fica só em memória (`_drawn`): nunca vira pin
  nem entrada do modo Histórico. Limite: a "escolha direta no LoL" só é vista pelo rastreio existente (`swiftplay_skin_tracking`);
  skins que a conta possui não são sorteadas (o cliente as aplicaria). Remover a fixação conta como escolha do usuário.
- Sorteio ponderado (`friends/skin_selector.py`, de /skins): usado em seleção automática, sorteio temático, "sortear agora",
  Bravura e Swiftplay; histórico só em memória; `eligible` agora inclui cromas; catálogo expõe `rarity`/`chromaRarity`.
- Item 5: Onetricks removido (sem como funcionar); a Fonte mostra só Lolalytics. Rota só exibe a rota do cliente (sem seletor).
  A aba Mods embute a biblioteca existente; a seleção de mod por skin segue no `SEXO2-CustomWheel`
  (não removido). "Todas as configurações" abre o painel em Configurações, sem restaurar rascunho.
  A geometria (botão 36 px, painel 8 px acima, à direita) não foi medida no cliente.
- Item 3: busca por skin depende de `/lol-game-data/assets/v1/skins.json` (não confirmado no cliente real).
  Imagens usam `tilePath` do cliente; se faltar, fica o espaço vazio.
- Item 1: as fontes são servidas por `/asset/fonts/` (cópia dos WOFF2 de `design/fonts` em `assets/fonts`).
- Conjuntos e Sorteio saíram só da UI (código e testes mantidos). Sala, chave e sincronização não foram alteradas.
- `SEXO2-Amigos` ainda tem as abas Perfis/Sorteio no código, ocultas pelo painel; o botão legado "Ferramentas" segue oculto.
- Não validado: CI Windows, ruff, `node --test`, cliente real, partida.
