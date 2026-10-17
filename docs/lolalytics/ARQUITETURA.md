# Contratos da fase 1 (antes da implementação)

## Decisão baseada nas reproduções

Fonte principal: GET por campeão em `/lol/{slug}/build/q-data.json` (ranked)
ou `/lol/{slug}/{aram|arena}/build/q-data.json`. Coordenador reproduziu JSON
Qwik em SR com patch=16.19, tier=gold, region=br, lane=middle e em Jinx/Arena,
Jinx/ARAM tier=all, Ahri/Arena tier=all. A navegação resolvida reflete filtros;
header confirma campeão/patch (Arena usa patch da navegação, sem header.patch).
Não usar HTML para rotina: o estado estruturado público basta. Sem navegador.

Fonte adicional opt-in: GET `https://a1.lolalytics.com/mega/` com
`ep=build-itemset&v=1&patch=16.20&c=ahri&lane=all&tier=emerald_plus&queue=ranked&region=all`.
Coordenador reproduziu HTTP 200 JSON com `itemSets`, rows `[ids,counter_1,counter_2]`.
A semântica destes contadores ainda não foi confirmada: preservar como valores
brutos sem calcular win rate. Consultas adicionais só serão expostas quando
confirmadas por modo. Fontes internas não são API oficial ou estável.

## Arquivos e contratos

Pacote independente na raiz `lolalytics/`, conforme pacotes Python existentes;
usa requests já declarado e stdlib. Não importado pelo aplicativo nesta fase.
Testes `tests/test_lolalytics_*.py`, fixtures `tests/fixtures/lolalytics/`.

- `errors.py`: `CollectorError`, `QueryError`, `TransportError`, `HTTPStatusError`
  (status, retry_after), `ResponseTooLarge`, `SchemaError`, `DataUnavailable`.
- `query.py`: dataclass congelada `Query(champion, mode='ranked', patch=None,
  lane='all', tier='emerald_plus', region='all')`. Slug explícito, sem resolver
  nomes/IDs por adivinhação. `url` determinística e `key` estável; somente modos
  confirmados. Rejeitar lane específico fora de ranked. Catálogo de valores
  aceitos conservador, separado da confirmação de cada combinação no servidor.
- `models.py`: `Record(category, identifiers, metrics, source_path, raw,
  metric_scope)` e `Snapshot(query,resolved,source_url,collected_at,overview,
  records,raw,availability,warnings,stale=False,cache_hit=False)`, `to_dict()`.
  Identificadores de Record são strings opacas; campeão mantém inteiro upstream.
  Métricas normalizadas: `win_rate`, `pick_rate`, `games` (None se indisponível).
  Não criar classificação de melhor. Preservar rótulos pick/win upstream.
- `decoding.py`: `decode_page(body: bytes) -> (nav: dict, payload: dict)`;
  `_entry` aponta loaders em `_objs`; localizar por estrutura, sem índices ou
  hashes de loader fixos. Base36 só nos valores de containers; strings na tabela
  são literais. Undefined -> None. Limites de objetos/profundidade/expansão,
  referências inválidas/ciclos/marcadores não suportados -> SchemaError.
- `parsing.py`: `parse_page(body, query, source_url, collected_at) -> Snapshot`.
  Conferir filtros resolvidos e identidade; erro se servidor ignorar filtro.
  Header obrigatório e resposta válida; zero jogos é DataUnavailable, nunca
  sucesso falsamente vazio. Categorias opcionais ausentes são marcadas.
  Trincas observadas ≠ build completa de seis itens. Sugestões de runas têm
  seleção completa de IDs mas não prova de amostra conjunta: nenhuma métrica
  será atribuída à página inteira. Runas individuais continuam separadas.
  Em Arena, remover win rates de itens, combos e augments de TODAS as saídas,
  inclusive raw, e registrar política. Não inferir colocação de win rate.
- `transport.py`: `HTTPTransport.get(url)->bytes`, close/context manager.
  Session reutilizável, timeouts conexão/leitura, teto de resposta descomprimida,
  no máximo 2 conexões/queries; requests por sessão protegidos (sessão não é
  thread-safe); intervalo mínimo 1 s, retries limitados para timeout/conexão,
  429/502/503/504. Retry-After segundos/data respeitado: se além do teto de
  espera, falhar com erro sem nova chamada precoce. Nunca retry 401/403/CAPTCHA.
  Não aceitar redirects silenciosos ou URLs externas arbitrárias; sem cookies,
  autenticação ou logs de corpos/headers.
- `cache.py`: `FileCache(directory, ttl=900, max_bytes=...)`, get(key) retorna
  envelope `{'stored_at': epoch, 'value': bytes}` ou None; put atômico; estado
  corrupto é miss. Chave hash de URL completa inclui modo/patch/filtros; cache
  de bytes contendo nav/payload validados e sanitizados antes de gravar. Expiração decidida pelo client;
  sem fallback antigo implícito. Usuário pode limpar diretório; teto de tamanho.
- `client.py`: `Client(...).collect(Query)->Snapshot`, close/context manager;
  cache opcional de disco, default memória limitada; single-flight por chave
  dentro do cliente, mesmo sem cache. Falhas propagadas a todos os aguardantes.
  Sem fallback antigo nesta fase; `stale=False` sempre. Não persistir payload
  Arena sem redação. `collect_many` no máximo 20 consultas explícitas, sequencial
  e retomável pelo cache; nenhum catálogo baixado por padrão.
- `__init__.py` exports públicos; `__main__.py` argparse, saída JSON, erros stderr
  e exit != 0; query única ou lista limitada de campeões explícitos. Documentar
  semântica antes de exibir métricas. CLI não emite corpos/respostas de erro.

## Rodadas e revisão

Coordenador mantém errors/query/models/client/CLI e decisões transversais.
Agente transporte/cache: somente esses dois módulos + testes correspondentes.
Agente decoder: somente decoding.py + testes; fixtures fornecidas coordenador.
Agente parser: somente parsing.py + testes depois de fixtures e modelos prontos.
Cada diff será lido e testes executados; ajustes em rodadas adicionais delimitadas.
Não aceitar fixtures sintéticas como prova de funcionamento atual.

## Limitações assumidas

Sem endpoints de jogadores; sem dados pessoais. Sem paginação observada nas fontes
por campeão; conjuntos podem ter limites upstream desconhecidos. Catálogos de
IDs/nomes existem no loader, mas enriquecimento externo e conversão de IDs para
importação ficam para depois. Variantes ARAM não foram encontradas nos controles
consultados; não declarar suporte. Políticas e fontes podem mudar.

## Ajuste confirmado na integração

ARAM retorna 404 mesmo com lane=all explícito. Query só envia lane para ranked;
os demais modos mantêm lane=all nos filtros resolvidos, sem enviá-lo na URL.
O cache guarda envelope nav/payload sanitizado e horário, não corpo HTTP original.
A expiração é de 900 s para qualquer patch (configurável até 86400), conservadora
para correções históricas. Não há fallback antigo.
