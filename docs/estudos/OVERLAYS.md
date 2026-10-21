# Estudo: como os apps fazem overlays no LoL (20/10/2026)

Pedido do usuário depois de duas tentativas sem sucesso no overlay de aprimoramentos e de uma
queda de FPS de cerca de 10× (de ~1000 para ~100) com os overlays ligados. Objetivo: entender
como Blitz, U.GG, Porofessor e Mobalytics fazem, medir o que derruba o FPS no SEXO2 e só então
decidir o caminho. Nada aqui foi implementado.

## O que já se sabe (fontes no fim)

1. **Os apps grandes não leem a tela para saber as cartas.** O Overwolf (plataforma de
   Porofessor, Mobalytics e outros) tem um provedor de eventos do jogo (GEP) com, na categoria
   `me`, `augments` (lista de aprimoramentos disponíveis na escolha) e `picked_augment` (o
   último escolhido), para Arena e ARAM Mayhem. O app recebe a oferta pronta; não há captura
   de tela nem OCR. Não confirmado se o Blitz usa o Overwolf.
2. **O Overwolf também é oferecido fora da plataforma** (`ow-electron`, um fork do Electron com
   GEP, overlay e gravação). O acesso aos eventos de cada jogo é liberado por pedido, o
   executável precisa de assinatura de código própria e o lançamento passa por revisão de
   conformidade. Não está claro se um app privado de duas pessoas seria aceito.
3. **Vanguard:** a Riot diz que overlays que usam as APIs oficiais (LCU e a API local do jogo)
   continuam funcionando; ler memória do jogo não funciona; não há lista de permissões.
   Janelas externas por cima do jogo são aceitas.
4. **Política da Riot:** proíbe mostrar win rate de aprimoramentos e itens da Arena em
   qualquer app ou overlay. O SEXO2 decidiu mostrar mesmo assim (A3, uso privado); o risco
   continua sendo da conta.
5. **Por que uma janela por cima derruba o FPS:** um jogo em tela cheia otimizada ou sem bordas
   apresenta em "independent flip". Qualquer janela externa por cima tira o jogo desse caminho
   e obriga o Windows (DWM) a compor cada quadro, o que custa muito com FPS alto e VSync
   desligado. Só não acontece quando a placa compõe a janela em um plano próprio (MPO).
   Capturar a tela com GDI (BitBlt, o que o `ImageGrab` faz) é o método mais caro; a
   duplicação de tela do DXGI é o mais barato.

## Hipóteses para a queda de FPS no SEXO2 (a confirmar por medição)

| # | Suspeito | Onde | Por quê |
|---|---|---|---|
| H1 | Captura de tela contínua | `augment_overlay.py`: `ImageGrab.grab` a cada 0,5–1 s durante toda a partida | BitBlt lê o quadro composto do DWM e força sincronização com a GPU |
| H2 | OCR do Windows e comparação de ícones | mesmo laço, sempre que há cartas | CPU no mesmo momento da escolha |
| H3 | Janela Tk transparente por cima | ouro e aprimoramentos | tira o jogo do independent flip enquanto está visível |
| H4 | Laço do ouro | lê o Tab a cada 0,1 s e a API local a 1 Hz com o Tab aberto | barato; pouco provável |

## Plano do estudo

1. **Medir antes de mudar (você, 10 min).** Na Prática ou numa Arena, anotar o FPS com:
   (a) os dois overlays desligados; (b) só o ouro; (c) só os aprimoramentos. Ideal com o
   PresentMon, que mostra também o modo de apresentação (independent flip ou composto).
   Isso separa H1/H2 de H3 sem código novo.
2. **Ver se a API oficial do jogo já entrega a oferta.** O Overwolf lista `live_client_data`
   como uma das fontes da Arena. Durante uma escolha de aprimoramentos, abrir
   `https://127.0.0.1:2999/liveclientdata/allgamedata` no navegador e salvar a página. Se as
   cartas oferecidas estiverem ali, o OCR e a captura de tela deixam de existir.
3. **Overwolf (ow-electron).** Ler as condições de acesso ao GEP de LoL e ao overlay, o custo
   da assinatura de código e se a revisão aceita app privado. Resultado: viável ou não.
4. **Desenho do overlay sem custo de FPS**, com o que os passos 1–3 mostrarem:
   - dados: API local (passo 2) ou GEP (passo 3); OCR só como último recurso, e então só
     durante a escolha, com captura DXGI de uma região pequena, uma leitura por oferta;
   - exibição: janela só visível durante a escolha; ou fora do jogo (painel no cliente,
     segundo monitor), que não custa nada ao FPS.
5. **Critério de aceite** (já no plano original, ADR-5): FPS médio e 1% low com o overlay
   ligado iguais aos sem overlay, dentro do ruído de 3 medições.

Até o estudo concluir, a recomendação é manter "Aprimoramentos na Arena e no Mayhem"
desligado.

## Fontes

- Overwolf, eventos de LoL Arena: https://dev.overwolf.com/ow-native/live-game-data-gep/supported-games/league-of-legends-arena/
- Overwolf, eventos de LoL (`augments`, `picked_augment`): https://dev.overwolf.com/ow-native/live-game-data-gep/supported-games/league-of-legends/
- Overwolf, changelog: https://dev.overwolf.com/ow-native/getting-started/changelog/ow-changelog/
- ow-electron, lançamento e assinatura: https://dev.overwolf.com/ow-electron/getting-started/release-your-app , https://dev.overwolf.com/ow-electron/guides/dev-tools/app-signing
- Riot, Vanguard para desenvolvedores: https://support-developer.riotgames.com/hc/en-us/articles/28021427366163-Vanguard
- Riot, Vanguard FAQ: https://www.riotgames.com/en/DevRel/vanguard-faq
- Blitz, Vanguard: https://support.blitz.gg/hc/en-us/articles/8744136175375-Will-Blitz-gg-Continue-Working-with-League-of-Legends-with-the-Introduction-of-Vanguard
- Independent flip e overlays (Blur Busters): https://forums.blurbusters.com/viewtopic.php?p=60295
- NVIDIA FrameView 1.9 (overlay em janela separada e MPO): https://www.nvidia.com/en-us/geforce/technologies/frameview/release-notes/
- Captura de tela no Windows (Microsoft): https://learn.microsoft.com/nl-nl/archive/blogs/dsui_team/ways-to-capture-the-screen
