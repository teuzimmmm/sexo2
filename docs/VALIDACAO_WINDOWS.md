# Validação no Windows

Testes que só podem ser feitos na sua instalação, com o LoL. Os automáticos passam no CI, mas usam
cliente e dados simulados.

## Executável de teste

O CI gera a build sem assinatura `SEXO2-teste-<commit>` (aba Actions, run da `sexoatividade`,
seção Artifacts). Feche o SEXO2 instalado, extraia a pasta e rode `SEXO2.exe`. Na primeira abertura, a pasta
`%LOCALAPPDATA%\Rose` é movida para `%LOCALAPPDATA%\SEXO2` (com o cliente do LoL fechado), com
preferências e mods. Ela não se
atualiza sozinha para a 1.6.4.

Na branch `galinacio`, o mesmo executável fica em Actions > run da branch > Artifacts,
sem publicar uma release. Para validar a correção dos menus, feche o LoL e o SEXO2 antigo,
abra a nova build e depois o LoL. Confira o menu; feche/reabra só o SEXO2 e confira de novo,
inclusive durante a seleção de uma partida personalizada. O cliente não deve ser reiniciado
durante a seleção nem durante a partida. Fechar o SEXO2 com o LoL aberto conserva a ativação
do Pengu e o registro de recuperação; na próxima abertura, o SEXO2 adota essa ativação ou
a limpa se o LoL já estiver fechado.

## Roteiro

1. **Abertura:** o painel SEXO2 (Skins, Mods, Sala, Configurações, Diagnóstico) abre no cliente, e a bandeja e o painel mostram a versão 1.6.4 e o nome
   SEXO2 (nada de "Rose" visível).
2. **Injeção:** uma partida normal com skin escolhida; a skin aparece no jogo.
3. **Sala:** criar, entrar por link e reconectar, com um amigo.
4. **Mods:** listar, aplicar, renomear e excluir; exportar a biblioteca.
5. **Assistente e runas:** na seleção, o botão SEXO2 abre o assistente acima dele (Runas, Itens, Mods).
   Clique num card de runas: a página "SEXO2" é criada ou atualizada no cliente, e o rodapé mostra
   "Aplicada". Edite runas na árvore e confira que a página do cliente acompanha. A aba Mods abre o
   painel de mods de sempre. Contratos a confirmar nessa hora:
   - formato de `/lol-perks/v1/pages`, `currentpage`, `inventory` e `styles`;
   - que "página livre" significa páginas editáveis menores que `ownedPageCount`;
   - que a página criada com `current: true` fica ativa e é lida de volta igual;
   - os slugs de campeões com nome especial no LoLalytics (Wukong, Nunu, Renata).
6. **Conjuntos de itens (automático):** confirme o campeão numa partida personalizada ou normal
   (e depois em ARAM e Swiftplay), sem abrir o assistente. Na loja da partida, confira:
   - uma única página "SEXO2 — {Campeão}", com as seções na ordem aprovada (D-018);
   - que ela aparece também em ARAM e Swiftplay (o conjunto é salvo para todos os mapas);
   - que os seus conjuntos pessoais continuam intactos, e que nenhuma página nova aparece a cada
     campeão;
   - trocando de campeão na seleção, que a página passa a ser a do novo campeão.
   O log mostra `[ASSISTANT]` com o resultado. Uma resposta HTTP de sucesso não prova que a loja exibe
   a página: só a conferência visual vale.
7. **Posição do painel:** na seleção, abra o painel do botão SEXO2 e rode no console do cliente
   (DevTools do Pengu) `window.__sexo2AnchorDiagnostics()`. O resultado mostra se os seletores
   `.champion-select` e `.bottom-right-buttons` existem, os retângulos do botão e do painel e a posição
   esperada. Copie a saída se a borda direita não estiver alinhada ao botão ou se o painel sair da
   janela. Repita depois de mudar a escala do cliente.
8. **Aprimoramentos (Arena e ARAM Mayhem):** acrescente em `config.ini`:
   ```
   [Overlay]
   augments_enabled = true
   ```
   Jogue em **sem bordas**. A cada oferta, confira se o nome lido abaixo de cada carta é o da carta;
   anote as erradas e "Não reconhecida", e a resolução e a escala do HUD. Confirme também que o
   cliente responde `/lol-game-data/assets/v1/cherry-augments.json` e `augment-lists.json` (o log
   mostra quantos aprimoramentos e ícones foram carregados) e as filas 1700 (Arena) e 2400 (Mayhem).
9. **Valor dos itens no placar:** acrescente em `%LOCALAPPDATA%\SEXO2\config.ini`:
   ```
   [Overlay]
   gold_enabled = true
   ```
   Jogue com o jogo em **sem bordas** e segure Tab. Confira:
   - se os números ficam alinhados às linhas do placar (ajuste com `gold_rows_top` e
     `gold_row_step`, frações da altura da tela);
   - se a ordem das linhas corresponde à do placar;
   - se o modo tela cheia também mostra o overlay.
   As coordenadas padrão foram calibradas com uma captura real em 1920×1080:
   primeira linha em y=346, passo de 76,5 px e totais em y=234. Outras escalas de
   HUD e resoluções ainda precisam de conferência. Compare também os FPS com o
   overlay desligado/ligado, segurando Tab por alguns segundos em cada caso.
   A janela foi limitada à coluna central e as leituras idênticas não redesenham
   o conteúdo; isso não substitui a medição de FPS em partida.
   A conexão local agora é reaproveitada e o nome do jogador só é consultado uma vez
   por partida. Confira também soltar Tab durante uma leitura, alternar para outra
   janela segurando Tab, retornar ao jogo e iniciar outra partida: não deve aparecer
   uma leitura atrasada nem reaproveitar a identidade anterior. O mostrar/ocultar
   sem `deiconify` foi conferido com Tk real em um desktop separado; o efeito na
   composição do LoL ainda depende dessa comparação de FPS no jogo.
10. **Linha de base de desempenho:** `docs/MEDICAO.md`, cenários 1, 2, 3 e 5.
