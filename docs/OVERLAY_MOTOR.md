# Substituição do motor do overlay

Investigação de 17/10/2026, após o usuário informar que a edição 2.0.0.4
também não exibiu o overlay. Este documento sucede a tentativa descrita em
[OVERLAY_CORRECOES.md](OVERLAY_CORRECOES.md). **Não há novo motor implementado
ou validado no LoL.** Não entregar novamente a janela anterior como correção.

## Restrições e situação

- Overwolf foi explicitamente rejeitado. Não adicionar Electron.
- Game Bar foi proposta, mas o usuário perguntou sobre seu consumo; isso não
  representa aceitação nem rejeição definitiva. Não torná-la dependência agora.
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
| [XboxGameBarSamples](https://github.com/microsoft/XboxGameBarSamples/tree/bd53d41dce2590727bd393cbafe9425a7e0cb3ae) | Widget UWP/XAML no host Game Bar, sem exigir Electron | MIT dos exemplos; plataforma Microsoft separada | Alternativa condicionada à escolha do usuário e medição; não adotada |
| [hudhook](https://github.com/veeenu/hudhook/tree/72e1cc062c35df847b703e5507b82eb21d80d82c) | Rust/ImGui, hooks DirectX/OpenGL; `src/inject.rs` usa `OpenProcess`, `WriteProcessMemory` e `CreateRemoteThread` | MIT | Motor independente real, mas funcionamento no LoL/Vanguard não demonstrado; não instalar seu injetor no produto |
| [GOverlay](https://github.com/hiitiger/goverlay/tree/3ca1f040b180dc6ce84baca093c6f726748461ad) | Motor C++ com DLL dentro do jogo e comunicação com a UI; não exige necessariamente Electron | Arquivo LICENSE: GPLv3 com termos adicionais, incluindo atribuição clicável em cada tela | Não incorporar sem resolver obrigações da distribuição e compatibilidade com o jogo |
| [GameOverlay.Net](https://github.com/michel-pi/GameOverlay.Net/tree/b43c9d9a2dc3e3423b63732f279a357d8fb1f263) | Direct2D/SharpDX em janela externa transparente; repositório arquivado | MIT | Não selecionado: trocar GDI por Direct2D não comprova resolver a falha; há limitações documentadas de tela cheia |
| [Open League Overlay](https://github.com/bossNilac/Open-League-Overlay/tree/2bca5917ce7b249eaad6024be8a7d64090ec534a) | Projeto C++ específico para LoL; README declara janela externa e Live Client Data API, sem hooks | MIT | Referência para investigar, não prova independente de funcionamento no PC do usuário ou de suporte a tela cheia |

As referências são commits fixos, não dependências adicionadas. A revisão leu
README, licença e, no hudhook, o injetor. Nenhum desses motores foi compilado
ou executado neste ambiente. Para reproduzir a inspeção sem credenciais:

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
2. **Seleção pendente:** escolher um motor que respeite as restrições e tenha um
   caminho viável de validação. Game Bar continua sem aceitação; hooks genéricos
   não têm compatibilidade comprovada. Não gastar uma rodada completa de integração
   supondo que qualquer uma dessas opções resolverá o problema.
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
programa; validação real no LoL documentada; custos medidos em Windows. Esta
investigação atende somente à primeira etapa. O overlay continua pendente,
e nenhum instalador novo foi gerado nesta rodada.
