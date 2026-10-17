# Matriz de entrega por modo — 17/10/2026

**Estado após o teste real da 2.0.0.7:** usuário relatou congelamento/fechamento no
carregamento e falha nas duas importações. Overlay suspenso em produção e seus
binários removidos da próxima edição; ouro/cartas **não estão disponíveis** nessa
edição de correção. A matriz abaixo registra o objetivo, não comprova entrega
funcional no jogo. Ver [correções do incidente](CORRECAO_TESTE_2_0_0_7.md).

Escopo atualizado explicitamente pelo usuário antes desta rodada.

| Modo | Seleção | Durante a partida | Itens |
| --- | --- | --- | --- |
| Normal / Ranked SR | Runas recomendadas; importação explícita | Comparação dos itens próprios contra um adversário, sem ouro guardado | Conjuntos importados disponíveis na loja |
| Swiftplay | Sem novo painel de seleção | Mesma comparação de inventários | Conjuntos compatíveis com o modo, sem fingir que Ranked é Swiftplay |
| Arena | Nenhum painel de seleção | Pick rate/jogos nas três opções efetivamente oferecidas | Não solicitado nesta matriz |
| ARAM Mayhem | Nenhum painel de seleção | Pick rate/jogos nas três opções efetivamente oferecidas | Conjuntos específicos do modo, quando houver fonte confirmada |
| ARAM normal | Nenhum painel de seleção | Sem comparação de ouro ou painel extra solicitado | Conjuntos de itens |

Ouro significa apenas estimativa do valor dos itens observados. Rota como
correspondência automática quando inequívoca; F7 permite selecionar outro inimigo.
A ordem manual do TAB não é exposta pela API local. Nenhum ouro disponível é lido.

## Rodadas e critérios

1. Fechar comparação de itens e recuperação do painel SR: backend, testes offline,
   TLS sintético, navegador e hotkeys Windows; versão visível nas configurações.
2. Investigar fontes Swiftplay/Mayhem acessíveis, métodos e campos; não substituir
   dados Mayhem por ARAM clássico/Arena. Se uma fonte não existir ou estiver
   bloqueada, registrar isso como requisito pendente, sem declará-lo concluído.
3. Separar apresentação das três métricas de oferta, preservar posição/troca/TTL,
   e integrar importação de itens sem exigir painel em ARAM/Mayhem/Swiftplay.
   Preparar/importar antes da partida sempre que o cliente permitir; a execução
   durante a partida não deve afirmar que importação tardia já aparece na loja
   sem validação. Conservar páginas pessoais e os limites de conjuntos do SEXO2.
4. Validar matriz por modo (incluindo exclusão de painel Arena/ARAM/Mayhem), fontes
   reais limitadas, regressões, pixels/atalhos e instalador no Windows. Janelas
   sintéticas não comprovam uma partida real nem geometria das cartas do jogo.
5. Entregar pacote de teste auditado e documentar precisamente o que funciona,
   o que foi testado e os bloqueios restantes. Sem release público ou push em main.

Permanece pendente diagnosticar no cliente do usuário por que nenhum painel SR
apareceu. A recuperação de eventos/contexto foi corrigida, mas a captura não
comprova qual loader/plugins estava ativo. Não sobrescrever Pengu externo sem
um diagnóstico de propriedade e autorização aplicável.

## Fontes adicionais confirmadas por HTTP nesta rodada

- LoLalytics Swiftplay: `/lol/ahri/swift/build/q-data.json?tier=emerald_plus&region=all`
  e `&patch=16.20`: HTTP 200; nav.mode `swift`, header.queue 480, patch 16.20,
  2958 jogos. Adicionar `&keystone=8112` retornou 404. Portanto, importar somente
  sugestões gerais do modo, sem afirmar condicionamento à runa. A sugestão Common
  trouxe `start.set=[0]`, correspondente à entrada vazia de `startSet`: omitir esse
  bloco como indisponível, não inventar um item zero.
- Mayhem: serviço público documentado por Sygnano/aram-mayhem-tracker (MIT), commit
  `7c28471bf5b511e545d8d1c38b63707157edb134`, fontes aramkit.
  `https://mayhemcache.drawyoursword.lol/v1/champion?champion=103`: HTTP 200,
  patch 16.20, dataDate 2026-10-16, doze pools por etapa e um arquétipo de itens AP.
