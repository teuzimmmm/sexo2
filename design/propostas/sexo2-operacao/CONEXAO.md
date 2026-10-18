# Conexão do painel

Abrir: `python3 design/propostas/sexo2-operacao/painel.py --data <pasta-de-estado> ver` (ou `Abrir-painel.command`). Estado de execução fica fora do repositório.

Progresso: os três trabalhadores gravaram `a|b|overlays.status.json` com `painel.py status`.

Consumo: os subagentes nativos só expuseram um total de tokens por sessão no aviso de conclusão (sem entrada/saída/cache, sem custo, sem contexto). O painel exige categorias, então o consumo ficou **n/d**; nada foi estimado. Totais informados no relatório final. Não há status line ao vivo nem OTel conectados (sem alteração de ~/.claude). Limites de conta: n/d.
