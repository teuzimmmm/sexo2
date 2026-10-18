# Protótipo SEXO2 1.0

Abra `index.html` no navegador (duplo clique). Não precisa de servidor nem de internet.

A barra superior troca entre as quatro áreas. O botão **Simulação** abre a gaveta da direita, que controla
o cronômetro, as respostas do cliente e os estados dos dados. Essa gaveta e a barra superior não fazem
parte do produto. O cliente aparece em 1280×720, o tamanho padrão do LoL, ampliado ou reduzido para
caber na tela.

## Telas

- **Seleção de campeões**: o botão SEXO2 no canto inferior direito abre o assistente logo acima dele
  (borda direita alinhada à do botão, 8 px de distância), com as abas Runas, Itens e Mods. A posição é
  calculada a partir do retângulo do próprio botão (`js/anchor.js`), com a mesma regra usada no plugin.
  - **Runas**:
    - cards Maior WR e Mais comum;
    - recomendações contra o adversário de rota, que é estimado e pode ser trocado;
    - árvore completa editável, com Voltar e Confirmar.
  - **Itens**: a página "SEXO2 — Campeão" como aparece na loja, com três grupos de três seções
    (sequência, Itens iniciais, Alternativas) para a maior WR, a mais jogada e o counter do adversário de
    rota. A importação acontece sozinha ao confirmar o campeão; o rodapé mostra o resultado.
  - **Mods**: escolha do mod do campeão e acesso à biblioteca.
- **Partida**: placar (Tab) com o valor dos itens por linha e por equipe. Segure Tab ou use a gaveta.
- **Aprimoramentos**: oferta de três cartas em ARAM Mayhem ou Arena (alternância na gaveta). Abaixo de cada
  carta, o que o SEXO2 leu e os números da fonte do modo: WR, PR e partidas, cada modo com a sua
  fonte. A carta com a melhor WR (com amostra suficiente) fica em destaque. Pela gaveta: nova oferta,
  fechar oferta, carta não reconhecida, reconhecimento errado e sem dados. **Corrigir** abre a lista para
  dizer qual é a carta; o botão ↻ simula a troca do jogo; clicar numa carta é a escolha do jogador.
- **Cliente e painel SEXO2**: painel aberto pelo botão SEXO2 da barra do cliente. Seções Skins, Mods,
  Sala, Configurações e Diagnóstico.

## O que experimentar nas runas

1. Confirme o campeão e clique em **Maior WR**. A página é importada na hora, e o rodapé mostra
   "Importando…" e depois a página aplicada.
2. Clique em runas e fragmentos. Edições válidas são aplicadas sozinhas depois de uma breve pausa;
   cliques rápidos geram uma única importação. Trocar de árvore deixa a página incompleta até você
   escolher as runas, e uma página incompleta não é enviada.
3. Use **Voltar**, abra **Mais comum** e use **Confirmar**.
4. Na gaveta, marque *Recusar importações* e escolha outra página: aparece a falha, e a página aplicada
   continua a anterior.
5. Durante uma edição, use *Encerrar fase* duas vezes, até "encerrada": nada novo é enviado, e a última
   página confirmada permanece.
6. Troque o campeão pela gaveta: as operações da seleção anterior são descartadas.

O registro na gaveta mostra cada envio, confirmação, falha e resposta descartada.

## Dados

- Ícones, nomes, IDs, preços e regras das runas são reais: Data Dragon 16.20.1, pt-BR, em
  `js/game-data.js` e `assets/`.
- Win rates, partidas, jogadores e inventários são **simulados** (`js/demo-data.js`).
- No app, os ícones e as regras vêm do próprio cliente (LCU), e as estatísticas do LoLalytics.
- Itens da aba Itens para Ahri: números e itens reais das fixtures LoLalytics do repositório (16.20).
- Aprimoramentos: nomes e ícones reais, recortados das capturas de ARAM Mayhem do projeto
  ARAM Mayhem Tracker (MIT, ver `tests/fixtures/augments/ORIGEM.md`); por isso os nomes estão em inglês.
  No app, nomes e ícones vêm do cliente, no idioma dele. As estatísticas dos aprimoramentos são simuladas.
- A porcentagem das runas é a da runa-chave; o tooltip explica.
- A dos itens é a do trio ou a de cada item, conforme a linha.
- O valor no placar é a soma dos preços dos itens, não o ouro obtido.

## Para avaliar (pendente de aprovação)

- Cores, espaçamentos e componentes (D-102, D-103).
- O botão SEXO2 no lugar do antigo botão de mods (D-104, D-105). A posição do assistente acima do botão
  foi aprovada (D-017).
- Organização das abas, nomes dos rótulos e textos (D-107).
- Dimensionamento da escala B compactada (D-101).
- Textos sob as cartas de aprimoramento, cor do destaque e a forma de corrigir uma carta durante a partida
  (D-115).
