# Decisões e entrega r6

Este documento registra as entregas anteriores. Para a 2.0, a instalação própria
e a limpeza/migração do legado seguem [SEXO2_2_0.md](SEXO2_2_0.md); preservar uma
dependência permanente de `LocalAppData/Rose` não é mais o destino aprovado.

Nome aprovado: SEXO2. BORK é o símbolo, com máscara que herda cor e dimensões do
cliente LoL. Interface escura, compacta e com um único ponto de entrada na barra.

Painel: Skins, Perfis, Sala e Configurações. Os painéis existentes foram
incorporados, preservando mods, perfis, sorteio temático, exclusões, Swiftplay,
diagnóstico e configurações. Stop de emergência e encerramento continuam
disponíveis na bandeja; controles contextuais do cliente são preservados.

Seleção automática: desligada, favorita, aleatória e entre favoritas. Sem
favoritas elegíveis, usar aleatória disponível. Sem skin elegível, conservar a
seleção. Pode repetir. Escolha manual prevalece na seleção do campeão atual.

Sala: hospedagem no processo principal, sem VPN/porta aberta. Criar, entrar,
copiar link, encerrar, sair e reconectar também na seleção de campeões. Sala
encerrada precisa de novo link. Não prometer preparo de skins a tempo após uma
recuperação tardia; nunca alterar escolhas durante uma injeção ou partida.

Autoaceite: opt-in persistente, desligado por padrão. Só ReadyCheck ativa, sem
iniciar fila nem aceitar recusa; confirmação e tentativas limitadas. Não testado
em uma partida real.

Dados: schema 2, leitura de schema 1, cópia permanente antes da migração e backup
recente. Restauração preserva arquivo corrompido. Downloads temporários, verificação
de tamanho/CRC e substituição atômica. Instância única por mutex existente.

Instalação: dados em LocalAppData/Rose preservados; preflight de processos e
espaço, backup da instalação e tentativa de retorno após interrupção normal.
Backup/retorno ainda não exercitados numa instalação real. Queda abrupta pode
exigir retorno manual usando a cópia preservada.

Validação da entrega: 252 testes Python, 11 testes JavaScript, navegador com
painéis reais e LCU simulada, auditoria do bundle e túnel público com dois clientes
sintéticos. Sem partida, autoaceite ou instalação reais. Arena ainda pendente.

Git local: base r5 e mudanças em commits separados. Dependências de build
registradas; dados pessoais, logs, skins e binários fora do histórico. Sem remoto
GitHub até definir conta/nome/visibilidade. Usar branches para novas mudanças.

Identidade SEXO2: executavel e instalador com BORK azul espectral, criado pela
ferramenta integrada de imagens a partir do desenho aprovado, preservando a
silhueta e usando fundo transparente. Arte em assets/bork-blue.png e ICO em
assets/sexo2.ico. Dentro do cliente, a mascara continua herdando a cor nativa.
Entrega zipada em novo/SEXO2/SEXO2 - Instalador para compartilhar.zip.

## Correção SEXO2 r2 — 13/10/2026

- Editor independente em Skins > Favoritas: busca qualquer campeão no catálogo
  do cliente, lista suas skins/cromas e salva as marcações sem exigir uma partida.
- Marcações sucessivas são serializadas e mostradas enquanto aguardam confirmação.
- Configurações usam conteúdo próprio integrado, sem o quadro antigo do Rose.
  Textos recebem a marca SEXO2; autoria/links da base ficam em créditos separados.
- Ícones distintos: BORK azul mais encorpado sobre fundo escuro para o Windows
  (`assets/bork-desktop-v2.png` e `assets/sexo2-v2.ico`) e silhueta simplificada
  para máscara nativa (`assets/bork-hud-v2.png`). Atalhos usam o ICO novo.
- As duas artes foram criadas pela ferramenta integrada de imagens. Prompts:
  desktop: BORK compacto e espesso em azul/ciano sobre tile azul escuro, legível
  a 32/48px; HUD: BORK em silhueta branca sólida e espessa, fundo transparente,
  sem detalhes finos, para tingir pela cor do cliente a 20px.
- Versão Windows/instalador 1.4.7.9. Entrega em `novo/SEXO2-r2`.
- Verificados 116 testes Python da personalização, 11 JavaScript, navegação real
  dos plugins em Chromium com cliente simulado e correspondência dos módulos
  congelados/plugins ao código-fonte. ZIP conferido. Sem instalação automática
  nem nova partida real; aparência final no cliente real ainda depende da avaliação
  do usuário. Capturas de teste usam componentes do cliente simulados.
