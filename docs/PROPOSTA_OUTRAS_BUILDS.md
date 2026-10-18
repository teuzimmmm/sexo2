# Escolha opcional de outras builds

**Estado: proposta para revisão. Não autoriza implementação.**

**Protótipo HTML navegável:** [abrir outras-builds.html](../design/propostas/outras-builds.html).
Funciona localmente, sem servidor e sem conexão com o aplicativo. Os dados e os ícones
estão congelados para esta revisão; “Importar conjunto” e “Voltar ao padrão” apenas simulam
a mudança dentro da página. Novos textos e interações continuam pendentes de aprovação.

Pedido de 18/10/2026: as recomendações e a importação padrão estão corretas. O usuário
quer poder escolher, quando desejar, outras combinações possíveis, incluindo caminhos
com itens de AP, seguindo o design existente. Esta proposta não redesenha o assistente
nem troca o critério das recomendações atuais.

## 1. Problema e resultado esperado

A aba Itens recebe hoje os dois resumos do LoLalytics: maior WR e mais jogado. Esses
resumos podem ter o mesmo trio inicial, variando somente os itens posteriores. Isso
não significa que a consulta esteja errada: a interface expõe somente dois caminhos
de uma tabela muito maior.

Resultado proposto: manter a experiência atual e oferecer uma navegação opcional pelas
demais combinações observadas. O usuário examina uma alternativa e decide explicitamente
se quer importá-la. Abrir a lista, pesquisar e visualizar uma combinação não escreve
nada no cliente.

## 2. Evidência e limite dos dados

Foi inspecionada, sem modificar, a resposta em cache coletada na máquina do usuário em
18/10/2026 às 00:46:57. Contexto confirmado: Cho'Gath, Selva, ranked, patch 16.20,
Esmeralda+, todas as regiões, sem filtro de runa-chave.

A tabela `builtBootSet3` contém **519 linhas** nesse recorte. Cada linha traz uma
combinação ordenada de três IDs, WR, taxa de escolha e partidas. O parser existente já
reconhece essa tabela como uma amostra conjunta de itens (`joint_build_sample`).

Exemplos dessa resposta, apresentados como evidência histórica, não como recomendações:

| Combinação de IDs | WR | Taxa de escolha | Partidas |
|---|---:|---:|---:|
| 3084 → 3009 → 3742 | 55,96% | 18,63% | 24.827 |
| 3152 → 3009 → 4633 | 54,65% | 3,70% | 4.935 |
| 3152 → 3009 → 4645 | 64,71% | 0,01% | 17 |

Uma WR maior com 17 partidas não comprova superioridade à combinação com milhares.
A escolha manual poderá acessar esses caminhos, sempre mostrando a amostra.

**Limites obrigatórios:**

- A estatística pertence aos três itens observados, não a seis itens nem à página
  inteira de runas.
- Os dados individuais de quarto, quinto e sexto itens não provam que foram comprados
  junto de qualquer trio selecionado.
- Uma combinação com AP não será rotulada automaticamente como “a melhor full AP”.
- A lista alternativa usará o contexto geral da rota, sem herdar o filtro de runa-chave
  dos dois resumos atuais. Isso evita limitar a exploração às mesmas builds iniciais.
- Ausência de uma combinação na fonte não será preenchida com números de outra rota,
  runa, fila ou patch.

## 3. Design e organização

Referências: D-007, D-008, D-015 a D-019; `design/tokens.css`;
`design/propostas/sexo2-v1/css/styles.css`; plugin `SEXO2-Assistant`.

- Mesmo painel de **452×492 px**, cabeçalho do campeão, seletor de rota e abas
  Runas / Itens / Mods.
- Mesma posição: acima do botão SEXO2, 8 px de distância, borda direita alinhada e
  conteúdo contido na janela.
- Oswald em títulos e abas; Inter nos demais textos; números tabulares.
- Mesmas superfícies escuras, bordas discretas, ícones quadrados e rolagem interna.
- Reutilizar botões, campos de texto e linhas densas existentes. Sem nova
  paleta, família tipográfica, janela, aba principal ou cartões maiores.
- Fonte, patch, contexto e escopo estatístico ficam nos tooltips e no diagnóstico,
  sem acrescentar parágrafos técnicos ao fluxo do jogador.

