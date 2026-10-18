# Medição de desempenho

Protocolo da linha de base (M0), reutilizado antes e depois de cada mudança de desempenho.

## Como gravar

Abra um terminal **como administrador**. Sem isso, a memória exclusiva (USS) do SEXO2,
que roda elevado, fica vazia. Use o Python do projeto e rode:

```
python scripts/perf_sample.py record --seconds 600 --out lobby-1.csv
```

Repita cada cenário 3 vezes (`-1`, `-2`, `-3`), com o mesmo estado inicial. Depois:

```
python scripts/perf_sample.py summary lobby-1.csv lobby-2.csv lobby-3.csv
```

O resumo traz média e p95 por grupo (`sexo2`, `client`, `game`). Traz também a variação
entre as repetições: esse é o ruído. Uma mudança só conta como melhora ou piora quando a
diferença supera esse ruído.

## Cenários da linha de base

| # | Cenário | Duração | Observação |
|---|---|---|---|
| 1 | Cliente aberto no lobby, sem fila | 600 s | não mexer no cliente |
| 2 | Seleção de campeões completa (personalizada) | do início ao carregamento | anotar o horário em que o campeão foi travado |
| 3 | Igual ao 1, com os plugins Pengu desativados | 600 s | isola o custo dos plugins no grupo `client` |
| 5 | Inicialização: abrir o SEXO2 com o cliente aberto | 120 s | anotar fria (após reiniciar o PC) ou quente |

Os cenários 4 (Practice Tool com PresentMon) e 6 (tempo de jogo suspenso na injeção)
dependem de autorização própria e ficam para os marcos M6b e M11.
