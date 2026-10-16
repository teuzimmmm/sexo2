# Referência: lolalytics-api e políticas públicas

Investigação em 2026-10-16. Evidência limitada a conteúdo público; sem autenticação, navegador, chamadas em lote, ou bypass. A chamada de reprodução foi somente um GET da página Ahri build, feito com urllib, porque `requests` não está instalado no Python do ambiente.

## Repositório `xPerSki/lolalytics-api`

- Origem: `https://github.com/xPerSki/lolalytics-api`; clone público shallow para `/tmp/lolalytics-api`, sem alteração no projeto de referência.
- HEAD observado: `3f40f7f57491921a96c21b4bf51c0282f9709e56`, commit `2025-07-16`, mensagem `auto-commit`; tag `v0.0.6`. `pyproject.toml` declara versão 0.0.6, Python >=3.6, dependências requests e lxml. README anuncia instalação via PyPI mas diz `[TBA] a lot of things`. Workflow GitHub Actions testa com Python 3.9.
- Licença exata no arquivo `LICENSE`: MIT License, Copyright (c) 2025 xPerSki. A permissão é expressamente concedida para usar, copiar, modificar, publicar, distribuir, sublicenciar e/ou vender cópias, condicionada à inclusão do aviso de copyright e da permissão em cópias ou partes substanciais. Código deste projeto não foi copiado. Se futuramente houver cópia de parte substancial, preservar o aviso e texto da licença; por ora a referência é arquitetural/comportamental.
- Arquitetura observada: pacote Python `lolalytics_api`, uma implementação `main.py`, erros próprios `InvalidLane` e `InvalidRank`, exports pelo `__init__.py`. Funções mapeiam nomes de rank/lane para parâmetros de URL; `requests.get`; parse de HTML por `lxml.html` e XPath absolutos; saída como JSON serializado em string. Não há cliente HTTP abstrato, timeout/status/retry/cache, fixtures ou modelo de dados explícito observado no código lido.
- Funções/documentação: `get_tierlist(n,lane,rank)` retorna posição/campeão/tier/winrate; `get_counters(n,champion,rank)` campeão e winrate; `get_champion_data(champion,lane,rank)` métricas gerais de página `/build/`; `matchup(champion1,champion2,lane,rank)` winrate e número de jogos; `patch_notes(category,rank)` lê a página inicial e extrai campeões listados como buffed/nerfed/adjusted. `display_ranks`/`display_lanes` expõem aliases. Não cobre ARAM, Arena, runas, árvores de build/itens, builds específicas, ou parâmetros de patch de forma documentada/observada. As rotas são páginas SR padrão (`/lol/{champion}/build/`, `/counters/`, `/vs/`), tierlist e home.
- Atualidade: commit/tag de julho/2025, sem evidência de manutenção posterior no shallow clone. É uma fotografia limitada ao HEAD/tag observado, não avaliação de todo histórico. A estratégia depende de estrutura DOM interna e XPath absolutos; quebra de layout é risco direto.

## Reprodução HTTP limitada

Comando (um GET, sem instalar dependências):

```sh
python - <<'PY'
import urllib.request
u='https://lolalytics.com/lol/ahri/build/'
req=urllib.request.Request(u,headers={'User-Agent':'Mozilla/5.0 (compatible; research/1.0)'})
with urllib.request.urlopen(req,timeout=20) as r:
    b=r.read()
    print('status',r.status,'bytes',len(b),'url',r.url)
    print('content-type',r.headers.get('content-type'))
    print('patch token present','16.20' in b.decode('utf-8','replace'))
PY
```

Resultado: HTTP 200, 620230 bytes, `text/html; charset=utf-8`, URL final igual à solicitada, marcador de patch `16.20` presente. O corpo inicia como documento HTML SSR Qwik 1.20.0. Essa requisição isolada confirma acesso à página, mas não demonstra que o scraper funciona. Em seguida, com `requests 2.34.2` e `lxml 6.1.1` já disponíveis, executei funções públicas diretamente do clone:

```sh
PYTHONPATH=/tmp/lolalytics-api/src python - <<'PY'
from lolalytics_api import get_champion_data, get_tierlist
print(get_champion_data('ahri'))
print(get_tierlist(3))
PY
```