**Ponto de entrada proposto:** um botão secundário “Outras builds” na aba Itens.
A listagem ocupa o corpo do próprio painel; cabeçalho, abas e dimensões permanecem.

Wireframe estrutural; todos os novos textos abaixo são **propostas**, não aprovados:

```text
┌─────────────────────────────────────────────────┐
│ CHO'GATH  [Selva]                            [×] │
│ RUNAS       ITENS       MODS                     │
├─────────────────────────────────────────────────┤
│ OUTRAS BUILDS                          [Voltar] │
│ Item                       Partidas mínimas    │
│ [Nome do item            ]  [0                ] │
│ 288 combinações                                │
│ Itens                          [WR] [Partidas ↓]│
│ [item] → [item] → [item] [5 ordens] 55,96% 24.827│
│ [item] → [item] → [item] [4 ordens] 53,80%  7.396│
│ [item] → [item] → [item] [5 ordens] 54,53%  5.898│
│                                                 │
│ [Mais combinações]                              │
├─────────────────────────────────────────────────┤
│ Conjunto importado                              │
└─────────────────────────────────────────────────┘
```

Os ícones representarão os IDs reais, com nomes e imagens do cliente no idioma dele.
As colunas precisam caber no painel: a lista mostra os itens, WR e partidas; taxa de
escolha fica no tooltip e na prévia, sem alargar a listagem.

### Revisão visual — controles diretos

Pedido seguinte do usuário: repensar o design a partir do campo numérico simples.
Esta revisão substitui a apresentação anterior do HTML, mantendo a proposta pendente:

- Busca e amostra mínima lado a lado, com rótulos acima. O mínimo é um campo de texto
  com teclado numérico e apenas dígitos; sem setas, controle de incremento ou ajuste
  por roda do mouse. Vazio equivale a zero. A busca também é um campo simples, sem
  lista nativa de sugestões sobrepondo os resultados.
- Ordenação nos próprios títulos “WR” e “Partidas”, sempre decrescente. A coluna ativa
  recebe uma seta discreta. Isso substitui o seletor separado de ordenação.
- Título, campos, contagem e cabeçalhos permanecem visíveis. Somente os resultados
  rolam. A posição na lista é preservada ao voltar da prévia; alterar filtros ou
  ordenação volta ao começo da lista.
- “N ordens” fica na mesma linha dos ícones, como ação independente da prévia.
  Expandir não importa nem seleciona outra build; revela as demais ordens daquele
  grupo, cada uma com seus próprios números. O agrupamento permanece ao voltar.
- “Limpar filtros” aparece apenas quando há busca ou mínimo ativos; preserva a
  ordenação escolhida. Uma linha inteira continua abrindo sua prévia.
- Prévia com o mesmo cabeçalho e ação “Voltar” à direita; métricas em tabela e os
  três itens em linhas numeradas. A confirmação permanece no rodapé.
- Cabeçalho do campeão, abas, página padrão, dimensões, posição, cores, fontes e
  componentes aprovados permanecem. A moldura de revisão usa fundo neutro e texto
  reduzido; os detalhes dos dados ficam recolhidos fora da interface do produto.

Textos e interações novos nesta revisão: rótulo “Item”, placeholder “Nome do item”,
“Limpar filtros”, título “Ordem dos itens”, ordenação por cabeçalho e expansão de
ordens por botão na linha. São propostas cobertas por D-118, sem implementação no app.

## 4. Exploração e escolha

1. A tela inicial continua exibindo a página atual, com sua importação automática.
2. “Outras builds” carrega a tabela do mesmo campeão, modo, rota, patch, tier e região.
3. Busca por nome de item, com seleção do item por ID: permite encontrar caminhos que
   incluam um item desejado de AP sem depender de um classificador “AP / tanque”.
   Vários itens selecionados exigem que todos estejam na combinação.
4. A ordenação inicial é por partidas, decrescente. O jogador pode escolher WR
   clicando no título da coluna correspondente, sem abrir um seletor.
   Empates são resolvidos por partidas e depois por IDs, de forma estável.
5. “Partidas mínimas” começa em zero para não esconder opções raras. Alterar esse filtro
   só muda a lista exploratória, nunca o padrão automático nem o nível de risco global.
