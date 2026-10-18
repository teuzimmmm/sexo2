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

## Diretrizes de comportamento
Diretrizes para reduzir erros comuns de LLMs em código. Somam-se às regras acima; em conflito, valem as do projeto.
Compromisso: priorizam cautela em vez de velocidade. Em tarefas triviais, use o bom senso.

### 1. Pensar antes de codificar
Não presuma. Não esconda a confusão. Exponha as compensações.
- Declare as suposições. Na dúvida, pergunte.
- Se houver várias interpretações, apresente-as; não escolha em silêncio.
- Se existir um caminho mais simples, diga. Discorde quando fizer sentido.
- Se algo estiver confuso, pare, diga o que é e pergunte.

### 2. Simplicidade primeiro
O mínimo de código que resolve o problema, nada especulativo.
- Nenhuma funcionalidade além do pedido.
- Nenhuma abstração para código de uso único.
- Nenhuma "flexibilidade" ou configuração que não foi pedida.
- Nenhum tratamento de erro para cenários impossíveis.
- Se escreveu 200 linhas e cabia em 50, reescreva.

Teste: um engenheiro sênior diria que está complicado demais? Se sim, simplifique.

### 3. Mudanças cirúrgicas
Mexa só no necessário. Limpe só a sua própria bagunça.
- Não "melhore" código, comentários ou formatação vizinhos.
- Não refatore o que não está quebrado.
- Siga o estilo existente, mesmo que você fizesse diferente.
- Código morto não relacionado: mencione, não apague.
- Remova imports, variáveis e funções que as SUAS mudanças deixaram sem uso; não remova código morto antigo sem pedido.

Teste: cada linha alterada deve se ligar diretamente ao pedido do usuário.

### 4. Execução guiada por objetivos
Defina critérios de sucesso e repita até verificar.
- "Adicionar validação" → escreva testes para entradas inválidas e faça-os passar.
- "Corrigir o bug" → escreva um teste que o reproduz e faça-o passar.
- "Refatorar X" → garanta que os testes passam antes e depois.

Em tarefas de várias etapas, apresente um plano breve:
```
1. [Etapa] → verificar: [checagem]
2. [Etapa] → verificar: [checagem]
```
Sinais de que funciona: diffs sem mudanças desnecessárias, menos reescritas por complicação e perguntas feitas antes da implementação, não depois dos erros.