- `/v1/pool?champion=103&rarity=silver|gold|prismatic` sem parâmetro stage: três
  HTTP 200, stage nulo, respectivamente 62/86/75 linhas. Exemplos de origem
  `champion`: IDs 1105/1373/1388, pickRate .0347/.1237/.0617 e amostras
  49701/177006/88350. Usar os agregados por campeão, converter fração para porcento
  e descartar fallback `global` como métrica daquele campeão. Não somar etapas.

O serviço documenta leitura anônima, limite sustentado de 1 req/s, Retry-After e
consulta individual por campeão. Não baixar seu dataset de todos os campeões.
A licença MIT do código não é declaração de licença dos dados; atribuir aramkit
via serviço comunitário e tratar endpoints como dependência externa não oficial.
Nenhuma autenticação, token administrativo ou contorno de bloqueio é usado.

Contratos novos: BuildPage aceita condicionamento `mode` para Swiftplay e
`archetype` para sugestões Mayhem sem runas. O core do serviço Mayhem pode ser
purchaseOrder ou apenas itemSet: tratá-lo como **grupo sugerido sem ordem**,
sem WR conjunta inventada. Conservar limites/propriedade de páginas do importador.

## Implementação e validação desta rodada

- `AutoItems` observa lobby/draft independentemente do painel e da opção de overlay.
  As duas escolhas locais de Swiftplay compartilham **dois** conjuntos gerenciados,
  não dois por campeão. Conjuntos pessoais são preservados; escrita requer contexto
  e conta inalterados e leitura posterior idêntica. Nenhuma runa é escrita automaticamente.
- Em SR, páginas WR/Common/matchups preparadas pelo usuário passam ao serviço de
  itens sem reconsulta/substituição por outro filtro. Sem preparação explícita,
  consulta padrão por campeão/rota e risco salvo. Em ARAM, fonte ARAM. Em Swift,
  summaries do próprio modo; em Mayhem, arquétipos aramkit. Arena não importa itens.
- O catálogo de itens é validado no LCU antes da escrita; item desconhecido bloqueia
  o conjunto inteiro. Não inferir substitutos. Importação tardia tenta o mesmo
  endpoint, mas leitura LCU confirmada não comprova atualização da loja já aberta.
- Oferta reconhecida gera três faixas, uma por posição, em uma única superfície
  DirectComposition curta com espaços transparentes. Não capturar tela inteira nem
  renderizar por frame do jogo. F8 recolhe; sem F9/F10/F7 no modo de três faixas.
  Troca de oferta, perda de foco, erro de OCR ou TTL oculta métricas antigas.
- Campeão das ofertas é confirmado pela seleção local final na sessão de partida;
  não usar hover de draft anterior. Mayhem nunca recebe fallback de Arena/ARAM.
- Reprodução adicional: `python scripts/validate_mode_sources.py --champion jinx --champion-id 222` (uma consulta Swift, uma Arena, três pools Mayhem e um campeão
  Mayhem; explícito, sem dataset completo). Jinx Swift retornou dois summaries com
  quatro blocos cada; Arena 214 aprimoramentos agregados; Mayhem 107 métricas por
  campeão e um arquétipo. Patch 16.20; Mayhem dataDate 2026-10-16. Fontes reais
  consultadas em 17/10/2026. Projeções/URLs/hashes em `tests/fixtures/modes/manifest.json`.
- `tests/test_mode_sources.py`, `test_auto_items.py`, `test_overlay_mayhem.py` cobrem
  corpos reais sanitizados, filtros, popularidade/fallback global, erros de esquema,
  expiração, troca de contexto, modo, importação sem painel, dois campeões e limites.
  O teste do navegador cobre exclusão em Arena/ARAM/Mayhem/Swift e recuperação SR.
- A suíte geral Linux tem uma importação histórica de `ctypes.windll` em
  `test_startup_policy` que exige Windows. Os checks pertinentes e a suíte completa
  Windows são a validação de destino; não apresentar o erro Linux como regressão
  solucionada ou esconder sua ocorrência.