6. Combinações com os mesmos três itens em ordens diferentes aparecem em um grupo
   expansível. A linha principal representa a ordem mais jogada. Ao expandir, cada ordem
   conserva sua própria WR e amostra; nada é somado ou apresentado como WR agregada.
7. Uma troca de botas continua sendo uma combinação distinta. Não agrupar estratégias
   por semelhança visual ou por uma classificação inventada de build.
8. A lista renderiza inicialmente 20 grupos e oferece os próximos sob demanda. Todas as
   combinações válidas permanecem acessíveis; não haverá corte definitivo nas 20 primeiras.
9. Clicar em uma linha abre sua prévia dentro da aba. Somente “Importar conjunto” aplica
   a escolha. “Voltar” cancela a prévia e conserva o conjunto já confirmado.

## 5. O que será importado

**Padrão atual:** preservado integralmente, incluindo a página gerenciada única, os grupos
atuais e a importação ao confirmar/trocar o campeão. Builds semelhantes não serão
substituídas à força para produzir diversidade.

**Escolha manual proposta:** importar somente a combinação de três itens escolhida,
na ordem e com os números que a fonte publicou, na mesma página `SEXO2 — {Campeão}`.
Enquanto esse modo manual estiver ativo, a prévia e a loja devem refletir essa seleção.
Não completar automaticamente uma alternativa de AP com os últimos itens da build tanque.

Essa substituição temporária da página, em vez de acrescentar um quarto grupo, mantém
uma página e evita extrapolar o limite de seções da decisão D-018. É uma extensão de
comportamento que precisa de aprovação explícita na revisão desta proposta.

- Conservar o `uid` gerenciado; conjuntos pessoais não são alterados ou apagados.
- A escolha de itens não troca nem importa runas.
- “Voltar ao padrão” restaura explicitamente a página automática daquela seleção.
- Fechar e reabrir o painel preserva a escolha manual da seleção atual.
- Atualizações repetidas do mesmo campeão não sobrescrevem a escolha manual.
- Mudar campeão, rota, modo ou sessão invalida a prévia e a escolha manual. A próxima
  confirmação elegível segue o padrão automático do novo contexto.
- Ao começar a partida, fica o último conjunto confirmado; nenhuma resposta atrasada
  pode substituir esse conjunto ou interferir na seleção seguinte.
- Em falha, a última página confirmada continua no cliente. O painel não anuncia sucesso.

**Build de seis itens:** a fonte inspecionada comprova trios, não uma sequência alternativa
completa de seis. A primeira entrega não promete esse dado. Caso se queira editar os três
itens restantes, isso será uma extensão manual separada, sem WR conjunta inventada, com
proposta própria antes de implementar. Esta distinção precisa estar aceita antes do código.

## 6. Dados, arquitetura e desempenho

O Pengu exibe a lista e envia intenções. O Python mantém consulta, validação, cache e
escrita no LCU, seguindo D-003. O navegador não consulta LoLalytics diretamente.

Responsabilidades previstas, ainda sem implementar:

| Área | Responsabilidade |
|---|---|
| `sexo2/services/stats.py` | Extrair alternativas dos registros conjuntos já normalizados; preservar origem e filtros resolvidos. |
| `sexo2/services/assistant.py` | Separar estado automático, navegação e escolha manual; validar o contexto antes de cada importação. |
| `sexo2/services/item_sets.py` | Empacotar o trio escolhido no conjunto gerenciado e reutilizar confirmação por releitura. |
| `SEXO2-Assistant/index.js` | Reutilizar componentes para listagem, filtros, prévia e confirmação. |
| Testes correspondentes | Cobrir proveniência, escolhas, corridas entre contextos e preservação de dados pessoais. |

Identidade obrigatória de cada opção: campeão, modo, rota efetiva, patch, tier, região,
condicionamento da consulta, IDs ordenados, WR, partidas, taxa de escolha quando disponível,
fonte e coleta. A importação aceita somente uma opção reconhecida pelo serviço no contexto
atual; não confia em IDs ou números arbitrários enviados pelo plugin.

- Usar primeiro a resposta geral já obtida/cacheada para aquele contexto.
- Fonte adicional só após abrir a exploração e apenas se os dados necessários faltarem.
- Busca, ordenação e paginação são locais; não fazer uma consulta por item ou por tecla.
- Sem crawling de todas as builds, novas varreduras periódicas ou mudanças nos overlays.
- Não carregar centenas de imagens ao mesmo tempo; somente as linhas renderizadas.
- Limites de memória e quantidade de registros devem preservar os limites existentes do
  coletor. Fonte incompleta gera estado indisponível, não combinação fabricada.
