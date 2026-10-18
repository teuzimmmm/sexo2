# Decisões de arquitetura

Cada ADR traz a decisão, o motivo, as consequências e quando revisitar.

## ADR-1: o núcleo continua em Python
- **Motivo:** injeção, atualização, sala e biblioteca funcionam e têm testes. Os custos suspeitos são polling e trabalho redundante, não a linguagem.
- **Consequência:** o empacotamento continua com PyInstaller.
- **Revisitar:** se, depois das otimizações medidas (M6b), a CPU ociosa ou a RAM continuarem acima do limite D-108 por causa do interpretador.

## ADR-2: o assistente de seleção roda no Pengu
- **Motivo:** não cria processo; o ponto de entrada já existe (`ROSE-CustomWheel`: `createButton`, `attachToChampionSelect`, `handleChampionLocked`).
- **Consequência:** os seletores do cliente ficam centralizados num módulo, porque o cliente muda.
- **Revisitar:** se o espaço ou a estabilidade dos seletores impedirem informação essencial, comprovado no cliente real.

## ADR-3: dados e escritas no LCU só no Python
- **Motivo:** reaproveita `lolalytics/` (limites de requisição, cache, validação) e mantém um único escritor no LCU.
- **Consequência:** a ponte precisa responder com baixa latência; isso é medido no M7.

## ADR-4: proteção da ponte local (revisto no M1)
- **Fatos:**
  - WS e HTTP já recusam `Origin` não-loopback.
  - Navegadores sempre enviam `Origin` no WebSocket, mas o omitem em GET de mesma origem. É por aí que entra o DNS rebinding.
  - Quem conecta sem `Origin` é processo local do mesmo usuário, que já lê o lockfile do LCU.
- **Decisão:**
  - recusar `Host` que não seja `127.0.0.1`, `localhost` ou `[::1]`;
  - manter o filtro de `Origin`;
  - não adotar um token entregue aos plugins (D-201);
  - não direcionar as respostas agora, porque os plugins podem depender do broadcast.
- **Revisitar:** quando a ponte ganhar uma tabela de despacho (M6a) e houver teste de contrato por mensagem.

## ADR-5: tecnologia do overlay escolhida por experimento
- **Candidatos, do mais simples ao mais complexo:**
  1. janela Tk em camadas (`WS_EX_LAYERED|TRANSPARENT|TOPMOST|NOACTIVATE`);
  2. PySide6 no mesmo processo;
  3. sidecar nativo (Win32 + Direct2D).
- **Regra:** vence o mais simples que, em 3 repetições no Practice Tool:
  - não altere a média nem o 1% low do PresentMon além do ruído;
  - fique dentro de D-108;
  - tenha texto legível.
- WebView2 está fora (D-202).

## ADR-6: um único cliente WebSocket (M6b)
- **Motivo:** hoje há `websocket-client` (LCU) e `websockets` (ponte, sala).
- **Revisitar:** se a migração ameaçar a reconexão do LCU. Nesse caso, mantêm-se os dois, documentado.
