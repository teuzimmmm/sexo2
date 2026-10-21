# Investigação da queda de FPS ao abrir o placar

18/10/2026. Registro inicial da investigação, antes da correção descrita ao final.
Nessa etapa nenhum comportamento, configuração, executável ou plugin foi alterado.
O usuário confirmou que percebe a queda também na versão corrigida.
Na comparação relatada, Tab sem os números não provoca a queda; ela aparece somente
com os números do SEXO2. É evidência do usuário, não uma captura instrumentada de FPS.

## Conclusão atual

A causa dos aproximadamente 30 FPS perdidos **ainda não está demonstrada**. Há um
custo medido nas consultas locais; a apresentação da janela transparente é a hipótese
principal após a comparação relatada pelo usuário. O cálculo dos valores foi pequeno
na amostra. Não houve captura de
tempos de quadro sincronizada com Tab e com a visibilidade do overlay.

Limite das observações automáticas: na sessão examinada,
o ouro está desligado, nenhuma thread Gold overlay foi registrada e não existe uma
janela Tk desse processo. As medições passivas dessa sessão não medem o overlay ligado.
O relato comparativo isola o sintoma melhor que esses registros, mas não separa o
custo da janela do custo das consultas, que ficam ativos juntos.

## Evidências locais

- Código examinado: `sexo2/overlay/gold_overlay.py`, no commit `f616949` da branch
  `galinacio`. As propostas de interface no diretório de trabalho são independentes.
- O módulo dentro do executável em uso, em `Downloads/SEXO2-corrigido`, foi inspecionado
  sem executá-lo ou importar seu código. Contém `overlay_bounds`, cache do desenho
  (`drawn`) e `_stop_event`: as correções anteriores estão no pacote instalado.
- Sessão do SEXO2 iniciada às 00:45:48: somente Augment overlay registrado; nenhuma
  ativação de Gold overlay nos registros examinados. Configuração consultada:
  `gold_enabled = false`, `augments_enabled = true`.
- Na partida observada, fila 400, o registro dos aprimoramentos é
  `[AUGMENTS] waiting: queue 400 has no augments`. Esse caminho não captura a tela
  nem mostra as cartas nesse modo.
- Enumeração passiva das janelas: jogo em primeiro plano, 1920×1080; nenhuma janela
  Tk do SEXO2. Não foi enviado Tab nem foram mostradas janelas de teste sobre o jogo.
- Windows 10 19045, GTX 1050 Ti, monitor reportando 74 Hz. O `game.cfg` contém
  `WindowMode=2` e `WaitForVerticalSync=1`; o registro do jogo confirma Borderless.
  Isso descreve a configuração lida, não verifica eventuais substituições pelo driver.

## Medições de custo

Foram feitas apenas leituras locais durante a partida. Nomes e inventários dos
jogadores não foram gravados. Os tempos são amostras curtas, não um ensaio de FPS.

| Caminho | Resultado observado | Limite da interpretação |
|---|---:|---|
| Comparação de 10 jogadores + layout, 100 execuções | média 0,0408 ms; máximo 0,1407 ms | Payload real reutilizado em memória, preços sintéticos; não inclui Tk, API ou GPU. |
| `_fetch('/playerlist')`, conexão nova | 33,81 ms | Uma leitura; depende do estado do jogo e do sistema. |
| `_fetch('/activeplayername')`, conexão nova | 24,84 ms | Uma leitura; as duas chamadas são sequenciais. |
| Perfil de outra chamada nova | 37 ms, dos quais cerca de 26 ms no caminho `connect` | Inclui conexão/TLS; não mede quanto o jogo fica ocupado atendendo. |
| Uma Session persistente, quatro consultas sucessivas | 34,66; 14,51; 4,02; 14,98 ms | Experimento separado; não representa ganho comprovado de FPS. |
| CPU do SEXO2, amostra passiva de 5 s com ouro desligado | 0,94% de um núcleo, 0,12% da máquina | Não caracteriza o custo do overlay ligado. |

O código chama `requests.get` separadamente para os dois endpoints, criando e fechando
uma Session por chamada. Enquanto Tab fica pressionado, isso se repete no máximo uma
vez por segundo. Portanto, os aproximadamente 59 ms observados **não são custo por
quadro**. Reutilizar uma conexão é uma otimização plausível para esse caminho, mas
não prova nem garante recuperar os 30 FPS relatados.

Os registros das duas partidas anteriores contêm médias gerais de 72,19 e 73,42 FPS,
com tempos médios de GPU de 10,93 e 10,55 ms. Eles não identificam os períodos de Tab
e não servem para negar nem confirmar uma queda localizada.

## Hipóteses que ainda precisam ser separadas

1. **Apresentação da janela sobre o jogo.** O ouro usa Tk, transparência por cor,
   janela layered/topmost e `deiconify` ao abrir. Mesmo com desenho imóvel, a janela
   continua sobre o jogo. A Microsoft documenta que conteúdo sobreposto pode mudar
   o caminho de apresentação para composição, composição reversa ou MPO. Não foi
   coletado `PresentMode`, portanto essa transição não foi observada nesta máquina.
   VSync ligado torna relevante verificar também se há uma mudança de cadência.
