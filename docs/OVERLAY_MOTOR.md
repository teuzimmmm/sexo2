# Substituição do motor do overlay

Investigação de 17/10/2026, após o usuário informar que a edição 2.0.0.4
também não exibiu o overlay. Este documento sucede a tentativa descrita em
[OVERLAY_CORRECOES.md](OVERLAY_CORRECOES.md). A rodada de composição ao final
integra DirectComposition ao produto; **ainda não há validação no LoL real**.
A janela GDI anterior não é mais o renderer de produção. As seções de pesquisa
e laboratório abaixo registram as etapas anteriores.

## Restrições e situação

- Requisito confirmado pelo usuário: as cartas do overlay devem corresponder
  **às opções oferecidas na tela naquele momento**, tanto em Arena quanto no
  ARAM com aprimoramentos/Mayhem. Uma lista geral por campeão não atende a isso.
- Overwolf foi explicitamente rejeitado. Não adicionar Electron.
- Game Bar foi explicitamente rejeitada depois da explicação de funcionamento.
  A solução deve ser independente; não torná-la dependência nem fallback.
- Não há medição de RAM da Game Bar neste ambiente Linux. Sua arquitetura inclui
  um host e o aplicativo do widget; ausência de Electron não comprova baixo
  consumo nem uma vantagem sobre Blitz. Não citar um valor universal de RAM.
- A falha anterior ocorreu também sem bordas. Não atribuí-la apenas à tela cheia.
  Testes de criação de janela passaram, mas não demonstraram exibição no LoL.
- Sem acesso ao LoL Windows do usuário, a causa concreta continua desconhecida.
  Não há evidência de que o Vanguard tenha bloqueado a janela GDI anterior.

## Motores examinados

