# M5b: Rose para SEXO2

Estado: feito com migração onde havia caminho seguro; o resto fica como está, com o motivo. CI Windows é o critério; validação real no Windows pendente.

## Feito (cada item lê o formato antigo; testes em `tests/test_legacy_names.py` e `tests/test_plugin_rename.py`)
- Mutex `Local\SEXO2SingleInstance`: o app toma também `Local\RoseSingleInstance`, então versão nova e antiga não rodam juntas. `AppMutex` do instalador lista os dois.
- Tarefa agendada `SEXO2`: a `Rose` conta como registrada, é trocada ao registrar e apagada ao desregistrar.
- Arquivos: `sexo2_*.log` (limpeza cobre `rose_*.log`), `sexo2_runoverlay_*.log`, `sexo2_diagnostics.txt` (movido de `rose_diagnostics.txt` sem sobrescrever), `sexo2.lock`.
- Plugins `ROSE-*` para `SEXO2-*`: o Pengu guarda o estado na pasta (`index.js` / `index.js_`), e o app já o gerencia. A pasta antiga do runtime é renomeada antes da sincronização, levando o estado; sobra é descartada herdando o desabilitado; o bundle ignora pastas antigas e o instalador as apaga. Plugins do usuário não são tocados.
- Globais, eventos, ids/classes CSS, atributos e chaves de cache dos plugins, em todos os plugins e testes `.cjs`. `menu_item_Golden Rose` virou `menu_item_SEXO2`; `golden_rose.png` virou `hub_icon.png`.
- Códigos de grupo e links: leitura aceita `SEXO2:` e `#sexo2=` além dos antigos.
- `SEXO2_RELAY_URL` e `SEXO2_CONFIG_PATH` (os antigos continuam lidos/definidos; o loader já compilado lê `ROSE_CONFIG_PATH`).
- Arquivo de sessão do Pengu com chaves novas, lendo as antigas (queda com versão antiga).
- Valores internos do relay próprio, loggers, classes de janela, `Rose.spec` removido, scripts de build, frase de locale (21 idiomas), comentários.

## Mantido de propósito
- **Crédito legal:** `LICENSE` (MIT, Alban e Florent), README "baseado em Rose", `AppPublisher`, "Créditos da base" nas configurações, `LegalCopyright` do executável, `LICENSE-Rose.txt` no pacote, `@author`/`@link` dos plugins. Obrigação da licença.
- **Pasta `%LOCALAPPDATA%\Rose`:** o `core.dll` do Pengu (binário sem fonte no repositório) lê o `config.ini` de um caminho que não dá para verificar aqui; o hook IFEO aponta para o `core.dll` dentro dela (mover após uma queda deixa o cliente apontando para DLL ausente); o nome `SEXO2` colide com a pasta de instalação padrão `%LOCALAPPDATA%\SEXO2`. Sem teste no Windows real. Caminho futuro: nome distinto (ex.: `SEXO2-Dados`) com junção `Rose`, validado no cliente.
- **Metadados `rose_mod_targets.json`, `rose_category_mods.json`:** estão na pasta dos mods, entram em exportações e fora do hash da sala. Versões antigas dos amigos os esperam.
- **Escrita de `ROSE:` e `#rose=`:** versões distribuídas só removem o prefixo `ROSE:`; `SEXO2:` seria recusado. Trocar a escrita exige todos os amigos na versão nova.
- **Protocolo `v=1.4.7`** da sala: herdado. O relay padrão agora é o Worker próprio (`sala/`, D-133).
- **Executáveis antigos:** `Rose.exe`/`Rose Sala.exe` em instalador, atualizador e `sexo2/update/lifecycle.py`; atalhos antigos no `InstallDelete`.
- **Plugin `SEXO2-Jade` (terceiros, desabilitado):** pasta e caminhos renomeados; chaves `Rose-language`/`Rose-plugin-settings` do DataStore, classes `Rose-*` e `ROSEJadeLog` mantidos (config do usuário, sem como testar). `assets/logo.png` mantido (não geramos imagens).
- `cslol-dll.stub` (binário pré-compilado) e `native/cslol_stub` (mensagem de erro); `launcher/update/github_client.py` (código morto, `FORK_BUILD`); vendor `Program.cs` links e `icon_rose.png` (créditos, binário não é recompilado no CI).
- Regex que troca "Rose" por "SEXO2" no texto do cliente (`SEXO2-UI`, `SEXO2-SettingsPanel`) e filtros dos links do upstream.
- Testes `.cjs` de navegador (`browser_*.cjs`) não rodam no CI nem aqui (sem Node/Playwright): renomeados por script e checados só quanto à sintaxe.
