# Pasta de dados `%LOCALAPPDATA%\Rose`: roteiro para descobrir de onde o Pengu lê o config

Pendência do M5b (`docs/PROGRESSO-M5B.md` na branch `ux/v0.9-m5b-rename`). Não dá para renomear a pasta sem saber se o `core.dll` do Pengu (binário sem fonte no repositório) tem o caminho `\Rose` fixo ou lê o `config.ini` pela variável `ROSE_CONFIG_PATH`. Este roteiro responde isso. Só leitura: não altera nada no app nem no sistema. Sem symlink e sem junção.

## O que já se sabe (no código)
- `utils/integration/pengu_loader.py:43` define `ROSE_CONFIG_PATH` com o caminho do `config.ini` do app.
- O loader vendorizado (`vendor/PenguLoader-1.1.6/loader/Main/RoseConfig.cs`) lê `ROSE_CONFIG_PATH` e, se ausente, `%LOCALAPPDATA%\Rose\config.ini`.
- O que NÃO se sabe: se o `core.dll` (injetado no cliente LoL pelo hook IFEO) faz o mesmo ou usa `\Rose` fixo.

## Preparação (Windows)
1. Baixar o Process Monitor (Sysinternals, Microsoft) e abrir como administrador.
2. Fechar o app e o cliente do LoL. Ter uma instalação do SEXO2 que já funciona.

## Passos
1. No Process Monitor: Filter > Reset Filter. Adicionar os filtros (Include): `Path contains config.ini` e `Path contains Rose`. Desligar a captura (Ctrl+E) e limpar (Ctrl+X).
2. Ligar a captura (Ctrl+E). Abrir o SEXO2 e depois o cliente do LoL normalmente. Esperar o cliente carregar por completo.
3. Parar a captura. Anotar, para cada linha: **Process Name** (SEXO2.exe, LeagueClientUx.exe, Pengu...), **Operation** (CreateFile, ReadFile) e **Path** completo, e se o **Result** foi SUCCESS ou NAME NOT FOUND.
4. Se alguma linha de `LeagueClientUx.exe` (onde o `core.dll` roda) abre um `config.ini`, copiar o Path exato. Isso é o caminho que o `core.dll` usa.
5. Teste do caminho alternativo: fechar tudo, abrir um `cmd`, executar `set ROSE_CONFIG_PATH=C:\Temp\sexo2cfg` (criar a pasta antes, com uma cópia do `config.ini`) e iniciar o SEXO2 a partir dele. Repetir os passos 2 a 4 e ver se o `LeagueClientUx.exe` passou a abrir `C:\Temp\sexo2cfg\config.ini`.
   - Atenção: o app define a variável por conta própria (linha 43 acima), então este teste pode ser sobrescrito. Se o Path continuar sendo `%LOCALAPPDATA%\Rose`, anote isso também; é informação útil.

## Como interpretar
| Resultado | Conclusão | Próximo passo |
|---|---|---|
| `LeagueClientUx.exe` abre o `config.ini` no caminho de `ROSE_CONFIG_PATH` | O `core.dll` obedece à variável | Renomear a pasta de dados, apontando a variável para o novo local (com migração e teste do formato antigo) |
| `LeagueClientUx.exe` abre sempre `%LOCALAPPDATA%\Rose\config.ini` | Caminho fixo no binário | Manter `\Rose` (ou recompilar o `core.dll` do código do Pengu com o caminho novo) |
| Nenhuma linha de `LeagueClientUx.exe` abre `config.ini` | O `core.dll` não lê o arquivo; só o loader/SEXO2 | Pasta livre para renomear, mantendo o mutex e os `rose_*.json` por compatibilidade |

## O que devolver
Os prints (ou exportação CSV do Process Monitor, só das linhas filtradas) dos passos 3 a 5, e o resultado da tabela acima. Com isso decidimos a renomeação da pasta sem criar atalho de diretório.
