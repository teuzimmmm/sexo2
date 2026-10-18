# Roadmap por marcos

Cada marco só é **verificado** com o CI Windows verde. "Pendente de validação real" significa que falta
conferir no cliente LoL ou na instalação do usuário. As decisões citadas (D-xxx) estão em
`docs/produto/decisoes.md`.

| Marco | Escopo | Depende de | Estado |
|---|---|---|---|
| M0 | CI com todas as suítes, inventário de comportamentos, amostrador de desempenho | — | verificado; linha de base pendente (usuário) |
| M1 | Remover telemetria; `Host` na ponte; config.ini em ANSI ao salvar a sala | M0 | verificado; validação real pendente |
| M2 | Versão única (`sexo2/version.py`) no painel, diagnóstico, User-Agent e instalador | M0 | verificado; validação real pendente |
| M3 | Formatação (ruff, AST verificada), remoção de scripts obsoletos, tracebacks preservados em injeção e monitor | M0 | verificado; remoção parcial (ver abaixo) |
| M4 | `CLAUDE.md`, skill `sexo2-ui`, registro de decisões, tokens, fontes, protótipo tipográfico | M0 | verificado; D-101 a D-103 pendentes |
| M5 | Rebrand dos textos visíveis | M2, M4, D-107 | nome trocado nos textos (ver abaixo, `test_no_visible_rose`); validação real pendente; demais textos aguardam D-107 |
| M6 | Infraestrutura funcional: tabela de despacho; LCU de runas e conjuntos; validação pelas regras do cliente; controlador de importação; adaptador LoLalytics; serviço do assistente com mensagens `assistant-*` na ponte | M0 | verificado por testes com cliente simulado; validação real pendente (contratos do LCU listados em `docs/VALIDACAO_WINDOWS.md`) |
| M13 (antigo M6b) | Desempenho: ticker de 1 kHz, filtro de eventos do LCU, polling JS, inbox, cliente WS único | linha de base (D-108), depois da 1.0 | adiado |
| M7 | Assistente na seleção (interface Pengu) | protótipo aprovado (D-101 a D-105) | protótipo pronto em `design/propostas/sexo2-v1`; interface real aguarda aprovação |
| M8 | Importação de runas | M6 | serviço pronto; falta a interface (M7) e a validação no cliente |
| M9 | Conjuntos de itens | M6 | serviço pronto; falta a interface (M7) e a validação no cliente |
| M10 | Inferência de rotas e matchup | M9 | — |
| M11 | Overlay de valor dos itens | M0 | janela pronta, desligada por padrão; calibração das linhas e teste em partida pendentes |
| M12 | Aprimoramentos (Arena e Mayhem) | M11 | — |
| M5b (antigo M13) | Identificadores e caminhos (`Rose` → `SEXO2`) com migração | M5, validação no Windows | pendente; arriscado |

## M5: nacionalização dos textos

Só a marca mudou: "Rose" passou a "SEXO2" no texto, sem reescrever mensagens (o restante da
linguagem continua em D-107).

- **Python:** diálogos nativos (patcher LTK, instância única, administrador, início com o Windows,
  configurações da bandeja, atualização, erro fatal), dicas de diagnóstico da injeção, mensagens da
  sala, título do seletor de mods, faixa de início do log. O diagnóstico agora sai como
  `SEXO2-diagnostico-*.zip`.
- **Plugins:** textos do painel de configurações e da sala; as chaves em inglês e os 21 arquivos de
  `SEXO2-I18n/locales` mudaram juntos, para os textos manterem a tradução.
- **Links do Rose:** Discord, Ko-fi e GitHub saíram do painel de configurações e do diálogo do
  patcher. O crédito fica em "Créditos da base" (`SEXO2-Settings`) e no `LICENSE`.
- **Instalador:** pede para fechar o SEXO2 (a verificação continua cobrindo `Rose.exe` e
  `Rose Sala.exe`).
- **Ativos:** `assets/rose_without_bg.png` removido (sem referência). `golden_rose.png` fica: é a
  máscara do ícone do Hub.

Mantidos de propósito (compatibilidade ou crédito; lista viva em `tests/test_no_visible_rose.py`):

- pasta de dados `%LOCALAPPDATA%\Rose` e os nomes de arquivo dentro dela (`rose_*.log`,
  `sexo2_runoverlay_*.log`, `rose_diagnostics.txt`, `rose.lock`, metadados `rose_*.json` dos mods);
- mutex `Local\RoseSingleInstance` e `AppMutex` do instalador; tarefa agendada `Rose`; chave de
  desinstalação `Uninstall\Rose`;
- `Rose.exe` e `Rose Sala.exe` nas listas do atualizador e do instalador;
- pastas `ROSE-*` dos plugins e os nomes nos cabeçalhos (`@name`, `@author Rose Team`);
- globais e eventos entre plugins (`__roseBridge`, `__roseHub`, `RoseI18n`, `rose-open-settings`,
  `rose-hub-*`, ids e classes CSS `rose-*`, classe `menu_item_Golden Rose`);
- fragmento `#rose=` dos links de sala, prefixo `ROSE:` dos códigos de grupo, valores do protocolo
  do relay (`rose-host-readiness`, `rose-friends-relay`), `ROSE_RELAY_URL`;
- `Rose.spec` (usado por `scripts/build_pyinstaller.py` e por teste) e os scripts de build;
- `AppPublisher` do instalador ("baseado em Rose") e o texto de créditos;
- plugin desativado `SEXO2-Jade` (`index.js_`, não carrega).

**Migrações arriscadas** (M13, exigem validação real no Windows e teste do formato antigo):
renomear a pasta de dados, o mutex (instalador e app juntos), a tarefa agendada, as pastas `ROSE-*`
(o Pengu guarda o estado ativado pelo nome da pasta) e os globais compartilhados entre plugins.

## Pendências técnicas registradas

- **Remoção de código morto ainda não feita**, por risco ou uso parcial:
  - `launcher/update/*` (no bundle, desativado por `FORK_BUILD`);
  - `party` STUN/UDP (exportado em `__init__`);
  - plugin `SEXO2-PartyMode` (tem teste e rotas no backend);
  - `Rose.spec` (usado por `scripts/build_pyinstaller.py` e por um teste);
  - ramo `mayhem` em `lolalytics/item_pages.py`.
- **Respostas da ponte direcionadas ao solicitante:** depende de teste de contrato por mensagem (M6a).
- **Executável de teste no CI:** `SEXO2.spec` empacota binários que não estão no repositório (Pengu Loader, mod-tools, cloudflared, hashes). Eles são recuperados de uma instalação anterior por `scripts/prepare_release.py`, o que exige infraestrutura nova no CI.
- **User-Agent do `lolalytics/`:** hoje usa o padrão do `requests`. Trocar exige validação ao vivo, porque o site pode tratar outro User-Agent de forma diferente.
- **Lint ampliado:** 247 avisos (`F401`, `F541`, `F841`) seguem como relatório informativo.
