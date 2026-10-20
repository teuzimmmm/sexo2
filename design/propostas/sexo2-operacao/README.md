# Painel local — três frentes

Abra `Abrir-painel.command` no Mac ou execute `python3 painel.py ver` na pasta deste arquivo. Requer Python 3.9 ou posterior. Fechar o painel não para os agentes. A tela confere os arquivos locais a cada segundo e redesenha somente linhas que mudaram; não chama modelos nem serviços.

Versão visual: blocos por frente, barras de progresso e estados em dourado, verde, âmbar ou vermelho; sem azul. A tela usa um espaço temporário do terminal e restaura o cursor e a tela anterior ao fechar com Ctrl+C. Em janelas pequenas, o layout fica compacto; aumente a janela para ver fontes, cache e evidências. Cores são automáticas no terminal; `--no-color` ou a variável `NO_COLOR` desativam as cores.

Para atualizar uma janela que já estava aberta, feche somente o painel com Ctrl+C e abra o mesmo lançador novamente. Isso não interrompe o Claude. Os comandos de status/coleta e os arquivos de estado continuam iguais.

Para uma prévia: `python3 painel.py ver --demo`. Os números desse modo são fictícios e ficam numa pasta temporária separada. Sem demo, o painel começa aguardando agentes; nenhum processo Claude foi iniciado por esta entrega.

Os três trabalhadores precisam enxergar a mesma pasta de estado. Nesta instalação, o lançador já aponta para `/Users/matheus/Documents/tremdolol/sexo2-lab/estado`, usada pelo laboratório Claude. O script, se chamado sem `--data`, usa `estado/` ao lado de painel.py. Para apontar outra pasta, usar `python3 painel.py --data /caminho/compartilhado ver`.

## Status de tarefa

Cada agente atualiza somente sua frente (`a`, `b` ou `overlays`) após progresso ou bloqueio real:

```sh
python3 painel.py --data /caminho/estado status a --state executando --task 'Revisando coleção' --done 2 --total 8 --model sonnet --evidence 'QA.md: A02 passou'
```

Estados: aguardando, executando, validando, bloqueado, parcial, concluido, falhou. `concluido` exige todos os critérios e evidência. Isso valida o registro; a qualidade da evidência continua dependendo dos testes.

## Dados de consumo

O coletor aceita snapshots oficiais de status line ou o evento final `result` do stream JSON do Claude Code. Não faz estimativas por caracteres. Sem fonte conectada, exibe n/d.

```sh
python3 painel.py --data /caminho/estado coletar controle --source statusline --input snapshot.json
python3 painel.py --data /caminho/estado coletar a --source result --input sessao-a.jsonl
```

Status line fornece contexto atual e custo estimado, não total histórico de tokens. O resultado de sessão pode fornecer tokens acumulados; sua cobertura pode incluir subagentes. Importações repetidas substituem o snapshot e não duplicam contagens. O painel não soma os custos das frentes com o controle, pois podem se sobrepor. Limites de conta aparecem só no controle quando fornecidos.

O coletor não instala hooks nem altera sua configuração. Para atualizações ao vivo, o Claude deve conectar o snapshot/evento real disponível no ambiente, conforme o prompt. Importar um arquivo estático é uma fotografia e mostra a idade da medição. Dados ausentes permanecem n/d.

Referências técnicas: [status line](https://code.claude.com/docs/en/statusline), [saída estruturada](https://code.claude.com/docs/en/headless), [custos e assinatura](https://code.claude.com/docs/en/costs).
