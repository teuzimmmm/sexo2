# Validação da fase 1

2026-10-16, Linux/Python 3.12.14, requests 2.34.2. Produção do SEXO2 é
Windows/Python 3.14; não se afirma execução do aplicativo real neste ambiente.
Nenhum navegador pessoal, credencial de jogador, instalador ou release usado.

## Coletor offline

`python -m unittest discover -s tests -p 'test_lolalytics_*.py' -q`:
**72 testes, todos passaram**. Fixtures de respostas reais sanitizadas em
`tests/fixtures/lolalytics/`, com proveniência e transformações registradas.
Os casos de falha proposital usam dados modificados/fakes e não servem de prova
de disponibilidade do site.

Cobertura: rotas e filtros por modo/patch; schema Qwik, referências literais,
undefined/ciclos/limites, JSON malformado/números inválidos; identidade e filtros
resolvidos, schema/métricas ausentes, resposta sem jogos, layouts de runas;
redação Arena, pick rate e contagens; timeout/429/Retry-After delta e data,
servidor, forbidden/redirect, stream e tamanho; cache/expiração/corrupção/limites,
memória e disco compartilhado; requisições idênticas simultâneas e falha para
todos os aguardantes; lote limitado/retomável e CLI com falha parcial.

Arena nas fixtures versionadas já tem WR de itens/aprimoramentos removida.
Os testes de redação injetam métricas sintéticas para provar a remoção sem
versionar essas taxas. Os payloads reais completos de Arena também foram
validados em memória pelo probe e pelo coordenador, sem persistência do corpo
upstream pelo coletor. `compileall` e `git diff --check` passaram.

## Integração HTTP real, separada

`python scripts/lolalytics_probe.py --live` passou **8 verificações**:

| Consulta | Resultado |
| --- | --- |
| Ahri ranked, padrão emerald_plus/all | 200, patch16.20, 1051 Records |
| Jinx ranked, padrão emerald_plus/all | 200, patch16.20, 933 Records |
| Ahri ARAM, padrão emerald_plus/all | 200, patch16.20, 1188 Records |
| Jinx ARAM, padrão emerald_plus/all | 200, patch16.20, 1414 Records |
| Ahri Arena, padrão emerald_plus/all | 200, patch16.20, 2259 Records |
| Jinx Arena, padrão emerald_plus/all | 200, patch16.20, 2161 Records |
| Ahri ranked patch16.19/lane middle/tier gold/region br | 200, todos filtros refletidos e header validado |
| Lazy build-itemset, Ahri patch16.20 | 200, itemSets e response.valid=true |

O número de Records agrega tabelas/slots/contextos distintos; não é o número
de builds completas, campeões ou partidas. Não somar jogos entre essas tabelas.
Relatório estruturado sanitizado: [live-validation-2026-10-16.json](live-validation-2026-10-16.json).
Estas amostras comprovam as consultas dessa data, não todos os campeões,
patches, combinações de filtro ou disponibilidade futura.

Antes da correção, a primeira execução passou SR e recebeu 404 no ARAM: a URL
incluía lane=all. Reproduções isoladas confirmaram que ARAM sem lane aceita
`tier=emerald_plus&region=all`, enquanto `?lane=all` retorna 404. Construção por
modo foi corrigida e coberta offline; as oito verificações acima são da execução
posterior bem-sucedida. Não houve contorno de bloqueio/autenticação.

O coordenador também reproduziu o endpoint lazy específico `arena-itemset`:
HTTP200, chaves itemSets/cache/response, tabelas itemSet4..6, valid=true.
Está documentado mas não exposto na interface, pela semântica não validada dos
contadores e risco de exibir WR de itens Arena.

CLI real adicional, saída redirecionada para arquivos temporários fora do Git:

- `python -m lolalytics ahri --patch 16.20 --item-sets`: sucesso, 1051 Records,
  contadores lazy presentes, schema validado.
- `python -m lolalytics jinx --mode arena --cache-dir /tmp/sexo2-lolalytics-cli-cache`:
  sucesso, 2161 Records, aprimoramentos com pick rate/jogos e WR null.
- Repetição da mesma CLI Arena: cache_hit=true e mesma coleta, sem novo HTTP.

Depois dos últimos ajustes de cache/metadados, os corpos completos reais já
capturados foram novamente processados pelo código final em ranked, ARAM e
Arena. Os ajustes não ampliaram os endpoints ou a coleta.

## Regressões do SEXO2

Baseline antes de implementar, com backend de tray dummy:
`PYSTRAY_BACKEND=dummy python -m unittest discover -s tests -q`:
218 testes, 1 erro de importação, 1 skipped. `test_startup_policy` importa
`ctypes.windll.user32`, indisponível no Linux. Sem o backend dummy, outros módulos
de tray também falham por ausência de display X; é diferença de ambiente.

Execução final padrão com backend dummy: **290 testes, o mesmo erro de
importação Windows, 1 skipped**. Não é declarado que a suíte padrão passou.
Selecionando somente os testes compatíveis (excluindo exatamente o
`unittest.loader._FailedTest.test_startup_policy`), o resultado foi **289 testes,
1 skipped, sem falhas**. São 217 testes compatíveis anteriores + 72 do coletor.
Não foi alterado código do aplicativo para fazer testes Linux passarem.
O teste Windows permanece pendente para execução no ambiente suportado/CI.

Reprodução da seleção compatível usada, sem modificar testes existentes:

```sh
PYSTRAY_BACKEND=dummy python - <<'PY'
import unittest

def compatible(suite):
    result = unittest.TestSuite()
    for test in suite:
        if isinstance(test, unittest.TestSuite):
            result.addTests(compatible(test))
        elif test.id() != 'unittest.loader._FailedTest.test_startup_policy':
            result.addTest(test)
    return result

suite = compatible(unittest.defaultTestLoader.discover('tests'))
result = unittest.TextTestRunner().run(suite)
raise SystemExit(not result.wasSuccessful())
PY
```

## Revisão e limites finais

Coordenador leu código/testes dos agentes, reproduziu fontes principais e
revisou sua integração. Revisão adicional por agentes apontou duas falhas de
cache, corrigidas com regressões. O coletor fica isolado dos serviços existentes.

Indisponíveis: variantes adicionais ARAM, filtros fora da allowlist, tradução
validada de todos os IDs, garantia de sequência completa de seis itens e
estatísticas conjuntas de páginas completas de runas. WR de itens/aprimoramentos
Arena é indisponível intencionalmente; campos `xx.xx` continuam null.

Manutenção: revalidar q-data/loaders e posições das métricas a cada mudança
upstream; graph/header Arena são preservados como estatísticas de campeão e
precisam de revisão se o schema mudar. Políticas foram consultadas, não há
promessa de autorização ou estabilidade de endpoints internos.
