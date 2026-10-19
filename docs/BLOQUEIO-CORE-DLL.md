# Bloqueio: recompilar o core.dll do Pengu Loader (pasta de dados renomeável)

Estado: **parado na etapa 2**. Nenhum código foi escrito e nenhum binário foi alterado.

## Verificado
- **Upstream** (PenguLoader v1.1.6, commit `4d641f52bc5d70aac4c09dfa1fa7a043a9069aff`): o `core` não lê `config.ini`
  nem `Rose`. Ele lê o arquivo `config` (sem extensão) ao lado do `core.dll`
  (`core/src/config.cc`, `get_config_map`, usando `config::loader_dir()`). A única variável de
  ambiente usada é `LOCALAPPDATA` para o cache do CEF (`config.cc:69`).
- **core.dll instalado no PC de desenvolvimento** (leitura apenas; origem exata não confirmada como a baseline v1.6.4):
  - `%LOCALAPPDATA%\Rose\Pengu Loader\core.dll`: 505464 bytes, SHA-256
    `280c894f800d4c00ae2363ccf2f55e63456cd6de67341aa7b2709c737487679a`.
  - `%LOCALAPPDATA%\SEXO2\Pengu Loader\core.dll`: 495104 bytes, SHA-256
    `3985768acc48510b6e6140681e62cf8ffd9acf4b61c3f1ca64839778d0b5104c`.
  - Ambos têm o caminho **fixo**: `LOCALAPPDATA` + `\Rose` (ou `\SEXO2` no segundo) e a string
    `\Rose\config.ini` (`\SEXO2\config.ini`), lido por `GetPrivateProfileStringW` (chaves `General/loaderpath`
    e `disabled`), com logs, auto-remoção ("self-delete") e versão "Rose Loader core module". Caminho de PDB:
    `C:\Users\Alban\Desktop\ROSE-Pengu\PenguLoader-1.1.6\bin\core.pdb`.
  - O segundo parece o primeiro com as strings trocadas por patch binário (mesma estrutura, `\Rose`→`\SEXO2`).
    Isso explica o Process Monitor ter visto `%LOCALAPPDATA%\SEXO2\config.ini`: o caminho é fixo e
    depende do binário, não da pasta real do app.
- Conclusão: o core da baseline **não é** o upstream. Tem mudanças de fork (leitura de `config.ini`,
  `loaderpath`/`disabled`, auto-remoção, logs) **sem fonte** no repositório nem no upstream.
- A release `v1.6.4` / `SEXO2-baseline.zip` não é acessível sem autenticação (404 anônimo; o `gh` não está
  instalado neste PC), então o hash do core exato da baseline não foi comparado.

## Por que parei
A tarefa proíbe inventar código para reproduzir mudanças sem fonte. Recompilar a partir do upstream geraria um core
que **não** lê `config.ini`, quebrando a ativação feita por `Sexo2Config.cs`, ou exigiria reescrever esse
comportamento do zero.

## Opções para decidir
1. Obter o fonte do fork "ROSE-Pengu" (autor do PDB, "Alban"; base: projeto Rose). Com ele, a mudança é
   mínima: ler `SEXO2_CONFIG_PATH`, depois `ROSE_CONFIG_PATH`, depois o caminho antigo.
2. Reescrever no upstream um patch próprio (novo comportamento, não reprodução). Exige aprovação e validação no
   Windows real; sem garantia de compatibilidade com o core antigo.
3. Patch binário das strings. Frágil (tamanho fixo; um nome distinto e mais longo que `\Rose` não cabe sem
   realocar) e não é recompilação. Não recomendado.

## Licença (a cumprir em qualquer redistribuição de core recompilado)
O Pengu Loader é GPL-3.0 (`vendor/PenguLoader-1.1.6/LICENSE`): manter avisos e créditos upstream, incluir o texto
da licença, indicar as modificações e oferecer o fonte correspondente da versão modificada a quem receber o
binário. Hoje o core distribuído já é uma versão modificada **sem fonte publicada**, o que precisa ser
resolvido de qualquer forma. Esta nota não é parecer jurídico.

## Atualização: busca do fonte do fork
- `github.com/Alban1911/Rose` (HEAD `146f798`, histórico completo, 1531 commits): só traz o `core.dll` pronto
  (`Pengu Loader/core.dll`, SHA-256 `280c894f…7679a`, **idêntico** ao `Rose\Pengu Loader\core.dll` local). Nenhum
  `.cc/.cpp/.vcxproj` jamais foi commitado; `vendor/PenguLoader-1.1.6` tem só o loader C#.
- Demais repositórios de Alban1911 (`LeagueUnlocked`, `openfork`): sem fonte de core. `Watermelon` tem um core C++
  em `src-tauri/native`, mas sem `config.ini`/`\Rose`/`loaderpath` (outro produto, Tauri); não serve de base.
- Conclusão: **não há fonte público do core da baseline**. Recompilar exige (a) obter o fonte com o autor
  (Alban1911; o core também precisaria ser publicado por ele sob GPL-3.0), ou (b) um patch novo sobre o upstream
  v1.1.6, que é comportamento novo e precisa de aprovação.
