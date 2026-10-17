# SEXO2

App privado para League of Legends: núcleo Python + plugins Pengu no cliente. Fork do Rose (créditos em `LICENSE`).

## Regras
- **Decisões:** `docs/produto/decisoes.md` é a fonte única. Respeite as aprovadas. Nomes, menus, layout, cores, componentes, textos visíveis e automatismos novos exigem aprovação do usuário: registre como pendente e não implemente.
- **Interface:** antes de qualquer mudança de UI, use a skill `sexo2-ui`. Sem imagens geradas; propostas em ASCII ou HTML estático.
- **Compatibilidade:** preserve
  - os dados em `%LOCALAPPDATA%\Rose`;
  - o formato de patch e assinatura e as baselines de `scripts/compatibility_bases.json`;
  - o mutex de instância única;
  - as mensagens da ponte usadas pelos plugins.
  Mudança nesses pontos exige migração explícita e teste do formato antigo.
- **Comportamentos protegidos:** `docs/comportamentos.md`. Toque numa área só com o teste correspondente passando.
- **Desempenho:** nada de polling, timers ou observadores novos sem necessidade. Não declare ganho sem medição (`docs/MEDICAO.md`). Não remova recuperação ou watchdog sem teste que prove a equivalência.
- **Commits:** pequenos e por finalidade. Formatação separada de comportamento: prove com `python scripts/ast_equal.py`. Branch `sexoatividade`; nunca `main` nem releases sem autorização.

## Verificação
```
python scripts/run_tests.py -q          # todas as suítes Python
node --test tests/test_*.cjs            # plugins
ruff check . && ruff format --check .
python design/build_tokens.py --check
```
O CI Windows (`.github/workflows/release.yml`) roda tudo isso e é o critério de verificação. Teste simulado não substitui validação no cliente real.

## Referências
- Arquitetura: `docs/adr/README.md`
- Plano de marcos: `docs/ROADMAP.md`
