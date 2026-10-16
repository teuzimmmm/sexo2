# LoLalytics — fase 1

Plano registrado antes da implementação em 2026-10-16. Checkout inicial limpo,
branch `work`. Coordenador: modelo da sessão (não é possível trocá-lo via ferramentas).
Subagentes disponíveis: `gpt-6-luna`, esforço `low`. Nenhum push/release previsto.

## Etapas e critérios

1. [em curso] Reconhecimento pelo coordenador: páginas SR/ARAM/Arena e arquitetura
   do SEXO2; depois investigações independentes por agentes.
2. [pendente] Reproduzir fontes, filtros e categorias; consolidar matriz com estados
   confirmado por HTTP / observado no código / hipótese / indisponível. Guardar
   somente evidências públicas sanitizadas, comandos e limitações.
3. [pendente] Definir contratos e arquivos com base nas evidências, separando
   consulta, transporte, interpretação, modelos, cache, biblioteca e CLI.
4. [pendente] Implementar em rodadas pequenas de agentes; coordenador revisa os
   diffs, reproduz chamadas e testa antes de integrar. Adicionar rodadas se preciso.
5. [pendente] Testes offline com fixtures reais sanitizadas: filtros, schema,
   ausências, modos/patches, HTTP, retries, cache e concorrência. Integração real
   limitada e separada; regressões pertinentes do SEXO2.
6. [pendente] Documentar uso, arquitetura, manutenção, políticas e próximas fases;
   revisão final e commit local. Nenhum instalador, atualização ou release.

## Escopo e conclusão

Somente biblioteca e CLI independentes. Sem Pengu, importação de runas/builds,
overlay, seleção, skins ou atualizador. Não inferir combinações a partir de itens
individuais; manter métricas ocultas indisponíveis e preservar proveniência,
patch, filtros, horário e dados brutos relevantes. Fontes internas são instáveis.

Concluir quando fontes/capacidades tiverem reprodução; biblioteca e CLI cobrirem
somente escopo confirmado; cache, limites, falhas e testes estiverem revisados;
validação real e limitações estiverem registradas; mudanças tiverem commit local.
Bloqueios não serão contornados. Fixtures/logs/commits não conterão credenciais,
dados pessoais ou chaves. Fontes e regras de Arena serão revistas antes de
qualquer integração futura.

## Registro inicial

GET `https://lolalytics.com/`, `/lol/ahri/build/`, `/lol/ahri/aram/build/`,
`/lol/ahri/arena/build/`: HTTP 200 em 2026-10-16. HTML SSR Qwik 1.20.0;
patch exibido 16.20. Isso confirma páginas acessíveis, não endpoints de dados.
Projeto usa Python (produção 3.14), requests e unittest; ambiente atual Python 3.12.
Nenhuma instrução AGENTS.md encontrada no checkout. Módulo será isolado das
funções existentes; local e contratos serão definidos após investigação.
