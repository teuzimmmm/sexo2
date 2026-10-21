# Organização da documentação

Atualizado em 18/10/2026. Inventário, padrão e pendências da documentação. O índice para leitura está em
[../README.md](../README.md).

## Padrão

**Estrutura**

- `README.md` (raiz): o que é o app, como atualizar e desenvolver, créditos. Aponta para `docs/README.md`.
- `CLAUDE.md` (raiz): regras do projeto. Só os ponteiros mudam quando um arquivo muda de lugar.
- `docs/README.md`: índice único. Todo documento novo entra nele.
- `docs/produto/`: decisões e glossário. `decisoes.md` é a única fonte de decisões; nenhum outro
  documento registra decisão nova.
- `docs/adr/`: arquitetura. `docs/lolalytics/`: biblioteca de coleta, com README próprio.
- `docs/arquivo/`: documentos superados. Não se apaga histórico; move-se para cá.
- `design/`: tokens, fontes, wireframes e protótipos. Cada pasta com explicação tem um `README.md` ou
  `ORIGEM.md`.

**Escrita**

- Português, frases curtas, sem emojis. Um assunto por documento.
- Títulos em `#` (um por arquivo), `##` e `###`, sem pular nível.
- Nomes de arquivo novos: minúsculas, sem acento, com hífen (`nome-curto.md`). Os existentes em
  maiúsculas ficam como estão para não quebrar links.
- Datas como `dd/mm/aaaa`. Caminhos do Windows em código: `%LOCALAPPDATA%\SEXO2`.
- Links relativos entre documentos. Nada de caminho absoluto.
- Fato com caminho, nome de arquivo ou número de teste deve ser conferido no código antes de escrever.

**Cabeçalho de estado** (só onde ajuda: planos, investigações e notas de entrega). Logo abaixo do título:

```
Estado: vivo | histórico | arquivado. Atualizado em dd/mm/aaaa.
```

Documentos vivos (decisões, roadmap, comportamentos) não precisam: o histórico do Git basta.

**Arquivar.** Quando um documento é superado: mover para `docs/arquivo/` com `git mv`, pôr no topo uma
linha `> Arquivado em dd/mm/aaaa: motivo.`, atualizar todo link e referência a ele (busca em todo o
repositório, inclusive comentários de código e testes) e registrar em `docs/README.md`.

**Verificação.** `python scripts/check_doc_links.py` falha se um link relativo ou uma referência
`docs/...`/`design/...` entre crases não existir. Rode antes de cada commit de documentação.

## Inventário

Última coluna: V = vivo, N = nota de entrega ou investigação (histórica), A = arquivado.

| Documento | Propósito | Data | Tipo |
|---|---|---|---|
| `README.md` | Apresentação, atualização, desenvolvimento, créditos | 2026-10 | V |
| `CLAUDE.md` | Regras do projeto | 2026-10 | V |
| `docs/README.md` | Índice | 18/10/2026 | V |
| `docs/produto/decisoes.md` | Fonte única de decisões | 2026-10 | V |
| `docs/produto/glossario.md` | Termos da interface (ainda vazio: nada aprovado) | 2026-10 | V |
| `docs/comportamentos.md` | Funções protegidas e cobertura | 2026-10 | V |
| `docs/ROADMAP.md` | Marcos M0 a M13 e pendências | 2026-10 | V |
| `docs/adr/README.md` | ADR-1 em diante | 2026-10 | V |
| `docs/MEDICAO.md` | Protocolo de desempenho | 2026-10 | V |
| `docs/VALIDACAO_WINDOWS.md` | Roteiro de validação real | 2026-10 | V |
| `docs/ATUALIZACOES.md` | Atualizador, central privada, publicação | 2026-10 | V |
| `docs/ARENA_BRAVURA.md` | Arena Bravura, 1.6.1 | 2026-10 | N |
| `docs/PERFORMANCE_1_6_3.md` | Desempenho, 1.6.3 | 2026-10 | N |
| `docs/MODS_E_AIRDROP.md` | Biblioteca em lote e AirDrop | 13/10/2026 | N |
| `docs/arquivo/DECISOES.md` | Entrega r6 | 10/2026 | A |
| `docs/arquivo/PROJETO_SEXO2.md` | Plano inicial | 13/10/2026 | A |
| `docs/arquivo/PLANO_CINCO_TAREFAS.md` | Plano e avanços até 1.6.4 | 13/10/2026 | A |
| `design/wireframes.md` | Moldes ASCII | 2026-10 | V |
| `design/fonts/ORIGEM.md` | Origem das fontes | 2026-10 | V |
| `design/propostas/sexo2-v1/README.md` | Protótipo estático | 2026-10 | V |

