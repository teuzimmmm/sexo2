# Risco nas recomendações e configurações

Plano registrado em 2026-10-16 antes da implementação desta extensão.

## Evidência e decisão

Fonte primária: vigovlugt/draftgap, commit
`872c6d5cebfec186fdebb14005fd42b2bf84ad22` (MIT), arquivos
`packages/core/src/risk/risk-level.ts`, `packages/core/src/draft/analysis.ts`
e `packages/core/src/builds/entity-analysis.ts`.
O mecanismo usa pseudoamostras: `(observado * jogos + referência * prior) / (jogos + prior)`.
Não é porcentagem de risco, intervalo de confiança nem probabilidade calibrada.

Usaremos os níveis very-low/low/medium/high/very-high e os priors de builds
3000/2000/1000/750/500. Padrão medium. A referência do SEXO2 será a WR do
campeão no contexto confirmado da consulta; isso difere dos priors históricos
e ratings cruzados do DraftGap. Não copiar código do projeto de referência.

## Contratos e propriedade

1. Coordenador: arquitetura, revisão de diffs, reprodução de fontes e validação real.
2. Agente de estatística: somente `lolalytics/risk.py` e `tests/test_lolalytics_risk.py`.
   Funções puras de validação, pontuação e ordenação; não alterar observações brutas.
3. Agente de API: somente `lolalytics/recommendations.py`, `lolalytics/client.py`,
   `lolalytics/matchups.py`, `lolalytics/__main__.py`, `lolalytics/__init__.py`
   e `tests/test_lolalytics_recommendations.py`. Uma recomendação explícita
   seleciona entre summary.win e summary.pick pela amostra da runa principal,
   preserva o layout completo fornecido pelo site e coleta seus itens pela
   keystone quando confirmado. Contra adversário, somente condicionamento ao
   adversário; nunca enviar keystone + opponent. Disponibilizar tabelas de itens
   ordenadas por risco separadamente, sem sintetizar seis itens como build conjunta.
4. Agente de configurações: somente `sexo2/services/settings.py`, novo
   `sexo2/services/lolalytics.py`, painel `SEXO2-Settings/index.js` e testes próprios.
   Persistir `[LoLalytics] risk_level`, preservar payloads antigos, aplicar a
   configuração por meio do serviço do aplicativo. Sem draft, importação ou overlay.
5. Agente de documentação: documentos de fonte/fórmula/uso/limites e probe real
   limitado, em rodada posterior aos contratos implementados.

## Critérios de conclusão

- Cinco níveis validados; risco menor aproxima mais da referência, maior do observado.
- Teste demonstra mudança real de vencedor com amostras distintas; WR original intacta.
- Dados sem WR, sem jogos ou com zero jogos são indisponíveis para pontuação;
  nunca viram zero/sucesso. Malformação gera erro compreensível.
- Tabelas e consultas não são misturadas; sem inferir estatísticas conjuntas.
- Runas: candidatos limitados aos dois layouts completos observados no summary;
  critério declarado como amostra da keystone, não da página inteira.
- Arena continua por pick rate; risco de WR não se aplica, sem reconstrução de WR oculta.
- Política aplicada localmente após o cache da fonte: mudar risco não exige rede
  para uma mesma fonte ainda válida; modo/patch/alvo permanecem isolados.
- CLI explícita e serviço usam os mesmos contratos, validação antes da rede.
- Configuração persiste atomicamente, preserva demais valores e aceita painel antigo.
- Testes offline, validação real limitada de ranked/ARAM/matchup/Arena, regressões
  pertinentes, revisão de cada entrega e commit local sem push.

## Progresso

- [x] Reconhecimento do código de referência e das configurações atuais.
- [x] Desenho e contratos registrados antes de implementar.
- [x] Implementação delegada e revisão.
- [x] Testes offline e validação real.
- [x] Documentação final; alterações prontas para commit local sem push.

## Revisão de conclusão

O nível de risco altera a seleção entre os layouts confirmados e a ordem das
observações em cada tabela; não é apenas um aviso de amostra mínima. A revisão
separou o baseline da seleção de runa do baseline dos itens filtrados, adicionou
`item_source` e corrigiu o indicador agregado de cache. Arena preserva valores
de popularidade acima de 100 quando fornecidos pelo site, sem atribuir-lhes uma
probabilidade nem recuperar WR proibida.

As tarefas foram delegadas a Luna low e revisadas pelo coordenador. Os agentes
atingiram o limite de uso na conclusão; o coordenador terminou os testes,
o probe e a documentação. Resultado real: quatro contextos, dois níveis,
seis GETs no probe e dois GETs da CLI. Regressões e falhas anteriores do ambiente
estão registradas em [RISCO_VALIDACAO.md](RISCO_VALIDACAO.md).
