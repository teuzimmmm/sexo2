# Roadmap por marcos

Cada marco só é **verificado** com o CI Windows verde. "Pendente de validação real" significa que falta
conferir no cliente LoL ou na instalação do usuário. As decisões citadas (D-xxx) estão em
`docs/produto/decisoes.md`.

| Marco | Escopo | Depende de | Estado |
|---|---|---|---|
| M0 | CI com todas as suítes, inventário de comportamentos, amostrador de desempenho | — | verificado; linha de base pendente (usuário) |
| M1 | Remover telemetria; `Host` na ponte; config.ini em ANSI ao salvar a sala | M0 | verificado; validação real pendente |
| M2 | Versão única (`sexo2/version.py`) no painel, diagnóstico, User-Agent e instalador | M0 | verificado; validação real pendente |
| M3 | Formatação (ruff, AST verificada) e remoção de scripts obsoletos | M0 | verificado (parcial: ver abaixo) |
| M4 | `CLAUDE.md`, skill `sexo2-ui`, registro de decisões, tokens, fontes, protótipo tipográfico | M0 | verificado; D-101 a D-103 pendentes |
| M5 | Rebrand dos textos visíveis | M2, M4, D-107 | bloqueado em D-107 |
| M6a | Mensagens do assistente na ponte, push do estado da seleção, adaptador LoLalytics | M0 | pronto para iniciar |
| M6b | Ticker de 1 kHz, filtro de eventos do LCU, polling JS, inbox, cliente WS único | linha de base (D-108) | bloqueado em medição |
| M7 | Assistente, fase leitura | M4, M6a, D-104, D-105, D-101–103 | bloqueado em decisões |
| M8 | Importação de runas | M7, D-106 | — |
| M9 | Conjuntos de itens | M8 | — |
| M10 | Inferência de rotas e matchup | M9 | — |
| M11 | Overlay: experimento ADR-5 e ouro | M0, Practice Tool | bloqueado em validação real |
| M12 | Aprimoramentos (Arena e Mayhem) | M11 | — |
| M13 | Identificadores e caminhos (`Rose` → `SEXO2`) com migração | M5 | — |

## Pendências técnicas registradas

- **Remoção de código morto ainda não feita**, por risco ou uso parcial:
  - `launcher/update/*` (no bundle, desativado por `FORK_BUILD`);
  - `party` STUN/UDP (exportado em `__init__`);
  - plugin `ROSE-PartyMode` (tem teste e rotas no backend);
  - `Rose.spec` (usado por `scripts/build_pyinstaller.py` e por um teste);
  - ramo `mayhem` em `lolalytics/item_pages.py`.
- **Respostas da ponte direcionadas ao solicitante:** depende de teste de contrato por mensagem (M6a).
- **Executável de teste no CI:** `SEXO2.spec` empacota binários que não estão no repositório (Pengu Loader, mod-tools, cloudflared, hashes). Eles são recuperados de uma instalação anterior por `scripts/prepare_release.py`, o que exige infraestrutura nova no CI.
- **Lint ampliado:** 247 avisos (`F401`, `F541`, `F841`) seguem como relatório informativo.
