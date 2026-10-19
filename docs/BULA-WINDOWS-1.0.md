# BULA — agente noturno no Windows: terminar o SEXO2 até a 1.0 (sem decisões de produto)

Cole este documento no Claude Code (Sonnet) que roda no Windows. Branch oficial: `amolula`. Tudo abaixo vale para você e para os agentes que você disparar.

## 0. Contexto em 6 linhas
SEXO2 é um app Python + plugins Pengu para o client do League of Legends. Só duas pessoas o usam (o dono e um amigo): **não existe base de usuários a migrar**. Fase 0.9 pre-launch concluída na `amolula`. A DLL nova (`core.dll`) já foi refeita pelo dono: **não a recompile e não a edite**. Leia primeiro: `CLAUDE.md`, `docs/BRANCH-OFICIAL.md`, `docs/ROADMAP.md`, `docs/PROGRESSO-INTEGRACAO.md`, `docs/produto/decisoes.md`, `docs/comportamentos.md`, `docs/VALIDACAO_WINDOWS.md`.

## 1. Arquitetura de execução (controlador + trabalhadores)
- **Pasta de trabalho única:** `Z:/mathe/Onedrive/Documents/sexo2-overnight` (clone da `amolula` dentro dela). Nada de escrever fora dela. Estado do controlador, logs e relatórios ficam em `…/sexo2-overnight/_controle/`.
- **Você (Claude Code, Sonnet) = controlador e revisor.** Em cada ciclo: escolhe a próxima tarefa de `_controle/TAREFAS.md`, escreve um arquivo de tarefa curto (§4), dispara um trabalhador, confere o resultado com o comando de aceite e decide.
- **Troca de modelo por cota:** enquanto a cota da conta tiver mais de 30% restante, você (Sonnet) implementa direto. Quando restar ≤ 30%, **pare de implementar**, guarde a cota para controlar, e delegue a implementação a agentes do `opencode` com o modelo DeepSeek disponível (descubra o nome exato com `opencode models`; o dono disse "DeepSeek 4.1" e isso NÃO foi verificado — use o que existir e registre o nome).
- **Como medir a cota (não adivinhe):** o dado vem do JSON da status line do Claude Code (`rate_limits`). Capture um payload real uma vez para ver os campos, depois escreva `_controle/cota.py` (stdlib) que lê o último snapshot e devolve "restante %". Se o campo não existir neste ambiente, assuma o pior: delegue ao opencode tudo o que for mecânico e use Sonnet só para revisar, e registre isso em `_controle/RELATORIO-NOTURNO.md`.
- **Recursão limitada:** profundidade máxima 2 (controlador → trabalhador; trabalhador não dispara trabalhadores). Máx. 3 trabalhadores simultâneos, de preferência 1.
- **Segurança do opencode:** configure `opencode.json` com as regras de permissão da documentação instalada (não invente sintaxe) restringindo escrita/execução à pasta acima e negando comandos destrutivos fora dela. Isso não é barreira real; a barreira real é o dono rodar o opencode sob um usuário do Windows com ACL só nessa pasta. Se o ambiente não estiver assim, avise no relatório e **não rode o opencode fora da pasta**.

## 2. Limites duros (kill switch)
- Arquivo `_controle/STOP`: se existir, termine o ciclo atual e pare.
- Máx. 8 horas, 40 ciclos e 3 ciclos seguidos sem progresso verificável (teste ou CI que passou). Ao bater qualquer um, escreva `_controle/BLOQUEIO.md` (causa objetiva) e pare. Não aumente gasto, créditos nem limites; não "tente de novo para sempre".
- Cada tarefa tem teto de 20 turnos e uma rodada de correção.

## 3. Regras de repositório
- Trabalhe numa branch `noturno/AAAA-MM-DD` criada a partir da `amolula`. Commits pequenos, por finalidade, rodapé `Co-Authored-By: …` do agente que escreveu. **Push só dessa branch.** Nunca `main`, `amolula`, `sexoatividade`, force push, release, tag, PR (o dono revisa de manhã).
- O **CI Windows** (`Validate SEXO2`) é o juiz: ruff check/format, `scripts/run_tests.py -q` (agora no Windows, sem as 7 falhas "só-Windows" de antes: se alguma falhar de verdade, é trabalho), `build_tokens --check`, `node --test`. Uma tarefa só conta como feita com o CI verde (`gh run watch`, bloqueante, sem polling). Teste instável conhecido: `test_startup_resumes_a_game_a_dead_rose_left_suspended` → repita o job.
- Preserve o crédito legal ao Rose/Pengu/LTK (LICENSE, README "baseado em Rose", instalador, créditos). Preservar comportamentos protegidos (`docs/comportamentos.md`) com o teste correspondente.

