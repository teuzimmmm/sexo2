# Overlay isolado — contrato de 17/10/2026

Pedido atual: retomar até obter funcionalidade; Blitz deixou de ser requisito.
O incidente real foi congelamento/fechamento no carregamento. Sem logs do PC,
não atribuir a causa ao renderer nem modificar skins por suposição.

Plano antes da implementação:
1. Substituir a DLL DirectComposition dentro do SEXO2 por processo auxiliar
   Python/Win32, com bitmap alpha via UpdateLayeredWindow. Sem GPU própria,
   Electron, Game Bar, Overwolf, hooks ou acesso à memória do jogo.
2. A janela externa continua limitada a janela/sem bordas. O novo isolamento
   não comprova tela cheia exclusiva. Não repetir promessa de compatibilidade
   universal nem chamar um teste sintético de partida validada.
3. Nenhum filho renderer ou OCR durante ChampSelect/GameStart/carregamento:
   exigir API Live Client local respondendo com gameTime > 0, além do contexto
   do modo. Falha desse sinal esconde e pausa os dados.
4. Reaproveitar fontes verificadas de inventário e ofertas reconhecidas. Mostrar
   comparação de valor dos itens em SR/Swiftplay; Arena/Mayhem somente pick rate
   das três ofertas, preservando ordem e expiração. Nada de WR restrita.
5. Pipe privado JSON Lines v2, até 256 KiB, sequência crescente, validade até 2s;
   somente texto e flags de apresentação, sem conta, credencial ou resposta bruta.
   Entrada inválida, EOF e expiração ocultam. Sem portas ou captura em disco.
6. O pai transmite o frame mais recente por uma thread; pipe bloqueado ou filho
   encerrado não bloqueia observação/importação. Watchdog mata apenas seu filho,
   retentativas no máximo duas por partida, diagnóstico estático e encerramento
   limitado. O filho não importa inicialização, skins ou configuração do app.
7. Testes offline do protocolo/supervisor/carregamento e Windows de pixels,
   alpha, foco, click-through, z-order, expiração e crash do auxiliar. Só depois
   gerar edição de teste 2.0.0.9 com auditoria do pacote instalado.

Critérios: importações/skins não dependem do filho; nenhuma DLL antiga carregada;
nenhuma janela/helper inicia no carregamento; dados antigos ocultos; erro de
renderização visível no diagnóstico; pacote testado em Windows. Compatibilidade
no LoL e geometria das cartas reais continuam dependentes de execução real.
Não alterar a main contendo a API nem publicar release. Usar branch privada de
experimentos e instalador de teste já autorizados.

Continuidade sem frontend: guardar em memória apenas modo/fila/mapa e chave
anônima de uma sessão já validada. Se o LCU cair, reutilizar esse contexto somente
enquanto a API do jogo continuar renovando um relógio crescente. Gap maior que
8s, reinício do relógio, modo desconhecido ou saída confirmada invalidam a ponte.
Não guardar roster, conta ou credenciais nem reutilizar contexto de outra partida.

Primeira rodada Windows (39044967272): testes reais de pixels/click-through,
foco, z-order, TAB, processos e protocolo passaram. A execução do auxiliar
compilado sem console não respondeu pelo pipe; empacotamento bloqueado. Adicionado
tratamento estático para impedir diálogo modal de exceção do bootloader e obter
a classe do erro pelo pipe privado; a rodada deve ser repetida.

Revisão de integração: campeão do gameflow/LCU permanece autoritativo para Arena;
não usar hover como fallback. A suíte completa flagrou essa regressão e a mudança
foi revertida. O laboratório gráfico roda somente protocolo/processos/janelas;
os testes de continuidade LCU usam as dependências completas no CI do aplicativo.
O probe windowed passa --paths . explicitamente: a análise anterior não coletou
os módulos do renderer/Pillow; a entrada também agora captura falhas de import
sem abrir diálogo modal. O pacote final deve repetir o probe no SEXO2 instalado.

A validade do pipe usa relógio monotônico compartilhado entre processos, não o
momento tardio da leitura. Frames guardam a expiração original das ofertas e dos
inventários; inicialização lenta não renova dados antigos. O início do auxiliar
tem até 8s de tolerância; depois do primeiro diagnóstico, escrita travada tem
limite de 1s. A tolerância inicial nunca estende a validade de uma métrica.

