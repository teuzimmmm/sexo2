# Coletor LoLalytics

Biblioteca Python independente do SEXO2, com CLI JSON. Coleta dados agregados
públicos de campeão em **Ranked/Summoner’s Rift, ARAM, Arena e Swiftplay** por HTTP direto,
sem navegador permanente. Não é uma API oficial e depende de fontes internas
instáveis do LoLalytics. As integrações no cliente LoL ficam fora desta entrega.

## Executar

Na raiz do checkout, com Python 3.12+ e a dependência requests já utilizada pelo
SEXO2 (produção do aplicativo: Python 3.14):

```sh
python -m pip install requests==2.34.2
python -m lolalytics ahri --lane middle --patch 16.20
python -m lolalytics jinx --mode aram --tier all
python -m lolalytics ahri --mode arena
python -m lolalytics ahri --mode swift --builds
python -m lolalytics ahri --patch 16.19 --tier gold --region br --lane middle
python -m lolalytics ahri --patch 16.20 --item-sets
```

Para instalar o aplicativo inteiro, seguem valendo as dependências do
`requirements.txt`; o coletor usa somente requests e a biblioteca padrão.
Não precisa executar `main.py`, Pengu, LCU ou o jogo.

A saída é **um objeto JSON por linha**, por campeão. Erros vão a stderr com
exit code 1; uso inválido da CLI retorna 2. Em lote, linhas já emitidas continuam
válidas se uma consulta posterior falhar; nenhuma linha de sucesso é criada
para a consulta que falhou. Há no máximo 20 campeões explícitos por lote.

```sh
# Reexecutar o mesmo lote usa resultados ainda válidos do cache em disco.
# Escolha um diretório próprio, fora do checkout, para evitar versionar dados.
python -m lolalytics ahri jinx --mode arena --cache-dir /tmp/sexo2-lolalytics-cache
python -m lolalytics --help
```

`--patch` omitido resolve o patch corrente no site. `--ttl` aceita 0–86400
segundos, padrão 900; 0 desliga o cache. O cache atual pode refletir um patch
anterior durante esse prazo: conferir `resolved.patch`, `collected_at` e
`cache_hit`. Não há fallback silencioso para dados expirados. `stale` é sempre
false nesta fase; um recurso futuro de fallback precisará alterar isso.

Filtros aceitos conservadoramente:

| Campo | Valores |
| --- | --- |
| champion | Slug minúsculo explícito do site, como ahri ou jinx; não há resolução automática de nome/ID |
| mode | ranked, aram, arena |
| lane | ranked: all, top, jungle, middle, bottom, support; nos demais modos somente all, omitido na URL |
| tier | ranked: emerald_plus, diamond_plus, gold, all; ARAM/Arena: emerald_plus ou all |
| region | ranked: all ou br; ARAM/Arena: all |
| patch | Formato observado 16.20, 16.19; a disponibilidade histórica depende do site |

Aceitar um valor não garante que toda combinação tenha jogos ou seja aceita
pelo servidor. A biblioteca verifica os filtros resolvidos e retorna erro
se a fonte recusar, ignorar ou alterar a consulta. Não trata HTTP 200 sozinho
como prova de dados válidos. ARAM rejeitou até `lane=all` explícito com 404;
por isso o construtor monta parâmetros diferentes por modo.

## Builds condicionadas e planejamento

Para as sugestões estruturadas WR/Common filtradas pela keystone principal, use
`--builds`; `--keystone ID` também pode ser usado sozinho para inspecionar um
snapshot filtrado. A terceira sugestão disponível é Highest Win de um
adversário explícito (`--matchup --opponent annie`). Matchup não aceita filtro
de keystone nem produz core/taxa conjunta runas+itens. Exemplos Python, limites,
metadados e semântica completa estão em [CORE.md](CORE.md).

```sh
python -m lolalytics ahri --lane middle --builds
python -m lolalytics ahri --lane middle --matchup --opponent annie --opponent-lane middle --min-games 100
```

Para recomendações com ajuste local de risco, use `--recommend` e escolha
`--risk-level very-low|low|medium|high|very-high`; o padrão é `medium`.
Arena permanece orientada por pick rate. A preferência do SEXO2 fica em
Configurações e o serviço de recomendações a aplica quando não há override.
Fórmula, níveis, amostras, fontes e limites estão em [RISCO.md](RISCO.md).

