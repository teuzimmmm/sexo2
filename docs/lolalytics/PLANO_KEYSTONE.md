# Core de builds relacionadas à runa principal

2026-10-16. Plano/contratos registrados antes da implementação. Pedido do usuário:
a API deve fornecer build relacionada à keystone e os conjuntos WR/Common para
futura importação no LoL. Não exige coocorrência das nove runas. Nesta rodada não
haverá escrita no cliente LoL/Pengu, instalador, release ou push.

## Etapas e conclusão

1. [concluído] Confirmar filtro keystone e schema em ranked/ARAM por chamadas
   limitadas; registrar fixtures reais sanitizadas, inclusive duas keystones.
2. [concluído] Implementar Query/validação/cache segregados por keystone.
3. [concluído] Implementar contratos de duas sugestões estruturadas de runas e
   blocos de itens (inicial/core/alternativas4/5/6), títulos com métricas do core.
4. [concluído] Integrar fluxo automático no Client e CLI, sem importação no jogo.
5. [concluído] Revisar todos diffs, testar erros, cache/concorrência e dados reais;
   executar regressões pertinentes e registrar limitações/documentação/commit.

Concluir quando API e CLI entregarem WR/Common com proveniência, keystone
resolvida, páginas de runas e itens do mesmo filtro. Nunca usar dados gerais como
fallback silencioso de uma consulta filtrada. Ausências/erros são explícitos.

## Fluxo e semântica

`Query(..., keystone: int | None = None)` adiciona filtro opcional. None não
altera URL histórica; IDs >0, inteiros não bool; só ranked/ARAM após evidência.
Arena rejeita filtro. `parse_payload` verifica nav.keystone contra consulta:
None aceita sentinel -1 ou ausência legada, filtro exige inteiro exato. Expõe
keystone nos filtros resolvidos. Chave de cache e lazy itemsets incluem filtro;
endpoint lazy filtrado deve ser reproduzido ou rejeitado, nunca devolver gerais.

`Client.collect_builds(query) -> BuildCollection`: ranked/ARAM somente.

- Coletar snapshot base validado. Sem filtro explícito, extrair keystone de
  `summary.win.runes.set.pri[0]` e `summary.pick.runes.set.pri[0]` separadamente.
- Fixar patch resolvido e, em ranked quando lane=all, effective_lane do snapshot.
  Fazer consultas por keystone, reutilizando a mesma resposta se ambas coincidirem
  mesmo com ttl=0. No máximo 3 consultas lógicas por coleta (base+2 filtradas).
- Com keystone explícita, usar uma única consulta filtrada para ambas as sugestões.
- Para cada seleção win/pick, usar runas e itens do summary correspondente na
  MESMA resposta filtrada. Validar que a página sugerida mantém a keystone
  solicitada. Sem montar páginas a partir de estatísticas marginais.
- Representar conjuntos iniciais e core com IDs/quantidades/ordem originais;
  alternativas item4/5/6 são alternativas independentes, não sequência conjunta.
- Títulos: `WR 52.7% / 1.795 jogos`, `Common ...`, usando EXCLUSIVAMENTE wr/n do
  core. Métricas da página inteira de runas e da build inteira continuam ausentes.
  Métricas faltantes: título `WR indisponível / jogos indisponíveis` conforme campo;
  sem inventar zero. Não usar WR da runa no nome de página de itens.
- Preservar metadados fonte/query/patch/coleta/cache por página, scope
  `keystone_conditioned` e aviso `not_full_rune_page_joint_sample`.
- IDs opacos internos preservados; não converter silenciosamente para IDs LoL.
  DTO da core é separado do formato LCU e não executa importação.
- Se faltar layout completo ou core observado em qualquer seleção: DataUnavailable,
  nunca resultado de sucesso parcial disfarçado de dupla completa. Schema inválido
  gera SchemaError. Todos os erros chegam ao chamador/CLI.

## Modelos e propriedade

Agentes gpt-6-luna reasoning low, contratos fixos, coordenador revisa/integrará.

A) filtro: `query.py`, validação keystone de `parsing.py` apenas, testes novos
`tests/test_lolalytics_keystone.py`. Não mudar normalizações existentes.

B) modelos e montagem pura: `builds.py` e `tests/test_lolalytics_builds.py`.
Dataclasses:
`ItemChoice(identifier: str, count: int, metrics: dict, raw: dict)`;
`ItemBlock(kind: str, choices: list[ItemChoice], metrics: dict, source_path: str,
ordered: bool)`;
`BuildPage(selection: str, label: str, title: str, keystone: int, runes: dict,
blocks: list[ItemBlock], core_metrics: dict, source_url: str, query: dict,
resolved: dict, collected_at: str, cache_hit: bool, warnings: list[str])`;
`BuildCollection(query: dict, pages: list[BuildPage], schema_version: int=1)`.
`BuildCollection.to_dict()` e `BuildPage.to_dict()` via asdict.
`build_page(snapshot, selection, keystone) -> BuildPage` valida snapshot filtrado,
runas complete pri4/sec2/mod3 com pri0 correspondente e summary.items.choices.
`ItemBlock` kinds starting/core/item4/item5/item6. Core exige set3 sem vazio,
wr/n podem None; start pode ausente -> omitir com aviso; alternativas ausentes
omitir com aviso. Quantidade inicial preservar set repetido em count por ID,
core conservar ordem da fonte e repetições (cada posição count1). ItemChoice
metrics de alternativas usam seus próprios wr/n; métricas core/start no bloco.
Não duplicar taxas de bloco como se individuais fossem. Campos unknown preservados
em raw relevante. Não acessar rede nesse módulo.

C) cliente/CLI e testes novos: `client.py`, `__main__.py`, `__init__.py`,
`tests/test_lolalytics_build_client_cli.py`. Integra contratos A/B após definidos;
`--keystone ID` para collect simples e `--builds` para modo dupla estruturada.
`--builds --item-sets` incompatíveis. `--builds` Arena rejeita antes de rede.
`collect_item_sets` com keystone: incluir filtro só com endpoint reproduzido;
caso contrário QueryError explícito. Lotes continuam limitados a20 campeões;
modo builds até3 consultas lógicas por campeão, mesmas regras de HTTP/retentativas.
Nenhum _once envolve chamadas collect aninhadas com semaphore (evitar deadlock).

Coordenador: investigação/fixtures/documentação/scripts/revisão e commits.
Teste de integração pequeno separado de offline, incluindo comparação sem/com
keystone e metadados exatos. Não repetir rede só para rerodar mesma validação.

## Revisão de encerramento

Implementação por subagentes gpt-6-luna reasoning low, com arquivos exclusivos.
Coordenador leu diffs, reproduziu fontes, revisou entregas e testes. Rodadas
adicionais corrigiram títulos sem métricas, schema/IDs, aliases de fixtures,
sentinela de adversário ausente, validação das posições e metadados do cache.
Nenhum fallback geral é usado para simular matchup/keystone indisponível.
Dados do jogo/overlay e importação permanecem futuros. Ver CORE_VALIDACAO.md
para testes offline, provas reais e regressões. Commit local ao fim da rodada;
sem push, release, instalador ou escrita no cliente.
