# SEXO2 — passo zero: réplica navegável

Abra `index.html` com duplo clique no Finder, ou use “Abrir com → Safari”. Basta este único HTML: fontes, ícones, estilos e scripts estão incorporados. Funciona por `file://`, sem servidor, internet ou LoL.

No repositório: `design/propostas/sexo2-replica/index.html`.

## Base e escopo

Base: `sexoatividade@aa558147`, incorporada a `galinacio` pelo merge `b9e445cd`. Os 44 commits recentes e os 7 exclusivos anteriores foram preservados. Consulte `docs/arquivo/sincronizacao-galinacio/README.md` para as resoluções dos conflitos.

A réplica usa cópias do código visual atual, sem alterar plugins ou serviços ativos. Inclui o Hub (Skins, Mods, Sala, Configurações e Diagnóstico), seleção automática, favoritas com cartões/cromas, perfis, sorteio temático, biblioteca de mods, assistente de runas/itens e categorias do painel legado de mods. “Outras runas” e “Outras builds” seguem a implementação atual D-120, não a proposta antiga D-118.

A barra superior e o seletor de estados são controles da simulação, fora do produto. Use “Cliente”, “Seleção de campeões” e “Partida / overlays”. O Hub abre pelo botão SEXO2 do cabeçalho; o assistente, pelo botão inferior da seleção. Escape fecha os painéis que já têm esse comportamento no código original. Reiniciar simulação restaura os exemplos.

## Limitações explícitas

- Fundo, navegação nativa do LoL, seleção de campeões e cartas são aproximações; nenhum cliente real foi executado ou comparado pixel a pixel.
- Estatísticas, inventários, nomes de skins/cromas, perfis e participantes são exemplos. Os retratos dos campeões são reutilizados nos cartões de skins demonstrativos. Trocar campeão não produz estatísticas reais daquele campeão.
- Prévia dos overlays: posições e cores do ouro seguem o código atual; placar, fonte Segoe UI, cartas e textos nativos são aproximados em HTML/SVG. Não simula OCR, FPS ou cliques através da janela. As prévias não validam o overlay Windows.
- Painéis usam as dimensões do código atual (Hub 820×560; assistente 452×492) e o fundo usa 1280×720. Em janelas menores pode ser necessário rolar ou reduzir o zoom do navegador. Controles nativos como select variam por navegador/SO.
- Tudo fica em memória e se perde ao recarregar. Nenhum arquivo de mod, configuração do sistema, sala, importação, atualização ou relatório real é criado. A rede está bloqueada por CSP. Ações que exigem filesystem ou serviço apenas informam a simulação.
- Não reproduz o instalador, bandeja/janelas do Windows nem todas as rodas nativas de skin/croma do cliente.

## Verificação

Verificado no Safari do Mac por `file://`: navegação do Hub, salvar configuração simulada, favoritas por campeão e cromas, editor de runas, abertura por outra runa-chave, página de itens, listagem e escolha de outra build e retorno ao conjunto padrão. Fontes e imagens incorporadas foram inspecionadas visualmente. Isto não é validação no LoL ou no Windows.

Proveniência das cópias: `sources.json`. O HTML é independente desse arquivo e deste README.