```sh
python -m lolalytics ahri --lane middle --recommend --risk-level medium
python -m lolalytics ahri --lane middle --recommend --risk-level high --opponent annie --opponent-lane middle
python -m lolalytics jinx --mode arena --tier all --recommend
```

## Usar em Python

```python
from lolalytics import Client, Query, CollectorError

with Client(cache_dir='/tmp/sexo2-lolalytics-cache') as client:
    try:
        data = client.collect(Query('ahri', mode='arena'))
        cards = [r for r in data.records if r.category == 'augment_statistics']
        for card in cards[:3]:
            print(card.identifiers, card.metrics['pick_rate'], card.metrics['games'])
    except CollectorError as error:
        print(error)  # Mensagem sanitizada; não imprimir corpos/headers HTTP.
```

As futuras **cartinhas de aprimoramentos usarão pick rate**, conforme decisão
do usuário. Não há implementação dessas cartinhas nesta fase. Pick rate é a
métrica reportada pelo site, sem ranking de “melhor” ou cálculo de sinergia.
IDs são opacos; ID 0 é preservado e seu significado não foi confirmado. Uma
integração precisa validar catálogo/nome antes de apresentar isso como uma
opção de jogo real.

`collect_many(queries)` é um iterador sequencial de até 20 Queries. Validar e
salvar cada resultado permite retomar o lote com o cache; falhas propagam na
consulta correspondente. `collect_item_sets(query)` é opcional e somente ranked:
coleta tabelas adicionais com contadores brutos, sem calcular WR ou chamar
contadores de jogos/vitórias sem confirmação da semântica.

## Entender as saídas

`Snapshot.to_dict()` contém versão do schema, consulta original, filtros
resolvidos, ID/nome do campeão, patch, URL fonte, horário UTC da coleta,
`overview`, `records`, `raw`, `availability`, avisos e estado de cache.
`resolved.lane=all` é o filtro da navegação; `resolved.effective_lane` informa a
posição efetiva do header em ranked quando disponível. Não confundir as duas.

Cada Record guarda categoria, IDs ordenados como na fonte, métricas,
`source_path` e valores brutos. Métricas desconhecidas/ocultas ficam null,
nunca zero calculado para preencher ausência. Estados de categoria distinguem
available, unavailable e not_applicable.

| Categoria normalizada | Significado |
| --- | --- |
| item_combination | Conjunto inicial ou trinca explicitamente observada na fonte; não é uma build completa de seis itens |
| item_statistics | Estatística individual por tabela/slot; `item1` e `item2` não estabelecem ocorrência conjunta |
| rune_suggestion | Layout completo apresentado pelo site (4 primárias, 2 secundárias, 3 fragmentos), com métricas conjuntas indisponíveis |
| rune_statistics | Estatística marginal por ID/variante da tabela de runas, sem montar uma página observada |
| augment_statistics | Aprimoramentos de Arena por tabela original, com pick rate e jogos; WR suprimida |

A contagem/WR do resumo de runas coincide com a da keystone na amostra analisada.
Por isso não é apresentada como estatística conjunta dos nove IDs. `raw` mantém
o contexto upstream para inspeção, e os avisos explicam a limitação. Não juntar
as distribuições dos itens mais populares para anunciar uma build observada.
Taxas de seleção de itens podem ultrapassar 100 na fonte (múltiplas compras);
não são normalizadas ou limitadas artificialmente a 100.

Em Arena, a política Riot proíbe exibir win rates de itens e Augments em sites,
aplicações e overlays. Essas células são removidas também de `raw`, Records,
cache e CLI. Metadados de campeão e distribuições `place1..8` são preservados
como métricas distintas; não se deriva colocação da WR. Campos Arena desconhecidos
são descartados por precaução de schema, com aviso. O endpoint lazy de Arena
foi reproduzido, mas não é exposto: os contadores permitiriam derivar WR de itens.

## Robustez e operação

