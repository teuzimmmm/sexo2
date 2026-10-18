# Validação no Windows

Testes que só podem ser feitos na sua instalação, com o LoL. Os automáticos passam no CI, mas usam
cliente e dados simulados.

## Executável de teste

O CI gera a build sem assinatura `SEXO2-teste-<commit>` (aba Actions, run da `sexoatividade`,
seção Artifacts). Feche o SEXO2 instalado, extraia a pasta e rode `SEXO2.exe`. A build usa os mesmos
dados em `%LOCALAPPDATA%\Rose`, então suas preferências e mods continuam valendo. Ela não se
atualiza sozinha para a 1.6.4.

## Roteiro

1. **Abertura:** o painel abre no cliente, e a bandeja e o painel mostram a versão 1.6.4 e o nome
   SEXO2 (nada de "Rose" visível).
2. **Injeção:** uma partida normal com skin escolhida; a skin aparece no jogo.
3. **Sala:** criar, entrar por link e reconectar, com um amigo.
4. **Mods:** listar, aplicar, renomear e excluir; exportar a biblioteca.
5. **Runas:** a interface ainda é o protótipo. O serviço já responde às mensagens `assistant-*` da
   ponte, mas só pode ser testado no cliente depois que a interface for aprovada e integrada.
   Contratos a confirmar nessa hora:
   - formato de `/lol-perks/v1/pages`, `currentpage`, `inventory` e `styles`;
   - que "página livre" significa páginas editáveis menores que `ownedPageCount`;
   - que a página criada com `current: true` fica ativa e é lida de volta igual;
   - os slugs de campeões com nome especial no LoLalytics (Wukong, Nunu, Renata).
6. **Conjuntos de itens:** os mesmos cuidados; conferir que os seus conjuntos pessoais continuam
   intactos depois da importação.
7. **Valor dos itens no placar:** acrescente em `%LOCALAPPDATA%\Rose\config.ini`:
   ```
   [Overlay]
   gold_enabled = true
   ```
   Jogue com o jogo em **sem bordas** e segure Tab. Confira:
   - se os números ficam alinhados às linhas do placar (ajuste com `gold_rows_top` e
     `gold_row_step`, frações da altura da tela);
   - se a ordem das linhas corresponde à do placar;
   - se o modo tela cheia também mostra o overlay.
8. **Linha de base de desempenho:** `docs/MEDICAO.md`, cenários 1, 2, 3 e 5.

9. **Upgrade a partir de uma instalação com nomes antigos (M5b):** `%LOCALAPPDATA%\Rose` preservada; plugins habilitados/desabilitados continuam como estavam (pastas `SEXO2-*`); tarefa agendada e instância única funcionam; sala com amigo em versão anterior (código `ROSE:`, link `#rose=`). Ver `docs/PROGRESSO-M5B.md`.
