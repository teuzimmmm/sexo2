# Workflow do SEXO2

Priorizar o menor consumo total necessário para entregar trabalho correto e
verificável. Estas são as convenções atuais; planos históricos em `docs/` não
obrigam a repetir agentes ou rodadas. Instruções explícitas do usuário prevalecem.

Para a 2.0, seguir [docs/SEXO2_2_0.md](docs/SEXO2_2_0.md). Instalação própria e
migração/limpeza do legado são critérios de publicação ainda não implementados.

## Execução e delegação

- Resolver diretamente ajustes pequenos, trabalho coeso, documentação e pesquisa
  curta. Delegar só quando o bloco autônomo compensar o contexto e a revisão.
- Preferir um agente; usar dois para blocos independentes. Mais agentes exigem
  benefício concreto. Não dividir automaticamente código, testes e docs em agentes.
- Quando disponível, usar `gpt-6-luna` com reasoning `low` para tarefas delimitadas.
  O coordenador cuida de arquitetura, decisões transversais e revisão. Não afirmar
  uma troca de modelo que o ambiente não permite.
- Passar contexto mínimo: objetivo, arquivos permitidos, contratos, erros, testes
  pertinentes e conclusão esperada. Evitar herdar toda a conversa por padrão.
  Dar ao agente um componente completo, com seus testes, sem sobrepor arquivos.
- Revisar a entrega completa uma vez; intervir antes apenas por bloqueio ou
  contrato incorreto. Corrigir detalhes diretamente e reutilizar o agente para
  retrabalho substancial. Não criar agente só para revisar outro por rotina.
- Se houver indisponibilidade ou limite de cota, informar uma vez e concluir
  diretamente o que for viável. Não insistir nem usar modelo caro automaticamente.

## Investigação, validação e fechamento

- Conferir Git e instruções; ler arquivos relevantes com `rg` e buscas agrupadas.
  Ampliar a investigação conforme as evidências. Não varrer tudo por padrão.
- Registrar plano e contratos para trabalho significativo; dispensar planos
  extensos para ajustes simples. O coordenador sempre confere o diff e as evidências.
- Rodar testes focados e regressões pertinentes ao fechar. Repetir só após mudança,
  falha ou dúvida relevante. Reaproveitar resultados válidos. Para docs simples,
  revisar e usar `git diff --check`, sem rodar toda a suíte.
- Registrar falhas anteriores sem repetir diagnósticos nem ampliar o escopo para
  corrigi-las automaticamente. Manter uma fonte de documentação por assunto.
- Usar mensagens e relatórios curtos. Não quantificar economia sem medição;
  quantidade de agentes e reasoning não comprovam menor consumo.

Preservar funcionalidades e escopo. Não copiar credenciais, configurações pessoais
ou chaves para código, fixtures, logs ou commits. Push, publicação, instalador e
release exigem autorização aplicável. Não enviar mensagens a terceiros.