O pacote novo também exclui os módulos Python win32/composition legados, além
da DLL antiga. A auditoria verifica sua ausência no PYZ. A prévia fora de partida
permanece apenas como seam de laboratório; a produção não informa aceite de
uma prévia que não poderia mostrar durante o carregamento.

## Validação do auxiliar — 39045921708

Commit 55e4b53142d9ce123dfdab59a48be10c490a99cc: job Windows aprovado.
Passaram pixels reais em janelas próprias, regiões transparentes, passagem de
cliques, foco, z-order, TAB, expiração e falhas reais de processos/pipes.
O entrypoint de laboratório foi movido para fora da raiz que contém __init__.py;
a auditoria do PYZ confirma renderer e Pillow e o executável --windowed respondeu
pelo pipe e encerrou por EOF. Isso resolve a falha de empacotamento do laboratório.
Não houve LoL/Vanguard nessa validação.

A edição 2.0.0.9 deve repetir testes gráficos/OCR, todas as regressões e verificar
o mesmo modo worker do SEXO2 efetivamente instalado. A instalação deve excluir
DLL/módulos legados, incluir o OCR compilado/notices e preservar os dados antigos.

Verificação final reforçada: o probe espera um estado posterior a not-started,
com a superfície inicializada, antes de aceitar o worker. Como só muda o script
de validação, revalidar o artefato já compilado em um job separado evita recompilar
o mesmo programa e o OCR. Esse job baixa somente um run numérico deste repositório,
confere SHA-256 e recibo/commit e repete instalação, worker e desinstalação.
Nenhuma mudança no runtime requer novo binário nesta etapa.

## Pacote validado — 2.0.0.9

Programa compilado de `30334790675d64de4d950a798cb157714ead5e75` no
[CI 39046087887](https://github.com/teuzimmmm/sexo2/actions/runs/39046087887).
Passaram 566 testes gerais (18 ignorados), 28 regressões do mecanismo de skins
e traduções, testes Node/Chromium, 19 testes de protocolo/gráficos/OCR reais em
Windows, auditoria do PYZ/assets e instalação/reinstalação/desinstalação.
A DLL e os módulos Python do renderer antigo estão ausentes.

O [CI 39046631608](https://github.com/teuzimmmm/sexo2/actions/runs/39046631608),
com o probe reforçado em d053aaf, baixou esse mesmo artefato, conferiu SHA-256 e
commit, reinstalou e comprovou `windowInitialized: true`, pipe privado e saída
por EOF no SEXO2 efetivamente instalado. Depois desinstalou e conferiu sentinelas
do legado. Não houve reconstrução ou mudança de runtime entre as verificações.

[Download privado do pacote](https://github.com/teuzimmmm/sexo2/actions/runs/39046087887/artifacts/12105602826)

- Instalador: `SEXO2-2.0.0.9-Teste-30334790.exe`
- SHA-256: `61d4ea7b8d55b37be29ad7b18051a0110a3ca18b25c6604dd72e42ba37dfe1d0`
- OCR SHA-256: `87b0c80110bcff5b353059559baad191301ed99b49253822ad7cb7e5479d092c`
- Motor: Win32 CPU em processo separado; sem a DLL antiga.
- LoL real: **não validado** (`nativeLeagueValidation=false`).

Uso: abrir a edição 2.0.0.9, habilitar “Overlay durante a partida” nas
Configurações e usar janela/sem bordas. TAB exibe a comparação de valor dos itens;
F7 troca adversário, com correspondência automática por rota somente quando
inequívoca. F8 recolhe/expande; F9/F10 alternam cartões/páginas de detalhes.
Arena/Mayhem relacionam métricas apenas às ofertas reconhecidas; OCR/idioma e
geometria de cartas reais ainda dependem de validação na partida.

Não foi reproduzido o fechamento do LoL relatado no carregamento. O renderer
novo não inicia nessa fase e é isolado do processo principal; o mecanismo de
skins foi preservado e teve regressões sintéticas, sem certificação de partida.
Tela cheia exclusiva e comparação de RAM com outros aplicativos não foram
comprovadas. Não anunciar a edição como correção do crash confirmada no LoL.