### `docs/lolalytics/`

| Grupo | Documentos | Tipo |
|---|---|---|
| Uso e contrato | `README.md`, `CORE.md`, `ARQUITETURA.md`, `FONTES.md`, `RISCO.md`, `RUNAS_E_ITENS.md`, `INTEGRACAO_MAIN.md` | V |
| Planos (16/10/2026, já executados) | `PLANO.md`, `PLANO_KEYSTONE.md`, `PLANO_MATCHUPS.md`, `PLANO_RISCO.md`, `PROPOSTA_MATCHUP_PAGES.md` | N |
| Validações | `VALIDACAO.md`, `CORE_VALIDACAO.md`, `RISCO_VALIDACAO.md`, `TESTE_MAYHEM_ARENA.md` | N |
| Investigações HTTP | `investigation-endpoints.md`, `investigation-sr.md`, `investigation-modes.md`, `investigation-reference-policy.md`, `INVESTIGACAO_MATCHUPS.md` | N |
| Evidência | `*-live-*.json` (respostas reais de 16 e 17/10/2026) | N |

Os planos e investigações dessa pasta não foram arquivados: são evidência datada do coletor e
arquivá-los é decisão de quem o mantém (ver pendências).

## Sobreposições e contradições encontradas

| Tema | Situação | Resolução |
|---|---|---|
| `DECISOES.md` e `produto/decisoes.md` | O primeiro era o histórico da entrega r6; não é registro de decisões do projeto atual | Arquivado; `produto/decisoes.md` já apontava para ele e foi atualizado. Nenhuma linha de decisão mudou |
| `ROADMAP.md`, `PROJETO_SEXO2.md`, `PLANO_CINCO_TAREFAS.md` | Três planos sobrepostos, os dois últimos de 13/10/2026 | Vale o `ROADMAP.md`; os outros foram arquivados |
| Pasta de dados | `ROADMAP.md`, `ATUALIZACOES.md` e `VALIDACAO_WINDOWS.md` diziam `%LOCALAPPDATA%\Rose`; o código usa `SEXO2` e move a `Rose` uma vez (`utils/core/paths.py`, `test_data_folder_migration`) | Corrigido |
| Nomes de arquivo de log | Viraram `sexo2_*.log`, `sexo2_runoverlay_*.log` e `sexo2_diagnostics.txt` (`config.py`, `utils/core/logging.py`, `utils/core/issue_reporter.py`); os `rose_*.log` antigos continuam sendo limpos e o `rose_diagnostics.txt` é renomeado uma vez. `rose.lock` mantém o nome | Documentação atualizada |
| Rótulos de marco | `ROADMAP.md` renomeou M6b para M13 e M13 para M5b; `MEDICAO.md`, `adr/README.md` e `comportamentos.md` usavam os antigos | Corrigidos para os novos |
| Comando de testes do README | Citava `unittest discover`; as regras pedem `scripts/run_tests.py` | Corrigido |
| `PREPROJETO.md` e `ANOTACOES.md` | Pré-projeto em aprovação e anotações do usuário, ambos vivos | Listados no índice |

## Comportamentos protegidos: conferência de caminhos

Todo arquivo, módulo e teste citado em `docs/comportamentos.md` existe. Observações, sem alteração:

- `ROSE-CustomWheel` é o nome curto de `Pengu Loader/plugins/ROSE-CustomWheel`.
- `test_anchor.cjs` está em `tests/`; o protótipo `js/anchor.js` fica em `design/propostas/sexo2-v1/`.
- A linha "Instância única" cita o mutex `RoseSingleInstance`, que continua com esse nome em `config.py`
  por compatibilidade.
- Os rótulos de marco da última frase foram corrigidos (M13, M7, M5b); o caminho de dados deixou de ser
  lacuna porque `test_data_folder_migration` o cobre.

## Pendências para decisão humana

- `produto/decisoes.md` cita "plano-mestre" como origem de D-001 e D-002, mas esse documento não está no
  repositório. Precisa de localização ou de uma nota do autor.
- Comentários em `party/core/party_manager.py`, `main/__init__.py` e `injection/overlay/match_context.py`
  citam `ROSE_0_3_DECISOES.md`, arquivo da base Rose que não está aqui. Não foram alterados (código).
- Em `produto/decisoes.md` as linhas D-115, D-116 e D-020 aparecem fora de ordem na tabela de aprovadas.
  Conteúdo e estado preservados; a reordenação pode ser feita pelo autor.
- Decidir se os planos de `docs/lolalytics/` seguem em linha ou vão para `docs/arquivo/`.
