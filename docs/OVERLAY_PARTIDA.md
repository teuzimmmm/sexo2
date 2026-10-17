# Overlay de recomendações durante a partida

Plano registrado antes da implementação. O painel Pengu permanece na seleção;
a janela durante a partida é um componente Windows separado, no mesmo programa.

## Etapas e contratos

1. Guardar uma projeção limitada das sugestões realmente consultadas no draft,
   vinculada a uma chave derivada do gameId e ao modo. Capturar nomes do catálogo,
   filtros, patch, origem e escopos das métricas. Não guardar contas/credenciais.
2. Ler fase/sessão pelo transporte LCU existente, com timeouts e sem consultar
   LoLalytics durante a partida. Confirmar identidade/modo antes de mostrar.
   Falha de leitura oculta a janela; fim da partida e outro draft limpam os dados.
3. Criar janela nativa Win32/GDI em thread própria: sem ativação, fora da barra de
   tarefas, acima do jogo somente enquanto ele estiver em primeiro plano, com
   passagem dos cliques. F8 expande/recolhe, F9 alterna as sugestões preparadas,
   F10 percorre as páginas de texto. A barra compacta continua visível; a opção
   nas configurações desativa também a barra.
   Registrar os atalhos somente com a janela do jogo ativa e liberar ao sair.
   Não injetar DLL, ler memória do jogo ou instalar hooks de teclado.
   Usar somente os atalhos registrados no Windows enquanto o jogo estiver ativo.
4. Integrar criação/encerramento ao monitor existente. Uma falha do overlay não
   deve impedir skins, painel, importações ou o encerramento do aplicativo.
   Configuração persistente permite desativar o componente.
5. Testar projeção, identidade, troca/fim de partida, erros, nomes e ciclo de vida
   offline; executar smoke Win32 em Windows descartável e regressões pertinentes.
   Empacotar a próxima edição de teste com os módulos novos auditados.

## Conteúdo e limites

- Visualização somente leitura de runas e itens já preparados. Nenhuma importação
  durante a partida ou nova recomendação automática baseada no estado ao vivo.
- Manter separados conjuntos iniciais/core e alternativas individuais de itens;
  WR da runa principal não vira WR da página completa nem probabilidade de vitória.
- SR e ARAM padrão. Arena e variantes sem fonte confirmada não habilitam o overlay.
- Sem consulta preparada, mostrar aviso curto para preparar na seleção seguinte.
- Sem dados de jogadores ou adversários além dos campeões já escolhidos no draft.
- Janela externa funciona como destino em janela/sem bordas. Tela cheia exclusiva,
  compatibilidade com o cliente/jogo instalado e atalhos reais exigem teste nativo
  no LoL; o smoke Windows não comprova uma partida nem mede consumo comparado ao Blitz.

## Critérios de conclusão

Janela integrada, controle de configuração, dados da partida correta, descarte
seguro, encerramento limitado, erros isolados, testes reproduzíveis, código
revisado e commit. Diferenciar teste Windows da janela de validação no LoL real.
Migração e limpeza do Rose continuam na fase final.

## Implementação e reprodução

`sexo2/overlay/model.py` guarda a projeção em memória, sem arquivos ou rede.
`runtime.py` observa o LCU a cada dois segundos, oculta em erro/observação vencida
e limita a retenção a seis horas. `win32.py` cria/destrói janela, fonte, brush,
timer e atalhos na mesma thread. Sem Qt, Chromium ou dependência adicional.
O campeão observado pelo monitor existente também invalida uma preparação de
outro campeão, inclusive em uma troca tardia na passagem para a partida.
Falha na projeção ou na janela é isolada do coletor, painel e importador.

As sugestões mostram nomes do catálogo, patch, filtros, momento de coleta, risco,
amostra da runa principal, conjunto inicial/core e até três alternativas por
posição. Não truncar um conjunto observado para fingir uma combinação menor.
Quando há mais alternativas, o texto avisa que existem no conjunto importado.
F8 ocupado por outro aplicativo impede a exibição e produz aviso no log; os
atalhos são liberados ao alternar de janela ou encerrar. F9/F10 também podem
estar ocupados; seus registros são verificáveis no smoke nativo.

```sh
PYSTRAY_BACKEND=dummy python -m unittest tests.test_game_overlay tests.test_build_bridge tests.test_build_https tests.test_settings_service -q
node --test tests/test_settings_ui.cjs
SEXO2_TEST_BROWSER_PATH=/usr/bin/chromium node tests/browser_builds.cjs
```

No Windows descartável, com desktop disponível e sem o LoL:

```powershell
$env:SEXO2_TEST_NATIVE_OVERLAY = '1'
python -m unittest tests.test_overlay_win32 -v
```

O teste nativo confirma criação/pintura, estilos de passagem de cliques/sem foco,
expansão, troca, paginação, ocultação quando o jogo simulado perde primeiro plano
e encerramento. O retângulo do jogo é sintético; não comprova renderização no LoL,
tela cheia exclusiva, DPI em vários monitores ou uso real dos atalhos no jogo.