| Fonte | Evidência no código/documentação | Licença conferida | Decisão atual |
| --- | --- | --- | --- |
| [XboxGameBarSamples](https://github.com/microsoft/XboxGameBarSamples/tree/bd53d41dce2590727bd393cbafe9425a7e0cb3ae) | Widget UWP/XAML no host Game Bar, sem exigir Electron | MIT dos exemplos; plataforma Microsoft separada | Rejeitada pelo usuário |
| [hudhook](https://github.com/veeenu/hudhook/tree/72e1cc062c35df847b703e5507b82eb21d80d82c) | Rust/ImGui, hooks DirectX/OpenGL; `src/inject.rs` usa `OpenProcess`, `WriteProcessMemory` e `CreateRemoteThread` | MIT | Motor independente real, mas funcionamento no LoL/Vanguard não demonstrado; não instalar seu injetor no produto |
| [GOverlay](https://github.com/hiitiger/goverlay/tree/3ca1f040b180dc6ce84baca093c6f726748461ad) | Motor C++ com DLL dentro do jogo e comunicação com a UI; não exige necessariamente Electron | Arquivo LICENSE: GPLv3 com termos adicionais, incluindo atribuição clicável em cada tela | Não incorporar sem resolver obrigações da distribuição e compatibilidade com o jogo |
| [GameOverlay.Net](https://github.com/michel-pi/GameOverlay.Net/tree/b43c9d9a2dc3e3423b63732f279a357d8fb1f263) | Direct2D/SharpDX em janela externa transparente; repositório arquivado | MIT | Não selecionado: trocar GDI por Direct2D não comprova resolver a falha; há limitações documentadas de tela cheia |
| [Open League Overlay](https://github.com/bossNilac/Open-League-Overlay/tree/2bca5917ce7b249eaad6024be8a7d64090ec534a) | Projeto C++ específico para LoL; README declara janela externa e Live Client Data API, sem hooks | MIT | Referência para investigar, não prova independente de funcionamento no PC do usuário ou de suporte a tela cheia |

Na investigação inicial, as referências foram fixadas em commits e a revisão leu
README, licença e, no hudhook, o injetor. Depois, a rodada do host abaixo adicionou
o hudhook como dependência exclusiva do laboratório, com versão travada. Os demais
motores não foram compilados. Para reproduzir a inspeção sem credenciais:

```sh
curl --fail --max-time 30 https://raw.githubusercontent.com/veeenu/hudhook/72e1cc062c35df847b703e5507b82eb21d80d82c/LICENSE
curl --fail --max-time 30 https://raw.githubusercontent.com/veeenu/hudhook/72e1cc062c35df847b703e5507b82eb21d80d82c/src/inject.rs
curl --fail --max-time 30 https://raw.githubusercontent.com/hiitiger/goverlay/3ca1f040b180dc6ce84baca093c6f726748461ad/LICENSE
```

Não foi encontrado um SDK público reutilizável do motor atual de Blitz/U.GG.
Não afirmar como suas versões atuais desenham o overlay sem evidência. Reutilizar
uma biblioteca com licença adequada é diferente de extrair seus binários privados.

## Compatibilidade e limites das evidências

A [Riot anunciou](https://support.riotgames.com/en-us/riot/performance/game-memory-access-removed-for-third-party-apps)
restrição de acesso à memória por aplicativos desconhecidos a partir de
06/10/2026. Isso torna inadequado presumir que um injetor genérico funcionará
porque já funcionou em outros jogos. O anúncio não comprova que toda janela
externa seja bloqueada nem que tenha causado nossa falha. Não contornar negativa
de acesso, modificar Vanguard ou aproveitar permissões de outro programa.

A [Microsoft documenta limitações](https://learn.microsoft.com/en-us/xbox/game-bar/known-issues)
da própria Game Bar, inclusive em certas combinações de renderização/driver.
Ela também não é garantia universal de tela cheia. O
[Discord descreve](https://discord.com/blog/how-to-use-discords-in-game-overlay-to-talk-while-playing-on-pc)
seu overlay de 2025 para janela/sem bordas: aplicativos conhecidos não usam
necessariamente um único mecanismo e não se deve confundir sem bordas com
tela cheia exclusiva.

## Plano antes de alterar a implementação

1. **Pesquisa realizada:** identificar mecanismo, licença e dependências das
   alternativas. Nenhum motor independente foi confirmado no LoL atual.
2. **Candidato de laboratório:** hudhook/ImGui, com somente o suporte DirectX 11
   habilitado. O recurso `inject` fica desabilitado. Primeiro testar em um host
   próprio que instala o hook em seu próprio processo. Isso avalia o motor e
   protocolo sem interagir com LoL/Vanguard. Não é a seleção definitiva para o jogo.
3. **Implementação após seleção:** preservar `Frame`, `View`, `OverlayStore` e
   `ArenaFeed`; substituir o adaptador de desenho e seu ciclo de vida. Conservar
   a fonte de contexto e a coleta fora da thread de renderização. Fonte de dados
   indisponível e motor indisponível precisam de estados distintos.
4. **Validação:** primeiro um host próprio Windows; depois LoL em janela,
   sem bordas e tela cheia, registrando separadamente quais funcionam. Só então
   empacotar outra correção do overlay. Host próprio não substitui essa etapa.

### Contratos que a substituição deve preservar

- Adaptador recebe `frame() -> Frame`, expõe `start()`, `stop()` e `diagnostic()`.
- `Frame` contém somente projeção de exibição. Não enviar credenciais LCU,
  identificadores de conta, respostas brutas ou configurações pessoais ao motor.
- Havendo processo auxiliar, definir antes um protocolo local versionado,
  tamanho máximo, expiração e encerramento; não abrir outro servidor permanente
  ou enviar consultas de rede pelo renderer.
- Dados expirados, jogo diferente, saída de partida e desligamento escondem a UI.
  Nenhuma alteração de runas, itens ou skins ocorre pelo renderer durante o jogo.
- Arena mostra popularidade/jogos, sem WR restrita. Mayhem não herda dados ARAM
  por aproximação; detecção automática das três cartas continua não comprovada.
- Medir memória privada, working set, CPU e efeito no tempo de frame: programa
  ocioso, partida com painel recolhido e aberto, incluindo processos auxiliares
  e eventual host. Informar que soma de working sets pode duplicar memória
  compartilhada. Sem números prometidos antes da medição.

## Critério de encerramento

Motor/licença definidos; código e empacotamento revisados; falhas isoladas do
programa; validação real no LoL documentada; custos medidos em Windows.
O laboratório abaixo valida o candidato somente no próprio processo.
O overlay continua pendente, e nenhum instalador novo foi gerado nesta rodada.

## Rodada do host isolado — contrato registrado antes do código

Arquivos novos: `native/overlay-host/`, `sexo2/overlay/wire.py`,
`scripts/native_overlay_probe.py`, `tests/test_overlay_wire.py` e job manual
`native_host_only` no workflow de testes existente. Não alterar a seleção do
renderer em produção, skins, painel de draft, coletor ou instalador.
Não incluir DLL/injetor para outro processo.

O Python projeta `Frame` em JSON Lines UTF-8 no stdin do host. Uma mensagem tem
no máximo 256 KiB, versão 1, sequência crescente, validade de no máximo 8 segundos,
estado ativo/prévia e somente títulos/linhas dos cartões; sem chave da partida
ou dados LCU. Limites: 16 cartões, 256 linhas por cartão, 512 caracteres por texto.
Não truncar silenciosamente: mensagem incompatível produz erro de protocolo.
O host guarda somente o frame mais recente, oculta ao expirar/EOF/erro e usa um
prazo máximo explícito de execução. Nenhuma porta, arquivo de dados ou rede.

O teste Python cria um frame sintético e inicia o host com stdin/stdout privados,
prazo limitado e encerramento do filho em falha. O relatório contém apenas
contadores de recebimento/desenho/expiração e declara `leagueValidated: false`.
Não chamar o host de janela de overlay sobre o jogo: é uma janela DX11 própria.
Contadores de callback comprovam passagem pelo renderer, não leitura de pixels.

Critérios desta rodada: protocolo testado offline, compilação Windows do candidato,
host recebe dados e executa o callback de desenho, expira/esconde dados e encerra.
Compatibilidade com o jogo e medição comparativa de recursos continuam separadas.

## Resultado do laboratório

Código `4530b256e2db0dec56d3bb6c753f83ed8b625f10`. O
[job Windows privado 39001443126](https://github.com/teuzimmmm/sexo2/actions/runs/39001443126)
passou em 17/10/2026: cinco testes do produtor Python, quatro do consumidor Rust,
compilação debug/release do host e execução DX11 no próprio processo. O job do
instalador foi ignorado; somente o relatório de teste foi disponibilizado.

O relatório registrou driver `hardware`, 212 apresentações/callbacks, 42 callbacks
com frame ativo, 170 ocultos, uma expiração, duas mensagens válidas e uma mensagem
rejeitada. O teste verificou o encerramento do filho. Isso comprova o fluxo pelo
callback de renderização, não a inspeção de pixels, qualidade visual ou atalhos.
`leagueValidated: false` e `injectionFeature: false` fazem parte do resultado.

A árvore de features para `x86_64-pc-windows-msvc` confirmou somente `dx11` no
hudhook, sem `inject`. Localmente passaram 64 testes Python de overlay/serviços,
dois testes Node de configurações e os quatro testes Rust portáveis. Quinze testes
locais adicionais do instalador passaram após a alteração do workflow. Foram
revisados os limites de leitura, expiração, esquema, ciclo de vida e projeção sem
conta/chave de partida; a licença MIT acompanha o código do candidato.

Reprodução do job sem gerar instalador, no branch privado de testes autorizado:

```sh
gh workflow run 387235855 --ref test/installer-2.0 -f native_host_only=true
```

### O que falta para substituir a edição atual

1. Demonstrar um carregamento compatível com LoL/Vanguard em Windows real.
   O laboratório não contém essa via e não abre o processo do LoL. Não adicionar
   o injetor genérico como se essa compatibilidade estivesse comprovada.
2. Depois dessa demonstração, integrar o adaptador ao `OverlayRuntime`, com
   encerramento/diagnóstico e protocolo de renovação de frames adequados à partida.
   O laboratório limitado a 4 s não deve ser convertido em host permanente por
   simplesmente remover o timeout.
3. Validar desenho, interação e consumo em jogo; cobrir modos/fontes de dados
   efetivamente confirmados. Sem isso, não empacotar uma alegada correção.

A versão de teste instalada pelo usuário continua com o motor anterior. Nenhuma
mudança desta rodada consertou ou substituiu silenciosamente esse motor.

## Cartas oferecidas na tela — requisito obrigatório

O `ArenaFeed` atual conhece estatísticas por campeão e tabelas de aprimoramentos;
ele **não conhece as opções que o jogo está oferecendo**. As tabelas
`augment1..4` são posições de aquisição observadas na fonte, não as opções da
oferta atual. O laboratório DX11 usa cartões sintéticos e também não detecta
cartas. Corrigir o renderer sozinho não conclui essa funcionalidade.

Pipeline necessário: identificar a oferta atual → resolver seus IDs → cruzar
somente esses IDs com estatísticas do campeão/modo/patch → exibir os resultados
na mesma ordem/posição das opções do jogo. Usar pick rate e jogos em Arena,
preservando as restrições de WR; popularidade não é probabilidade de vitória.

1. Investigar primeiro uma fonte local acessível que exponha **opções oferecidas**,
   distinguindo-as de aprimoramentos já escolhidos. Nenhum endpoint para essas
   opções está confirmado. Não ler memória do jogo nem contornar Vanguard.
2. Se essa fonte não existir, avaliar captura local da janela do jogo e
   reconhecimento de nomes/ícones no recorte das cartas. O usuário quer dados
   correspondentes à tela; não presumir que precisamos capturar o desktop inteiro.
   Não transmitir imagens, salvar capturas ou colocá-las em logs por padrão.
3. A observação deve carregar revisão da partida/oferta, modo, IDs reconhecidos,
   momento de observação e estado de reconhecimento. Limitar trabalho e descartar
   resultados atrasados. Confiança de reconhecimento e filtro estatístico de
   risco são conceitos distintos.
4. Rerrolar, escolher uma carta, fechar a oferta, perder o contexto ou expirar a
   observação invalida a projeção anterior. Um erro de reconhecimento deixa a
   opção sem identificação; estatística ausente aparece como indisponível.
   Não substituir por cartas populares que não estão na tela.
5. Confirmar modo e fonte de estatísticas separadamente para Arena e ARAM com
   aprimoramentos/Mayhem. Identificar uma carta na imagem não confirma a existência
   de dados LoLalytics daquele modo; não usar dados Arena/ARAM clássico como
   equivalentes de Mayhem. A fonte Mayhem continua não confirmada.

Critérios de teste futuros: ofertas reais dos modos suportados, posições e
resoluções diferentes, idioma/escala de UI, rerrolagem e escolha, identificação
parcial/ambígua, perda da janela e respostas atrasadas. Confirmar visualmente que
cada métrica pertence à opção correspondente; não confundir o teste de render
DX11 com esse teste de reconhecimento. Nenhuma escolha automática é necessária.

### Implementação da leitura local — contratos da rodada

- `screen.py`: recortes GDI diretos do cliente do jogo em primeiro plano, sem
  capturar todo o desktop. Conferir HWND/PID/retângulo antes e depois; descartar
  em alt-tab, mudança de janela ou tamanho. Sem salvar imagens ou texto OCR.
- `offers.py`: resolução conservadora de nomes, estado de confirmação de duas
  leituras, expiração e invalidação por contexto. Preservar três posições, IDs
  desconhecidos e métricas indisponíveis. Nunca publicar a lista geral como oferta.
- `reader.py` e `sexo2-offer-reader` (novo binário Rust): um processo OCR Windows
  reutilizável, pipes privados, mensagens/imagens limitadas, timeout que encerra
  o filho e estados de erro estáticos. Usar modelos OCR instalados no Windows,
  sem modelo remoto, navegador, screenshots em disco ou OCR em serviço externo.
- `ArenaFeed` passa a oferecer uma projeção de estatísticas só dos IDs reconhecidos
  na tabela geral do campeão. As tabelas de posição 1–4 não são a oferta atual.
  Mayhem pode identificar nomes sem consultar Arena como substituto estatístico.
- `OverlayRuntime` conecta um worker de leitura separado à projeção. Só funciona
  em partida e modo elegível, lê um grupo de três recortes no máximo uma vez por
  segundo e expira a oferta em 2 s. Sem leituras sobrepostas ou consultas externas
  no worker OCR; o catálogo é carregado pelo LCU local uma vez por contexto.
- Geometria inicial dos títulos, em unidades da altura, é referência do projeto
  MIT [ARAM Mayhem Tracker](https://github.com/Sygnano/aram-mayhem-tracker/tree/7c28471bf5b511e545d8d1c38b63707157edb134),
  `crates/mayhem-core/src/layout.rs`: centros -0.3346/0.0062/0.3470, banda
  vertical 0.348–0.427 e largura 0.25. Isso é evidência do projeto de referência,
  não calibração reproduzida no LoL deste ambiente; Arena precisa de validação.
- Testes: matching, ambiguidade, rerrolagem, expiração, contexto, métricas apenas
  das opções, captura limitada e falhas; Windows OCR real com imagem sintética
  renderizada pelo teste. Não declarar esse teste como leitura de cartas reais.

### Fontes e operação da leitura

A consulta limitada de 17/10/2026 confirmou por HTTP 200:

- `https://static.developer.riotgames.com/docs/lol/queues.json`: fila 2400,
  descrição `ARAM: Mayhem`, mapa Howling Abyss. A classificação do overlay foi
  atualizada; os filtros do coletor e a UI do draft não foram ampliados.
- `https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/default/v1/cherry-augments.json`:
  554 registros; exemplos ID 1205/nameTRA `ADAPt`, 1141/`All For You`.
- `https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/default/v1/augment-lists.json`:
  listas CHERRY, KIWI e KIWI_JADE. Todos os nomes internos dessas listas
  resolveram no catálogo. Não usar essa evidência para inventar uma fonte de PR
  de Mayhem ou presumir que uma lista enumere toda oferta possível do jogo.

O programa usa o catálogo local traduzido em
`/lol-game-data/assets/v1/cherry-augments.json` para resolver nomes/IDs. O catálogo
é compartilhado entre modos; as **estatísticas** continuam separadas pelo modo,
campeão e contexto da partida. Nomes numéricos de fallback não são reconhecidos
como títulos. Leitura aproximada é identificada no painel, sem inventar uma
porcentagem de confiança nem misturá-la ao risco estatístico das recomendações.

O leitor funciona em Arena ou Mayhem com o jogo em primeiro plano, no máximo uma
leitura de três recortes por segundo. Duas leituras consistentes confirmam a oferta; ambiguidade,
mudança de opções ou falha invalidam a anterior. A validade de 2 s começa no
momento da **captura**, não na conclusão do OCR. A inicialização fria do OCR pode
levar até 8 s; uma imagem que envelheceu é descartada, preservando o helper já
inicializado para as próximas leituras. Sem renovação do contexto por 8 s, a
captura pausa e encerra o helper. Não há screenshots/texto OCR em disco ou logs.

Para uso a partir do código-fonte Windows, compilar o helper antes de iniciar o
programa. O instalador de teste passa a compilá-lo em staging e incluir seus
avisos de dependências; nenhum executável é baixado para substituir essa etapa.

```powershell
python scripts/build_offer_reader.py
$env:SEXO2_TEST_SCREEN_OCR = '1'
python -m unittest tests.test_overlay_screen_windows -v
```

É necessário ter ao menos um idioma OCR instalado no Windows. Idioma, resolução,
recortes reais e aparência das cartas do jogo ainda exigem validação. A captura
GDI foi projetada para janela/sem bordas; tela cheia exclusiva não está validada.
O renderer anterior continua separado deste trabalho e ainda não foi corrigido
ou substituído no LoL. O laboratório hudhook não foi ativado no processo do jogo.

### Validação da implementação de ofertas

Código final da rodada: `c5ba7620c874d39a87c78434a5f2fde95151cf58`.
O [job Windows 39002956756](https://github.com/teuzimmmm/sexo2/actions/runs/39002956756)
passou: 12 testes Python de protocolo/reconhecimento/ciclo de vida, cinco testes
Rust, dois testes de integração com o OCR real do Windows e compilação/staging
do helper com avisos de dependências. Também passou o laboratório DX11, que
continua sem interagir com o LoL. O job do instalador foi ignorado.

O teste OCR reconheceu três títulos sintéticos duas vezes no mesmo processo.
Outro teste criou uma janela Win32 própria, capturou só os recortes, executou OCR
e conferiu os três nomes, incluindo a guarda que rejeita o processo Python nas
regras de produção. O contexto de pixels físicos foi exercitado; monitores reais
com escalas diferentes e a geometria das cartas do LoL não foram testados.

SHA-256 do helper compilado/staged nesse job:
`785e87555945f1338fe39510457c2298f551b4d08f0c46a48d22dee270f06419`.
Nesse job não foi gerado instalador nem testado o pacote PyInstaller completo.
Posteriormente, a edição 2.0.0.5 compilou e auditou o helper, avisos e módulos
Python no pacote final; instalação/reinstalação/desinstalação passaram. Veja
[INSTALADOR_TESTE_2_0.md](INSTALADOR_TESTE_2_0.md#validação-windows--2005).
Isso não altera as limitações de validação no jogo abaixo.

Passaram 88 testes locais de regressão dos serviços/overlay, dois testes Node
de configurações e 58 testes focados após a correção final de DPI. São cobertos
matching conservador, nomes ambíguos/numéricos, posições, identificação parcial,
rerrolagem, expiração, contexto diferente, EOF/esquema inválido, escrita bloqueada
no pipe, encerramento do filho e OCR demorado. O teste de demora também confirma
que a ausência de renovação do contexto interrompe a captura.

**Limites de conclusão:** leitura/projeção integradas no código e testadas com
Windows real e imagens/janela sintéticas; nenhuma carta real de partida foi
validada. A fonte de estatísticas de Mayhem no LoLalytics e a correção do renderer
em jogo continuam pendentes. Não apresentar os testes acima como prova dessas
funcionalidades.

## Correção de composição — plano antes do código (17/10/2026)

Problemas reproduzíveis por inspeção: `SetWindowPos(HWND_TOPMOST)` só é chamado
quando o conteúdo/geometria muda; outro topmost pode encobrir o painel para
sempre. A janela também oculta toda a UI em Arena/Mayhem sem uma oferta OCR,
impedindo distinguir ausência de dados de ausência do renderer. Isso não prova
qual problema ocorreu no PC do usuário.

Substituir o desenho GDI por DirectComposition + Direct3D 11 + Direct2D/DirectWrite
em DLL própria carregada **somente pelo SEXO2**. Preservar o controlador Win32 e
os atalhos, com nova reafirmação periódica do z-order, geometria em pixels físicos
e diagnóstico de desenho separado do estado de dados. Sem hook, injetor, acesso
à memória do jogo, Game Bar, Overwolf ou Electron. A janela externa destina-se a
janela/sem bordas; não prometer tela cheia exclusiva nem mudar opções do jogo.

Contratos: DLL C ABI recebe HWND pertencente ao próprio processo e textos de
apresentação limitados, retorna HRESULT, libera todos os objetos COM antes de
destruir a janela. Nenhum HTTP, arquivo de captura ou thread permanente nativa.
Build usa MSVC/Windows SDK instalados no runner; o empacotador audita o hash da
DLL compilada. Falha de criação/desenho aparece como falha, sem retornar ao GDI.
O runtime mantém um pequeno estado de espera em Arena/Mayhem sem publicar
ofertas ou métricas falsas; cartas confirmadas continuam sendo só as lidas.

Validar: pixels realmente compostos sobre outra janela, perda/recuperação de
z-order sem mudar dados, clique passando ao alvo, foco preservado, DPI/geometria,
atalhos/paginação, ocultação em alt-tab/expiração e liberação. Suíte de regressão,
Windows real descartável e pacote auditado; teste com LoL continua separado.

### Resultado da composição antes de empacotar

O [job Windows 39004397951](https://github.com/teuzimmmm/sexo2/actions/runs/39004397951),
código `e1afd6b82d9b4ec5b1ce8919ae495089285ae6db`, compilou a DLL e passou cinco
testes nativos. O teste de pixels lê a composição na área de trabalho, cobre-a
com outro topmost branco e verifica que ela volta sem novas pinturas/dados.
Também verifica passagem de hit-test, ausência de foco próprio, atalhos,
paginação, geometria de HWND real, ocultação e encerramento. Os testes de OCR
sintético continuaram passando. A primeira execução falhou numa suposição do
teste sobre hit-test de STATIC; corrigiu-se o teste e repetiu-se a rodada.

O runtime distingue projeção de dados de aviso de renderer. Perda/expiração do
LCU mantém apenas aviso estático, sem campeão ou métrica antiga, enquanto a
janela ainda exige o executável do jogo em primeiro plano. Desligar, sair da
partida ou parar continua ocultando/encerrando. Isso também permite diagnosticar
configurações do cliente que o fecham durante a partida; não é uma nova fonte de
estatísticas sem LCU. Não presume que essa foi a causa do relato do usuário.

O empacotamento 2.0.0.6 deve repetir os testes com a última revisão e exercitar a
DLL efetivamente instalada. Sucesso em HWND próprio não é prova de tela cheia
exclusiva, compatibilidade com Vanguard ou leitura de cartas reais. O laboratório
hudhook permanece separado e não foi promovido a injetor. Não foi medido consumo
comparativo com Blitz/U.GG; a composição só é repintada quando muda o conteúdo.

### Pacote final da rodada

A edição 2.0.0.6, commit `abc17e58d7b0f51556881b36a8081b953f6703f6`, passou no
[job Windows 39004586918](https://github.com/teuzimmmm/sexo2/actions/runs/39004586918):
501 testes gerais (oito ignorados), cinco testes nativos de composição e painel
em Chromium isolado. A DLL de produção foi auditada no pacote e a DLL instalada
foi carregada/desenhou em um HWND sintético. Instalação, reinstalação e
desinstalação passaram. Hashes e download estão em
[INSTALADOR_TESTE_2_0.md](INSTALADOR_TESTE_2_0.md#validação-windows--2006).
Otimização conferida: reafirmação de z-order sem repaint nem resize quando
conteúdo/posição não mudam. Foco/cliques e ciclo de vida passaram no teste
sintético. Não confundir isso com validação dentro de uma partida do LoL.

Situação atual: renderer DirectComposition integrado e pacote testável entregue;
pendentes confirmação em LoL janela/sem bordas, calibração de cartas reais, fonte
estatística Mayhem e medidas de consumo no programa completo. Tela cheia
exclusiva não faz parte do suporte confirmado. Nenhum hook/injetor foi integrado.

## Rodada 2.0.0.7

Uma superfície curta desenha três regiões separadas por transparência, na ordem
esquerda/centro/direita das ofertas reconhecidas. Arena usa apenas augment0 do
LoLalytics; Mayhem usa pools por campeão de aramkit via cache comunitário.
Não aproveitar hover para selecionar o campeão das estatísticas. O ouro de SR e
Swiftplay compara apenas inventários observados, com troca de oponente em F7.

Sete testes Windows de pixels/atalhos e carregamento da DLL instalada aprovados
no CI 39007544851. Geometria de cartas e visibilidade no LoL real continuam sem
validação de partida. Ver [matriz vigente](FUNCIONALIDADE_PARTIDAS.md).
