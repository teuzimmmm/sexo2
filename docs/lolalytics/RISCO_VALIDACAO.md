# Validação do filtro de risco — 2026-10-16

## Revisão e testes offline

O coordenador leu os diffs dos agentes Luna e revisou os contratos estatísticos,
as consultas e a persistência. A revisão corrigiu a referência dos itens após
filtrar keystone, acrescentou sua proveniência, tornou `cache_hit` agregado e
removeu a suposição incorreta de que todo valor de popularidade de Arena fica
entre 0 e 100. Nenhuma implementação do DraftGap foi copiada.

- `python -m unittest discover -s tests -p 'test_lolalytics_*.py' -q`:
  157 testes relacionados ao coletor/serviço, sem rede, passaram; a suíte geral
  abaixo também inclui esses testes.
- `python -m unittest tests.test_lolalytics_recommendations -q`:
  16 testes passaram após a revisão final, incluindo seleção, falhas, fonte,
  baseline, cache e validação de CLI.
- Configurações e adaptador: 13 testes Python passaram; o fluxo do painel passou
  em dois testes Node VM com o código real do plugin e DOM/bridge isolados.
- Compilação dos módulos Python, sintaxe do plugin e `git diff --check` passaram.

O teste sintético de sensibilidade usa 80%/50 jogos contra 53%/2.000 jogos,
com referência de 50%. Em `very-low`, vence a segunda observação; em
`very-high`, vence a primeira. São valores sintéticos de teste, não resultados
atribuídos a campeões do LoLalytics. As observações brutas permanecem intactas.

## Validação real limitada

Executado pelo coordenador:

```sh
python scripts/lolalytics_risk_probe.py --live --output docs/lolalytics/risk-live-2026-10-16.json
python -m lolalytics ahri --lane middle --recommend --risk-level low
```

O probe passou com seis GETs de fonte, nos níveis `very-low` e `very-high`:

| Consulta | GETs | Patch | Seleção / primária | Tabelas |
| --- | ---: | --- | --- | ---: |
| Ahri Ranked middle | 2 | 16.20 | win / 8992 | 12 |
| Jinx ARAM, tier all | 2 | 16.20 | win / 8008 | 12 |
| Ahri vs Annie, middle/middle | 1 | 16.20 | win / 8112, somente filtro de adversário | 11 |
| Jinx Arena, tier all | 1 | 16.20 | popularidade, sem página de runas | 18 |

Nessas amostras, os dois níveis mantiveram o mesmo candidato vencedor; a política
não força uma troca. Cada consulta repetida reutilizou todas as fontes pelo
cache, sem novo GET. A CLI real passou separadamente com mais dois GETs, Ahri
8992, seleção win e patch 16.20. Total desta validação: oito GETs de fonte.

O [relatório sanitizado](risk-live-2026-10-16.json) registra queries, URLs,
filtros resolvidos, políticas, métricas dos candidatos e amostras de tabelas.
Arena manteve WR e pontuações de WR indisponíveis em itens/aprimoramentos.
As fontes são endpoints internos do site, sujeitos a mudanças.

## Regressões e limites do ambiente

Suite Python completa em Linux, com `PYSTRAY_BACKEND=dummy`: 381 testes,
nenhuma falha de asserção, um erro preexistente na importação de
`test_startup_policy` (`ctypes.windll` só existe em Windows), um teste de evento
nativo de Windows ignorado. Os demais testes passaram.

Node: os dois testes novos de configurações, dois de amigos e nove de pins
passaram. Os sete testes de `test_party_ui.cjs` falham porque seu sandbox não
define `window`. O coordenador reproduziu as mesmas sete falhas usando somente
esse teste e seu plugin extraídos do commit anterior `b517687`; nenhum dos dois
arquivos foi alterado nesta extensão.

O painel foi exercitado com VM/DOM isolados; não foi aberto no cliente LoL real.
Não foram implementados draft, overlay ou importação. A política seleciona entre
os dois layouts completos confirmados e não estima a WR conjunta de nove runas
nem a de seis itens. O consumidor futuro deve preservar a política da
`Recommendation` ao planejar páginas e distinguir a pontuação local da WR exibida.