Ainda exigem partida real: OCR/posição das cartas na interface atual de Arena e
Mayhem, visibilidade sobre LoL sem bordas, importação antes de abrir a loja e o
painel no Pengu efetivamente carregado no PC. Os testes Windows usam somente
janelas próprias; não equivalem a esses testes de jogo. Tela cheia exclusiva
não é garantida pelo compositor externo. Sem hooks no processo do LoL.

## Uso no pacote 2.0.0.7

- SR normal/competitivo: abrir **SEXO2 · Builds**, escolher WR/Common ou adversário
  após finalização, e usar **Importar runas**. Os conjuntos de itens são preparados
  automaticamente; o botão **Importar itens** permite confirmar manualmente as
  sugestões abertas. Não remover páginas pessoais para liberar espaço de runas.
- Na partida SR/Swiftplay: **F7** troca o oponente da comparação de inventários;
  **F8** recolhe/expande; **F9/F10** navegam sugestões/texto quando existem.
- ARAM/Mayhem: conjuntos são preparados sem abrir painel. Na loja, selecionar o
  conjunto **SEXO2**. Mayhem e Arena: manter o jogo sem bordas/em janela e em
  primeiro plano; o reconhecimento precisa de duas leituras consistentes da oferta.
- Configurações do SEXO2 mostram versão e estado da importação junto ao diagnóstico
  do overlay. A opção de desligar o overlay não desliga a preparação de itens.
- Coletor separado, sem importar para o cliente:
  `python -m lolalytics ahri --mode swift --builds --cache-dir /tmp/sexo2-swift-cache`.
  A CLI `lolalytics` continua sendo exclusivamente LoLalytics; Mayhem fica no
  adaptador próprio `sexo2.sources.mayhem.MayhemClient`, com `pools(103)` e
  `builds(103, 'ahri', 'Ahri')`. Fechar o cliente com `close()` ao terminar.

ARAM foi também reconsultado por HTTP em 17/10: Jinx, tier all, patch 16.20,
WR/Common com keystone 8008 e cinco blocos cada. Reprodução:
`Client().collect_builds(Query("jinx", mode="aram", tier="all"))`, fechando o
cliente ao terminar. Resultado sanitizado em `docs/lolalytics/modes-live-2026-10-17.json`.

## Pacote auditado — 2.0.0.7

CI privado [39007544851](https://github.com/teuzimmmm/sexo2/actions/runs/39007544851)
concluído com sucesso. Código `3042968326042f87661bd0ebbf69ac94a6298a88`.

- 533 testes gerais Windows (10 skips de checks nativos opt-in), seguidos de
  7 testes nativos executados explicitamente: pixels nas três faixas, transparência
  dos intervalos, F7, paginação, foco, clique através e recuperação de z-order.
- Chromium isolado: painel normal/ranked, antes da escolha, importação, erros,
  respostas atrasadas, recuperação sem evento e exclusão nos demais modos.
- Auditoria do frozen e de cada plugin; DLL/renderizador e helper OCR incluídos.
- Instalação/reinstalação/desinstalação; DLL **instalada** realmente carregada e
  desenhada em HWND sintético próprio; sentinelas de dados antigos preservadas.
- 526 testes compatíveis com Linux passaram (10 skips); o módulo histórico
  `test_startup_policy` foi excluído desse comando por exigir `ctypes.windll` e
  foi executado na suíte Windows. Dois testes Node das configurações passaram.
- **Não foi iniciada uma partida ou cliente real do LoL no CI.** As ressalvas
  de geometria, carregamento efetivo no Pengu do PC e loja em partida permanecem.

Artefato privado [12091312878](https://github.com/teuzimmmm/sexo2/actions/runs/39007544851/artifacts/12091312878),
retenção de sete dias. Executável `SEXO2-2.0.0.7-Teste-30429683.exe`, 61123942 bytes.
SHA-256: `3d29b581e9db38186f2d0488100325da0cc5942d8ebdde2b139d53ef70c08f73`.
Renderer: `da1949023d4d6585d8652de32d75104630554c351ec7780adaefa82175d2681b`; OCR: `1d2618ac7c1a811b249d4027a113bfe90ae182548188fc40ba456b4bb9275973`.

No cliente, a edição deve aparecer como **2.0.0.7 (teste)** nas configurações do
SEXO2. Esses resultados não sustentam uma promessa de overlay sobre tela cheia
exclusiva, nem confirmam a causa do painel ausente no computador do usuário.