- SR e ARAM só oferecem a exploração onde a tabela conjunta for validada. Swiftplay,
  Arena e Mayhem não herdam esse contrato por analogia; o fluxo padrão existente continua.

## 7. Estados e falhas

Prever no mesmo corpo: carregando, lista disponível, busca sem resultado, fonte sem
combinações, falha de rede, prévia, importação pendente, confirmação e falha de confirmação.
Nenhum desses estados apaga o conjunto já confirmado. “Tentar novamente” é uma ação
manual; nada de repetição contínua silenciosa.

Resposta de uma rota anterior é descartada. A identidade também precisa acompanhar os
filtros da exploração e a prévia para impedir que o cabeçalho mostre Selva enquanto uma
lista de Topo continua selecionável.

## 8. Entregas e critérios de aceite

**Etapa 1 — contrato de dados.** Fixture sanitizada do caso Cho'Gath, confirmação dos
trios alternativos e de suas métricas, filtros e agrupamento. Sem mudar o padrão.

**Etapa 2 — protótipo para revisão visual.** HTML estático que importe os tokens e
reutilize o CSS de `sexo2-v1`, mostrando lista, prévia e retorno ao padrão. Não conecta
ao cliente nem importa itens. A aparência é revisada antes de conectar o fluxo real.

**Etapa 3 — serviço e importação.** Somente após aprovar a proposta e o protótipo:
implementação com o conjunto gerenciado existente e operações protegidas por contexto.

**Etapa 4 — interface e validação.** Conectar o protótipo ao serviço, rodar as suítes e
o CI Windows, gerar executável de teste e conferir o painel e a loja no LoL.

Aceite mínimo:

- Sem abrir “Outras builds”, o resultado automático é idêntico ao atual.
- Uma alternativa fora de `summary.win`/`summary.pick` aparece e pode ser encontrada por item.
- WR e partidas conferem com a linha da fonte; as ordens agrupadas não somam estatísticas.
- Opções raras continuam acessíveis e mostram sua amostra.
- Navegar e visualizar não escreve no LCU; confirmar escreve só no conjunto gerenciado.
- Runas e conjuntos pessoais permanecem iguais.
- Cancelamento, falha e respostas atrasadas preservam a última importação confirmada.
- Trocar contexto invalida a opção antiga; reabrir o painel no mesmo contexto a preserva.
- A escolha manual não é sobrescrita por um callback repetido da importação automática.
- Não há estouro horizontal no painel de 452×492; busca, rolagem, tooltip e teclado funcionam.
- Teste real confirma a página na loja. Testes simulados não são tratados como validação real.

## 9. Decisões pendentes para revisão

**D-118 — escolha opcional de outras builds.** Revisar em conjunto:

1. Entrada “Outras builds”, listagem no mesmo painel, filtros, agrupamento e prévia.
2. Confirmação explícita para importar; visualizar não altera nada.
3. Substituição temporária da página gerenciada pelo trio escolhido e ação “Voltar ao padrão”.
4. Escolha manual válida apenas no contexto atual, sem persistir para outros campeões/partidas.
5. Primeira entrega limitada aos trios comprovados; edição dos seis itens fica fora deste escopo.

Textos novos propostos: “Outras builds”, “Buscar por item…”, “Mais jogadas”, “Maior WR”,
“Partidas mínimas”, “Mais combinações”, “Voltar ao padrão” e textos dos estados de falha.
Componentes são reaproveitados; posições internas e interações novas continuam pendentes.

Nenhuma dessas decisões é considerada aprovada por constar neste documento.

## Referências locais

- `docs/produto/decisoes.md` e `docs/produto/glossario.md`.
- `.claude/skills/sexo2-ui/SKILL.md` e `design/wireframes.md`.
- `design/propostas/sexo2-v1/README.md` e `css/styles.css` desse protótipo.
- `lolalytics/parsing.py`, `builds.py`, `item_pages.py` e `query.py`.
- `sexo2/services/stats.py`, `assistant.py` e `item_sets.py`.
