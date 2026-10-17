# Validação da core de sugestões e matchups

2026-10-16. Linux/Python3.12.14; produção SEXO2 continua Windows/Python3.14.
A rodada anterior tinha72 testes offline do coletor. Esta extensão acrescenta
filtros de keystone/adversário, dupla WR/Common, sugestão de matchup e planejador
puro de páginas de itens, sem LCU/overlay/importação.

## Offline

`python -m unittest discover -s tests -p 'test_lolalytics_*.py' -q`:
**129 testes passaram**, sem rede. Inclui os testes anteriores e fixtures reais
novas em `tests/fixtures/lolalytics/keystone/` e `matchups/`, com manifests,
hashes das respostas originais, filtros e transformações. Nenhum dado de jogador.

Cobertura nova: filtro exato/ignorado, URLs distintas por alvo/posição/keystone,
sentinela sem adversário, patch/posições fixados, conflito header/nav/query,
cache separado/reutilizado, layout9IDs e blocos de itens preservados, métricas
faltantes/esquemas inválidos, nomes WR/Common originados do core, troca de alvo,
avisos de amostra, incompatibilidades pré-rede e erros sem sucesso parcial.
Planejador testa identidade/filtros/orçamento e independência das cópias,
preservação de blocos/quantidades/métricas, capacidade excedida e17/24blocos.
`compileall` e `git diff --check` passaram.

## Fontes reais e testes opt-in

```sh
python scripts/lolalytics_builds_probe.py --live
python scripts/lolalytics_matchup_probe.py --live
python -m lolalytics ahri --opponent annie --matchup
```

Primeiro probe: **3 cenários, 6 consultas lógicas, passou**:

- Ahri ranked/middle: dupla automática, keystones8992 e8112, 3consultas.
- Jinx ARAM/all ranks: dupla automática, ambas8008, 2consultas com reutilização.
- Ahri/middle keystone8112 explícita: duas sugestões da mesma resposta,1consulta.

Relatório: [core-builds-live-2026-10-16.json](core-builds-live-2026-10-16.json).
Todos verificam IDs/layout/source/filtro e core; nomes refletem somente wr/n do
core. Os nove IDs de runas não recebem uma WR conjunta inventada.

Segundo probe: **cenário completo, 5 consultas lógicas, passou**. Coletou a dupla
geral de Ahri e os matchups contra Annie e Ryze, fixando patch16.20 e posições
middle. Voltou a Annie sem nova consulta (cache_hit=true) e verificou que obter
Ryze não alterou o resultado anterior. Runas9IDs, target correto e7blocos de
itens por matchup; nenhuma falsa estatística de core. WR/Common+Annie deram
17blocos em uma página com orçamento20; adicionar Ryze deu24, foi recusado para
uma página e preservado em duas (20+4).

Relatório: [matchups-live-2026-10-16.json](matchups-live-2026-10-16.json).
A CLI de matchup também passou com posições omitidas: query all/all, resposta
resolveu campeão e adversário para middle,7blocos. Isso comprova o default nessa
amostra, não garante todas as combinações de campeões/posições.

Coordenador reproduziu as fontes principais e revisou o código de todos os
agentes; houve revisão cruzada do planejador, parser e montagem de matchup.
Após o último reforço de validação de posições, fixtures e testes de parser
confirmaram compatibilidade; o ajuste só rejeita posições contraditórias.

## Limitações confirmadas, sem substituições silenciosas

- Vs+keystone: seis testes com Ahri vs Annie/Ryze e keystones8992/8112 deram404.
  A API rejeita a combinação antes de rede. Matchup é condicionado ao oponente,
  com runa sugerida do próprio summary, sem alegar condicionamento por keystone.
- Vs não fornece core conjunto no summary amostrado: posições1..3 ficam
  individuais. `core_metrics` null; métricas gerais do confronto ficam em
  `matchup_metrics` com escopo separado, não no título da build.
- `region=all` explícito deu404 em vs; região fica restrita a all, omitida na URL.
  `tier=emerald_plus` e `patch=16.20` explícitos responderam200.
- Só ranked tem matchup confirmado nesta rodada. ARAM por keystone foi testado;
  Arena continua estatísticas e pick rate de itens/augmentos, sem builds de runas.
- O planejador recebe orçamento do consumidor; não afirma o limite real do LoL
  nem sabe quais páginas pessoais existem. Não apaga/substitui essas páginas.
- `min_games=100` é aviso local configurável, não medida de confiança. Nenhuma
  promessa de build ideal ou vitória foi criada.

## Regressões

A suíte padrão do SEXO2 foi executada com `PYSTRAY_BACKEND=dummy`. Continua com
a falha de importação Windows já observada antes das alterações: o módulo
`test_startup_policy` exige `ctypes.windll` no Linux. A execução final tem347
testes,1erro de importação e1skipped; não declaramos a suíte padrão aprovada.

A seleção compatível exclui exatamente
`unittest.loader._FailedTest.test_startup_policy`: **346 testes,1skipped, sem
falhas**. A seleção é a mesma documentada em VALIDACAO.md, sem alterar testes
existentes para esconder o erro. O teste Windows continua para ambiente/CI
suportado. Nenhum arquivo de skins, atualização, overlay ou fluxo de jogo mudou.
