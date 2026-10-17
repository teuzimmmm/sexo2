# Protótipo SEXO2 1.0

Abra `index.html` no navegador (duplo clique). Não precisa de servidor nem de internet.

A barra superior troca entre as três áreas. O botão **Simulação** abre a gaveta da direita, que controla
o cronômetro, as respostas do cliente e os estados dos dados. Essa gaveta e a barra superior não fazem
parte do produto. O cliente aparece em 1280×720, o tamanho padrão do LoL, ampliado ou reduzido para
caber na tela.

## Telas

- **Seleção de campeões**: o botão SEXO2 no canto inferior direito abre o assistente, com as abas Runas,
  Itens e Mods.
  - **Runas**:
    - cards Maior WR e Mais comum;
    - recomendações contra o adversário de rota, que é estimado e pode ser trocado;
    - árvore completa editável, com Voltar e Confirmar.
  - **Itens**: trio de itens mais vencedor e mais comum, iniciais, botas, 4º a 6º item, adversário de rota
    e importação dos conjuntos.
  - **Mods**: escolha do mod do campeão e acesso à biblioteca.
- **Partida**: placar (Tab) com o valor dos itens por linha e por equipe. Segure Tab ou use a gaveta.
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
- A porcentagem das runas é a da runa-chave; o tooltip explica.
- A dos itens é a do trio ou a de cada item, conforme a linha.
- O valor no placar é a soma dos preços dos itens, não o ouro obtido.

## Para avaliar (pendente de aprovação)

- Cores, espaçamentos e componentes (D-102, D-103).
- Posição e tamanho do assistente na seleção, e o botão SEXO2 no lugar do antigo botão de mods (D-104, D-105).
- Organização das abas, nomes dos rótulos e textos (D-107).
- Dimensionamento da escala B compactada (D-101).
- Opção "Importar itens ao confirmar o campeão" (D-106).