Uma Session HTTP é reutilizada e serializada por cliente, com conexão/leitura
limitadas (5/20 s), intervalo mínimo de 1 s, até 3 tentativas para falhas de rede
e 429/502/503/504, backoff limitado e Retry-After em segundos/data HTTP.
Se Retry-After superar 30 s, a chamada falha com o prazo disponível na exceção;
não tenta novamente antes desse prazo. 401/403 e redirects falham sem bypass.
O limite é de 4 MiB descomprimidos por resposta. No máximo duas operações por
Client entram na coleta simultaneamente; requisições idênticas em andamento
compartilham o resultado ou a falha, mantendo cópias independentes para chamadores.
Os limites são por cliente/processo, não uma quota global entre programas.

Cache em memória de até 32 entradas; disco opcional com gravação atômica,
nomes SHA256 da consulta e até 32 entradas de até 4 MiB de dados cada
(envelope/base64 ocupa mais espaço). Inclui rota/modo/patch/filtros na chave.
Arquivos corrompidos, grandes ou expirados viram miss. Arena é sanitizado antes
de persistir; não há cópia persistente automática do corpo original. Não há
logs de corpos, cookies, credenciais ou dados de jogadores.

## Verificar e manter

```sh
# Offline: fixtures reais sanitizadas e falhas de transporte simuladas.
python -m unittest discover -s tests -p 'test_lolalytics_*.py' -q

# Integração real explícita: 8 consultas públicas, até 3 tentativas por consulta.
python scripts/lolalytics_probe.py --live

# Risco real explícito: quatro cenários fixos, dois níveis por cenário.
python scripts/lolalytics_risk_probe.py --live

# Regressões padrão do SEXO2 no ambiente Windows suportado.
python -m unittest discover -s tests -q
```

O probe tem duas amostras por modo e um patch histórico fixo. Quando o patch
16.19 deixar de existir, ele deve falhar visivelmente; revisar a amostra e a
evidência antes de mudar a expectativa. Testes offline não comprovam o site
atual. Resultados desta entrega estão em [VALIDACAO.md](VALIDACAO.md).

Quando surgir SchemaError: repetir uma única consulta, comparar metadata,
loaders e tabelas com [FONTES.md](FONTES.md), revisar os bundles públicos
relevantes e atualizar decoder/parser somente com nova evidência. Nunca
converter falha em lista vazia. Reavaliar nomes/chaves, cardinalidade de runas,
posições das métricas e allowlist de Arena. Regenerar fixtures apenas de dados
agregados, mantendo manifest com filtros, data, hash original e transformações.
Sem dados pessoais, tokens, cookies ou chaves. Não ampliar coleta para todos os
campeões/patches por padrão.

Revisar antes de qualquer integração/distribuição as políticas vigentes:
[Riot League of Legends](https://developer.riotgames.com/docs/lol),
[Riot General Policies](https://developer.riotgames.com/policies/general) e
[robots LoLalytics](https://lolalytics.com/robots.txt). Não foi localizada página
própria de termos nas rotas convencionais testadas; isso não prova sua ausência
nem transforma endpoints internos em API pública autorizada/estável.

## Próximas fases

1. Associar recomendações ao alvo atual do draft e descartar respostas antigas
   quando a seleção de campeão ou adversário mudar.
2. Resolver IDs/nomes com catálogo validado por modo; projetar cartinhas com
   pick rate, jogos e alternativas, respeitando as regras vigentes.
3. Tratar importação de itens/runas como trabalho separado, validando IDs e o
   contrato do cliente LoL; não assumir que sugestão de runas tem WR conjunta.
4. Pesquisar variantes adicionais de ARAM e filtros/regiões fora da allowlist
   apenas com reproduções novas e revisão das políticas.

Integração das recomendações ao draft/overlay, importação de runas/itens e
escrita no cliente LoL não foram implementadas. Nenhum instalador, atualização
ou release foi produzido.

Arquitetura: [ARQUITETURA.md](ARQUITETURA.md). Evidências e matriz:
[FONTES.md](FONTES.md). Plano e rodadas: [PLANO.md](PLANO.md).

Swiftplay: apenas região `all`, tier `emerald_plus`, sem filtro de rota/runa.
`--builds` retorna summaries gerais (`conditioning=mode`); não afirmar que os
itens foram filtrados pela runa. Mayhem tem um adaptador comunitário separado,
fora do pacote `lolalytics`; ver [matriz de modos](../FUNCIONALIDADE_PARTIDAS.md).
