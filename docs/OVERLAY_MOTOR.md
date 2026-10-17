# Substituição do motor do overlay

Investigação de 17/10/2026, após o usuário informar que a edição 2.0.0.4
também não exibiu o overlay. Este documento sucede a tentativa descrita em
[OVERLAY_CORRECOES.md](OVERLAY_CORRECOES.md). **Não há novo motor integrado
ou validado no LoL.** Não entregar novamente a janela anterior como correção.

## Restrições e situação

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
