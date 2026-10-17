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