## 4. Formato de tarefa para trabalhador
Arquivo `_controle/tarefas/NNN.md`: objetivo em 1 frase; arquivos que pode tocar; arquivos proibidos; comando de aceite (um teste ou comando que prova); o que fazer se falhar (parar e relatar). O trabalhador devolve só: feito/não feito, saída do comando de aceite, lista de arquivos alterados.

## 5. Tarefas (nesta ordem) — todas sem decisão de produto
1. **Auditoria de linha de base:** rode toda a suíte no Windows e o ruff; liste falhas reais em `_controle/BASE.md`.
2. **Expurgar `%LOCALAPPDATA%\Rose`:** o app não pode criar nem ler essa pasta. Descubra no código-fonte da DLL nova (no checkout do dono; leia, não recompile) qual caminho de dados/config ela usa e alinhe o app a esse caminho. Como só há 2 usuários, **remova a camada de compatibilidade da M5b** (mutex antigo `Local\RoseSingleInstance`, tarefa agendada `Rose`, chave `Uninstall\Rose`, `Rose.exe`/`Rose Sala.exe` das listas, leitura de pastas de plugin `ROSE-*`, formatos `ROSE:`/`#rose=`) e os arquivos `rose_*`. Nada de migração. Atualize `tests/test_no_visible_rose.py`, docs e decisões (D-122 → "decidido: sem compatibilidade com Rose"). **Se o caminho que a DLL usa não puder ser determinado, pare esta tarefa e registre o bloqueio (não invente caminho).**
3. **Instalador (`installer-sexo2.iss` + scripts):** refaça para funcionar direito e para **desinstalar absolutamente tudo** do SEXO2 e do Rose: arquivos, pastas de dados (`%LOCALAPPDATA%\SEXO2`, `%LOCALAPPDATA%\Rose`, `%APPDATA%` equivalentes), chaves de registro (incl. hook IFEO do loader, chave de desinstalação, Run), tarefa agendada, plugins copiados ao cliente, atalhos. Gere o instalador em máquina Windows (Inno Setup), instale em limpo, rode, desinstale e **verifique por script** que não sobrou nada (arquivos, registro, tarefas, pastas) e que uma instalação nova **não cria nenhuma pasta Rose**. Registre o resultado em `docs/VALIDACAO_WINDOWS.md`.
4. **Teste cirúrgico no cliente (SÓ abrir o client; NUNCA entrar em fila, lobby de partida ou jogo):** com o app instalado, abra o client do LoL e verifique, com logs e capturas de tela salvas em `_controle/evidencias/`: (a) a abertura animada toca no carregamento; (b) o ícone novo no exe, atalho, bandeja e item de menu; (c) o painel SEXO2 abre em Sala, menus Sala/Favoritas/Configurações/Suporte, cantos retos; (d) Favoritas: busca por campeão e por skin, cromas; (e) o app reinicia o client quando aberto com o client já rodando. Feche o client ao final. Não toque em login/conta. Qualquer erro no log do app é uma tarefa de correção.
5. **Auditoria final do código:** resíduos de "Rose" não exigidos por licença, código morto (ex.: abas/funções órfãs como `prefsTab` no assistente, `launcher/update/github_client.py`), segredos, TODOs, caminhos absolutos, dependências não usadas, testes frágeis. Corrija o que for seguro; o resto vai para `_controle/AUDITORIA.md`.
6. **Resto até a 1.0 que NÃO requer decisão:** use `docs/ROADMAP.md` (marco v1.0) e `docs/PROGRESSO-INTEGRACAO.md`. Só faça o que for correção, teste, documentação, desempenho com medição ou limpeza. Se exigir decisão (ver §6), **não faça**: liste em `_controle/DECISOES-PENDENTES.md`.

## 6. Proibido sem o dono (decisões de produto)
Nomes, menus, textos visíveis novos, layout, cores, ícones/marca, novos componentes, automatismos novos, qualquer mudança de UX; a reformulação das salas (sala automática/pareamento por chave, Cloudflare/relay: o dono está criando a conta e vai especificar); versão (bump/1.0/release assinado); recompilar a DLL; `main`; configurações do GitHub; tocar em contas, login ou jogo. Onetricks foi removido; Galo e BORK foram removidos (D-112): não reintroduza.

## 7. Entrega
Ao terminar ou parar: `_controle/RELATORIO-NOTURNO.md` (≤60 linhas): tarefas feitas/bloqueadas com o link do run do CI, commits, modelos realmente usados e consumo (n/d se não medido), o que NÃO foi validado e riscos; mais `_controle/DECISOES-PENDENTES.md`. Não declare sucesso por atingir o teto.
