# Progresso da UX (branch ux/v0.9-prelaunch, base sexoatividade @2bf8607)

Origem: proposta A (sessão de design de 18/10/2026). Decisões registradas como pendentes (D-115 a D-121).
Nada foi validado no cliente real do LoL, no Windows nem em partida. Sem bump de versão.

| Item | Estado | Commit |
|---|---|---|
| 1 Painel: cantos retos, só "SEXO2" (Oswald), Inter no resto | feito | ae56a8d |
| 2 Menus Sala, Favoritas, Configurações, Suporte, Swiftplay; abre em Sala | feito | ae56a8d |
| 3 Favoritas (campeões, busca por skin, cromas separados, só Favoritar) | feito | ca9fccf |
| 4 Swiftplay | parcial | ae56a8d |
| 5 Assistente 452x492 | feito (ver limites) | b332320 |
| 6 Overlay de ouro: topo só com a diferença (ex.: -210) | feito | veja git log |

## Testes
- `python scripts/run_tests.py -q`: 673 testes; as únicas falhas são as 7 da linha de base deste Mac
  (4 módulos de launcher/atualizador e 3 de `test_patcher_stop`, que dependem do Windows). Novos testes:
  `skin-index`, croma favoritável à parte, builds do assistente, diferença do overlay.
- JavaScript: sem node/ruff aqui. Sintaxe checada com Deno; fluxos do painel e do assistente exercitados em jsdom
  (script descartável, fora do repositório). `tests/browser_hub.cjs` foi atualizado, mas não executado (Playwright).

## Bloqueios e limites
- Item 4: o painel Swiftplay mostra os 2 campeões e a escolha de skin (plugin `ROSE-SwiftplayPins`, já existente).
  NÃO foi feito o sorteio dos não tocados: as fixações são persistentes por campeão e `FriendsService.apply`
  grava fixações; sem distinguir "escolhido pelo usuário" de "sorteado" o sorteio viraria fixação permanente.
  Exige mudança no comportamento protegido de Swiftplay e teste próprio.
- Item 5: Onetricks não tem provedor (indisponível). Rota só exibe a rota do cliente (sem seletor).
  A aba Mods embute a biblioteca existente; a seleção de mod por skin segue no `ROSE-CustomWheel`
  (não removido). "Todas as configurações" abre o painel em Configurações, sem restaurar rascunho.
  A geometria (botão 36 px, painel 8 px acima, à direita) não foi medida no cliente.
- Item 3: busca por skin depende de `/lol-game-data/assets/v1/skins.json` (não confirmado no cliente real).
  Imagens usam `tilePath` do cliente; se faltar, fica o espaço vazio.
- Item 1: as fontes são servidas por `/asset/fonts/` (cópia dos WOFF2 de `design/fonts` em `assets/fonts`).
- Conjuntos e Sorteio saíram só da UI (código e testes mantidos). Sala, chave e sincronização não foram alteradas.
- `ROSE-Amigos` ainda tem as abas Perfis/Sorteio no código, ocultas pelo painel; o botão legado "Ferramentas" segue oculto.
- Não validado: CI Windows, ruff, `node --test`, cliente real, partida.