Ambas retornaram JSON serializado sem exceção. Saída sanitizada de `get_champion_data('ahri')`: `winrate=52.88%`, `wr_delta=1.66%`, `game_avg_wr=51.22%`, `pickrate=9.19%`, `tier=S`, `rank=4 / 98`, `banrate=2.97%`, `games=165,144`. `get_tierlist(3)` retornou três linhas (`Cho'Gath`, `Jinx`, `Ekko`) com rank/tier/winrate. São valores observados no momento da chamada e voláteis, não fixtures. Não houve tentativa de funções Arena/runas; esse scraper não as declara. A chamada GET isolada não prova parser, e os resultados atuais provam apenas que essas duas funções/seletores funcionaram nesta execução.

## Robots e termos públicos LoLalytics

- `GET https://lolalytics.com/robots.txt`: HTTP 200, `text/plain`, 40 bytes. Corpo observado: `User-agent: AmazonAdBot` e `Crawl-delay: 1`. Não há regra `Disallow` no corpo retornado. Isso descreve somente o robots.txt observado; não constitui autorização legal/contratual, nem garante que outras regras inexistam.
- Tentativas de páginas convencionais de termos/política: `/terms/`, `/privacy/`, `/terms-of-service/`, `/terms-of-use/`, `/about/`, `/privacy-policy/`, `/contact/` retornaram HTTP 404. Assim, nesta investigação não foi localizada uma página pública de termos própria nessas rotas. Não inferir que inexiste em outra rota ou vinculada fora dessas páginas.

## Riot: texto público relevante para métricas Arena

- `GET https://developer.riotgames.com/docs/lol`: HTTP 200, HTML, 99451 bytes. Na seção de exemplos para chaves de produção, a página lista como aprovados “Aggregate player stats (no specific players).” Na seção “Examples of Unapproved Use Cases”, afirma exatamente: “Products cannot display win rates for Augments or Arena Mode items. This applies to all websites, applications and overlays.”
- Implicação específica: a página declara não aprovados produtos que exibem taxas de vitória de Augments ou itens do modo Arena, e estende explicitamente a regra a sites, apps e overlays. Não generalizar o texto para uma proibição expressa de toda estatística agregada de modo Arena: a frase nomeia as win rates de Augments/itens, enquanto stats agregadas sem jogadores específicos aparecem na lista aprovada. A página também não resolve se uma métrica específica fora desses alvos constitui win rate de Augment/Item; isso depende do dado/produto concreto. A orientação é evitar expor win rates de Augments e itens de Arena em qualquer interface do produto.

- `GET https://developer.riotgames.com/policies/general`: HTTP 200, página HTML, apresenta “LAST UPDATED: MAY 29, 2025”. O conteúdo diz que as políticas se aplicam a produtos do ecossistema de terceiros que trabalham com Riot API e Developer Tools; requer registro/auditoria pelo Developer Portal, alterações de produto auditadas, e recomenda serviços suportados para ingestão. Regras de integridade incluem não criar vantagem injusta, aumentar a diversidade das decisões (builds, composições, personagens/decks) e não remover decisões do jogo; podem destacar decisões importantes e oferecer múltiplas escolhas. Não cita LoLalytics, scraping de site de terceiro ou Arena especificamente.
- A página geral, portanto, não permite concluir que toda consulta de estatísticas agregadas de Arena é proibida ou permitida. Aplicabilidade a uma biblioteca local de leitura pública sem Riot API, registro, distribuição e apresentação ao jogador não está determinada apenas pelo texto capturado. Antes de produto público/integração de Arena, conferir políticas então vigentes e solicitar orientação/auditoria pela via Riot se necessário; não tratar essa recomendação como decisão jurídica.
- TOS oficial Riot `https://www.riotgames.com/en/terms-of-service` respondeu HTTP 200, mas esta captura não foi usada para uma conclusão específica sobre coleta de páginas LoLalytics nem estatísticas Arena. O escopo de referência aqui é a política pública do Developer Portal acima.

## Comandos/fontes e sanitização

Comandos de pesquisa usados: `git clone -q --depth 1 https://github.com/xPerSki/lolalytics-api /tmp/lolalytics-api`; `git log -1 --format='%H%n%cs%n%s'`; leitura local de `LICENSE`, `README.md`, `pyproject.toml`, `src/lolalytics_api/main.py`, `errors.py`, `__init__.py` e workflow de testes; scripts Python com urllib para GETs acima; `PYTHONPATH=/tmp/lolalytics-api/src python` para chamar `get_champion_data('ahri')` e `get_tierlist(3)`. Código HTTP não incluiu cookies nem chaves; não foram lidos arquivos de credenciais. Nenhum conteúdo pessoal foi registrado. Evidências contêm somente URL pública, status, metadados mínimos e excertos públicos curtos necessários para identificar os resultados.
