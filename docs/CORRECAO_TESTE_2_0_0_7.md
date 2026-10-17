# Falhas reais relatadas após 2.0.0.7 — 17/10/2026

O usuário relatou: overlay quebrou o LoL; nenhuma importação de runas/itens
funcionou; resíduos visuais do Rose; acesso a builds fora do padrão visual e
fora do lugar de Mods. Relato real prevalece sobre os checks sintéticos anteriores.
O renderer entregue continuava sendo janela externa DirectComposition; a versão
nova alterou dados/apresentação, não substituiu essa arquitetura. Não chamar essa
alteração de um novo motor funcional comprovado no LoL.

Plano antes de alterar implementação:
1. Desativar e impedir criação automática do renderer/OCR problemático em produção,
   inclusive quando existe preferência antiga true. Manter importação independente.
2. Conferir contratos LCU atuais e causas concretas de falha: conta, catálogos,
   limites de runas, corpos JSON, comparação de leitura, erros e versão do plugin.
   Adicionar reprodução do problema confirmado antes da correção. Não presumir que
   timeout ou exemplos fictícios descrevem o erro do computador do usuário.
3. Substituir o ponto visual Mods por Runas/Itens em SR normal/competitivo, usando
   o componente/estilo do cliente. Manter acesso às funções de mods em local próprio;
   não adicionar outro botão flutuante. Excluir ARAM/Mayhem/Arena desse painel.
4. Remover resíduos de identidade visíveis (textos, popups e imagens) em caminhos
   realmente usados. Identificadores internos e limpeza de instalações antigas são
   assuntos separados; migração destrutiva permanece na fase final acordada.
5. Testes de regressão, navegador e contratos atuais; revisar o pacote. Sem novas
   promessas de funcionamento no jogo apoiadas apenas por HWND sintético. Um novo
   overlay exige diagnóstico do incidente e validação real antes de ativação.

Critérios: nenhum renderer/helper OCR inicia em produção; runas/itens têm erros
compreensíveis e tratamento dos contratos reais; UI usa o espaço e aparência
pedidos; branding próprio nos fluxos executados; evidências e limitações explícitas.

Detalhe do relato: jogo congelou e depois fechou; ambas as importações exibiram
mensagem genérica de falha. Sem logs locais disponíveis para atribuir a causa.


O usuário localizou o congelamento no **carregamento**, antes de jogar. O caminho
legado de skins suspende explicitamente o processo do jogo enquanto prepara mods;
é um segundo mecanismo a investigar. Sem logs de execução não se pode dizer qual
mecanismo causou o fechamento. Nenhuma outra suspensão foi adicionada.

Descobertas reproduzidas:
- Catálogos CommunityDragon atuais perkstyles/perks/items: HTTP 200, schemaVersion
  2, sete slots por estilo. As duas páginas reais de amostra geram IDs válidos.
- Na implementação anterior, primeira importação de runas sempre fazia POST, mesmo
  com o limite da conta ocupado. Fluxo novo permite escolher página editável e faz
  PUT nela; backup local limitado, sem apagar páginas. Escolha explícita no painel.