2. **Trabalho do placar nativo.** A comparação relatada pelo usuário desfavorece essa
   explicação: sem os números do SEXO2, Tab não causa a queda percebida. Falta somente
   registrar os tempos de quadro dessa comparação, como controle do ensaio.
3. **Conexões locais repetidas.** O custo é real e concentrado nas consultas. Pode
   contribuir para engasgos periódicos, mas a medida externa não demonstra uma
   perda sustentada de FPS do jogo.

O cache do desenho já evita redesenhar comparações iguais. A janela atual também
já foi reduzida a 256×466 px em 1080p; não é mais uma superfície de tela inteira.
Nenhuma dessas mudanças, sozinha, comprova resolver composição ou sincronização.

## Comparação necessária para fechar o diagnóstico

Usar uma cena reproduzível fora de uma partida competitiva, com as mesmas condições
e pelo menos três repetições. Não mudar resolução, VSync ou limite de FPS entre casos.

| Caso | Janela de ouro | Consultas do ouro | O que separa |
|---|---|---|---|
| A: Tab com ouro desligado | ausente | ausentes | Custo do placar nativo. |
| B: Tab com overlay atual | visível | presentes | Custo adicional total. |
| C: janela com números congelados | visível | ausentes | Apresentação da janela, sem custo das consultas. |
| D: leitura sem janela | ausente | presentes | Consultas, sem composição do overlay. |

Coletar tempos de quadro, modo de apresentação e CPU/GPU, marcando pressionar/soltar
Tab e mostrar/ocultar a janela. PresentMon é indicado pela própria Microsoft para
inspecionar o caminho de apresentação. C e D são variantes de diagnóstico a preparar
se necessárias; não foram implementadas nem executadas nesta investigação.

Só depois dessa comparação escolher uma correção para a queda sustentada. A mudança
menor já identificada é reaproveitar a conexão local, preservando frequência, timeout,
recuperação e isolamento da thread, e medir antes/depois. Uma troca de renderizador
não se justifica antes de verificar a hipótese de composição.

## Referências primárias

- [Microsoft: DXGI flip model e efeito de conteúdo sobreposto](https://learn.microsoft.com/en-us/windows/win32/direct3ddxgi/for-best-performance--use-dxgi-flip-model),
  seção DirectFlip. Sustenta a possibilidade da transição, não confirma sua ocorrência
  no LoL desta máquina.
- [Tk: implementação das janelas no Windows](https://github.com/tcltk/tk/blob/core-8-6-branch/win/tkWinWm.c).
  O caminho normal usa `SW_SHOWNOACTIVATE`; não há evidência coletada de perda de foco
  provocada pelo ouro. A janela do projeto também usa override-redirect e noactivate.

## Correção posterior autorizada pelo usuário

Pedido: “então melhore”. Implementadas somente mudanças internas do ouro, preservando
cores, textos, posição, tamanho, intervalo de atualização e a configuração do usuário:

- Uma `requests.Session` exclusiva da thread reaproveita a conexão local e ignora
  proxies do sistema para esse endereço de loopback. O timeout continua em 0,5 s.
- O nome do jogador ativo é reutilizado dentro da partida: após a primeira leitura,
  cada atualização precisa consultar somente `/playerlist`.
- Falhas descartam conexão e identidade; sair de InProgress ou encerrar a thread
  também fecha a Session. Identidade não encontrada é consultada novamente.
- Tab só mostra o ouro quando a janela do jogo está em primeiro plano. Após cada
  leitura, Tab, fase e parada são conferidos antes de exibir qualquer resultado.
- `state('normal')` substitui `deiconify`: usa a transição de estado do Tk sem a
  operação adicional de restack de `deiconify`. O cache do desenho permanece.

Verificação do Tk real em um desktop separado, sem trocá-lo para o usuário: estados
normal/withdrawn/normal corresponderam a visível/oculto/visível; os 14 elementos do
canvas permaneceram e as flags layered, click-through, toolwindow e noactivate foram
preservadas. Não foi mostrado um overlay de teste na partida do usuário.

Comparação curta de três leituras pareadas do caminho completo de consulta, usando
a versão anterior do Git e a nova, alternando a ordem entre pares:

| Par | Anterior (ms) | Novo (ms) |
|---|---:|---:|
| 1 | 109,57 | 38,93 |
| 2 | 65,00 | 14,82 |
| 3 | 93,86 | 15,21 |
| Mediana | 93,86 | 15,21 |

Payloads atuais da API local, preços sintéticos para a comparação e nenhuma janela
de teste visível. A primeira leitura nova inclui a abertura da conexão; as seguintes
reaproveitam conexão e identidade. Não há promessa de ganho equivalente de FPS: esse
ensaio curto mede latência das consultas, não tempos de quadro, e não substitui o
protocolo completo de `MEDICAO.md`. A hipótese de composição ainda precisa da
validação A/B em partida. Nenhuma configuração do LoL ou do SEXO2 foi modificada.

