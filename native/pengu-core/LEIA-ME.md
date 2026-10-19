# Pengu core do SEXO2

`core.dll` = Pengu Loader v1.1.6 (commit `4d641f52bc5d70aac4c09dfa1fa7a043a9069aff`) + `0001-sexo2-config-ini-path.patch`.

## O que o patch muda
- `config.ini` vem de `SEXO2_CONFIG_PATH`, depois `ROSE_CONFIG_PATH`, depois `%LOCALAPPDATA%\Rose\config.ini` (instalações antigas).
- Só injeta se `[General] disabled=0`. `loaderpath`, se preenchido, é a pasta do loader (config, plugins, datastore).
- Fora isso, é o upstream. Não replica a auto-remoção nem os logs do core antigo (sem fonte).

## Como reproduzir
Rode o workflow `Build Pengu core` (`.github/workflows/pengu-core.yml`): windows-latest, MSBuild/MSVC do runner, Release x64,
Node 22 + pnpm 9 para o `preload.g.h`. Versões reais: `build-info.txt` no artefato. Localmente: clone o upstream no commit acima,
`git submodule update --init core/cef`, `git apply` o patch, `pnpm install && pnpm build` em `plugins/`,
`msbuild core/core.vcxproj /p:Configuration=Release /p:Platform=x64`.

## Integração
`core.lock.json` fixa a execução (`run_id`/artefato) e o SHA-256 aceito. `scripts/restore_build_binaries.py --core <core.dll>`
recusa um hash diferente. Após mudar o patch: rode o workflow, atualize o `core.lock.json` e comite.
O artefato expira em 90 dias; regenere antes disso.

## Teste real no Windows (só isto confirma)
1. Instale a build de teste (artefato `SEXO2-teste-*` do release.yml, disparado manualmente). Não apague nem mova a pasta de dados atual.
2. Feche o cliente e o SEXO2. Copie a pasta de dados para um nome novo (ex.: `%LOCALAPPDATA%\SEXO2-Dados`) como **cópia**, sem junção.
3. Garanta que `SEXO2_CONFIG_PATH` aponta para `...\SEXO2-Dados\config.ini` no ambiente de quem lança o cliente
   (o Riot Client não herda a variável do SEXO2: ver risco no relatório) e que o IFEO aponta para o novo `core.dll`.
4. Process Monitor: filtros `Path contains config.ini` e `Path contains core.dll`, `Process Name is LeagueClientUx.exe`.
5. Abra o cliente. Esperado: `LeagueClientUx.exe` lê `...\SEXO2-Dados\config.ini` e **nunca** `...\Rose\config.ini`; os plugins carregam.
6. Repita sem a variável: deve cair em `\Rose\config.ini` (compatibilidade).