- Schema LCU arquivado (https://www.mingweisamuel.com/lcu-schema/lcu/openapi.json)
  descreve defaults opcionais `startedFrom`, `showIfSummonerSpell` e
  `hideIfSummonerSpell`. Comparação anterior exigia igualdade integral após PUT.
  Nova confirmação normaliza apenas esses defaults e a ordem dos conjuntos;
  continua comparando blocos, ordem dos itens, quantidades, mapas, campeões e dados
  pessoais existentes. Mudanças reais/UIDs duplicados continuam sendo falha.
- O mesmo schema documenta PUT /lol-perks/v1/currentpage com ID inteiro. Quando
  salvar uma página não a torna atual, selecionar explicitamente e reler.
  Este schema é arquivado e avisa que pode estar desatualizado: observação de
  contrato, não prova de execução contra o cliente atual do usuário.

Implementação da edição 2.0.0.8:
- Inicialização padrão mantém apenas o observador/importador de itens. Não importa
  ou cria NativeOverlay/Composition/OfferReader e recusa a prévia. Preferências
  antigas true não reativam esse caminho. DLL/OCR ausentes do pacote; remoção dos
  dois nomes exatos ao reinstalar o programa de teste, validando propriedade do
  destino e ausência de links/junctions. Nenhuma limpeza de AppData/Rose.
- Runas/Itens usa `lol-uikit-flat-button` no `.bottom-right-buttons`, mesmo espaço
  de Mods. O botão anterior fica oculto apenas em SR compatível; acesso a mods
  continua no flyout. Filtros avançados recolhidos e seletor de página nativa.
- Ao aplicar em página existente: valida ID/editabilidade/conta/contexto, guarda
  backup privado limitado e faz PUT. Se o cliente não a marcou atual, usa endpoint
  de seleção e relê. Sem apagar páginas. A opção de criar página nova continua
  explícita e requer espaço. Não trocar destino escolhido em polls do contexto.
- Normalização de defaults na confirmação dos itens sem descartar mudanças de
  conteúdo. Erros HTTP estáticos atravessam importador/bridge; nunca retornar
  corpo do erro, URL ou credenciais. Nenhuma repetição automática de escrita.
- Resíduos visíveis tratados em traduções/diálogos próprios e badges da tela do
  Pengu. Créditos/licenças da base preservados, variáveis pessoais não renomeadas.
  Identificadores internos, mutex e caminhos de dados compatíveis continuam para
  a migração final; não afirmar que a desvinculação do Rose foi concluída.

Limites: sem LoL real neste ambiente, sem logs do PC nem reprodução do crash.
A janela externa anterior foi retirada, não consertada/rebatizada como novo motor.
Comparação de ouro e PR nas cartas ficam pendentes. Testes de contrato/UI e pacote
não autorizam afirmar que importações ou estabilidade já foram validadas no jogo.

Revisão adicional do fluxo: abrir antes de escolher campeão não fornece páginas
ao frontend. Só uma mudança feita pelo usuário fixa o destino; o primeiro contexto
com páginas escolhe a editável atual. Regressão Chromium remove `runePages` do
contexto pré-pick para testar a transição real de ausência para disponibilidade.
Opção vazia é “Página gerenciada SEXO2”, não promessa de criar uma página nova.

Etapa adicional justificada pela revisão de inicialização: `activate_on_start`
adota um Pengu externo com ROSE-UI/ROSE-SkinMonitor e retorna antes de atualizar
plugins. Assim, um executável novo pode manter frontend antigo mesmo com pacote
correto. Corrigir atualização somente de entrypoints conhecidos do projeto, com
prova por hash histórico, preservando plugins alterados, datastore, core/EXE e
Registro do loader externo. Sem cópia genérica de pastas; reinício apenas na fase
segura já usada pelo aplicativo. Não afirmar que esse foi o caminho no PC sem
inventário/logs. Fixtures de teste só usam scripts públicos e diretórios temporários.

Atualização externa implementada: manifesto de SHA-256 dos entrypoints públicos
atual/históricos, preflight de todos os scripts, backup limitado aos conteúdos
reconhecidos e substituição atômica com rollback em erro. Plugins desativados
permanecem desativados. Core, EXE, datastore, plugins particulares e Registro
externos não são copiados nem substituídos. Alterações próprias desconhecidas
bloqueiam a atualização com erro; não declarar atualização concluída nesse caso.
O reinício usa somente o fluxo LCU existente, fora da partida e do draft.

Validação local adicional: 13 testes focados de sincronização/importação passaram;
cobrem rollback após falha de escrita, script particular, symlink, manifesto
malformado, preservação do datastore e idempotência. O manifesto é auditado no
pacote e testado contra os scripts efetivamente entregues. Isso não reproduz
a instalação do Pengu no PC do usuário.

CI 39043855589: 549 testes gerais passaram; a regressão de retomada do processo
sintético falhou ao encontrar zero processos parados. O teste suspendia Python
logo após Popen, sem esperar a inicialização nem verificar a pré-condição.
Agora há sinal de prontidão e espera limitada pelo estado parado. Nenhuma mudança
no mecanismo de suspensão do jogo decorre desse ajuste; falha persistente deve
continuar bloqueando o pacote.
