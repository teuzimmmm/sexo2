# SEXO2 — checkpoint de continuidade

Data: 18/10/2026. Execução interrompida por solicitação do usuário para economizar contexto.
Próximo ciclo: produzir/completar e validar os protótipos; não repetir pesquisa.
Tudo abaixo é proposta pendente, sem alterar decisões oficiais ou produção.

## Descobertas úteis
- O Hub já possui lateral: adicionar uma lateral não constitui nova arquitetura.
- Diagnóstico abre Preparo; autoaceite e prontidão estão misturados.
- Configurações e rodapés repetem diagnóstico, biblioteca e abrir pasta.
- Centralizar resolução de problemas; biblioteca continua dona de importação/exportação.
- Perfis são conjuntos por campeão; sorteio coordenado desliga perfil. Explicitar o conflito.
- Campos operacionais e preferências estão misturados; há salvamento imediato e pendente.
- Custom mods exigem compatibilidade de campeão/skin-base e às vezes aguardam seleção terminar.
- Outras builds são trios observados de itens, não builds completas de seis itens.
- Evidências de código e documentos consultados estão em diagnostico.md; não refazer inventário.

## Arquiteturas decididas para experimentar
- A: evolução do Hub, lateral por recurso: Skins, Mods, Sala, Configurações, Suporte.
- A: reduzir redundância, manter coleção/favoritas e reunir suporte/pastas/diagnóstico.
- B: entrada por atividade: Preparar partida, Personalizar coleção, Resolver problema.
- B: workspace com retorno; preparo dividido em Antes da fila, Na seleção, Em jogo.
- Configurações rápidas no champselect e acesso às completas, preservando retorno/contexto.
- Preferência de fonte no uso habitual; comparação simultânea sob demanda.
- Onetricks é integração futura simulada; amostras e WR não devem ser mesclados.
- Ponderação futura: elegibilidade antes do ranking; Exalted+croma que desativa CTRL5 excluído.
- Arena Bravura: revelar antes de selecionar automaticamente; não implementar algoritmo.
- Recomendação provisória: A incremental; B experimento comparativo, sem usabilidade medida.
- Especificação detalhada curta: arquitetura.md; tradeoffs/dependências: comparacao.md.

## Arquivos preservados
- diagnostico.md, arquitetura.md, comparacao.md.
- sexo2-ux-a/index.html: primeira implementação navegável; validação de interação pendente.
- sexo2-ux-b/index.html: primeira implementação por atividades; validação pendente.
- sexo2-shared/: imagens/fontes extraídas da réplica; recursos locais compartilhados.
- sexo2-overlays/index.html: três modos Blitz/A/B, cenário misto/empate/indisponível e fonte.
- sexo2-overlays/blitz-reference.webp: referência oficial inspecionada visualmente.
- Referência: https://blitz-cdn.blitz.gg/blitz/ui/img/settings/lol-itemdifference-minv3.webp
- Reprodução conserva faixa, moldura, losango, seta e diferença inferior; não é pixel a pixel.
- Réplica original sexo2-replica/ preservada; não reconstruir.

## Verificações e pendências
- Sintaxe dos scripts inline A/B/overlays passou em compilação JS (node:vm).
- Nenhum percurso de interação nem responsividade foi validado no navegador.
- Navegador de teste recusou file:// por política de protocolos; não contornar bloqueio.
- Confirmar abertura offline no Mac e integridade de todos os recursos relativos.
- Testar navegação/retorno, favoritos, mods, sala, preferências, fontes, runas e trios.
- Conferir aderência entre implementação e arquitetura: o HTML atual não garante todos contratos.
- Validar configurações completas/contextuais, cenários de falha e teclado/foco de modais.
- Revisar A/B em 1280×720 e assistente compacto; corrigir uma rodada de problemas relevantes.
- Revisar alinhamento/legibilidade dos três overlays e comparar Inter/Oswald com a referência.
- Validar rótulos futuros e não alegar integração real, algoritmo ou teste no Windows.
- Checar links entre protótipos/overlays e registrar resultados efetivamente executados.
- Manter toda edição em design/propostas/; não tocar produção, main, sexoatividade ou réplica.

## Estado do repositório
- Branch de destino exclusiva: galinacio; base remota inicial 4c43d09595dd4ebfcd127d649c7d5857202b5110.
- sexoatividade estava em aa558147cc7db74daae6b4c12ce7f5623dcc7739: nenhuma novidade para incorporar.
- Workspace é cópia de arquivos sem .git; registro do checkpoint via API GitHub, preservando árvore-base.
- API de blobs binários não concluiu a primeira chamada; recursos preservados em UX-RESOURCES.zip.b64.
- No checkout remoto, restaurar antes de abrir HTML: na pasta design/propostas, executar o comando abaixo.
- `python3 -c "import base64,io,zipfile; zipfile.ZipFile(io.BytesIO(base64.b64decode(open('UX-RESOURCES.zip.b64','rb').read()))).extractall('.')"`
- Localmente os recursos já estão extraídos; o arquivo codificado guarda imagens e fontes sem perda.
- Dois gestores GPT-6.1 Sol Medium e Low para inventário/A/B foram usados; High não foi consultado.
- Após o commit deste checkpoint, parar. A próxima execução retoma os arquivos, não a pesquisa.

## Atualização v2
- Base `5bfea7a` (galinacio). Recursos restaurados do ZIP (idênticos) em `sexo2-shared/` e `blitz-reference.webp`.
- Entregas: `sexo2-ux-a`, `sexo2-ux-b`, `sexo2-overlays` (index, QA, PROGRESSO, evidencias). Painel em `sexo2-operacao/`.
- Verificação: Chromium headless por file:// com CDP (A 95 checagens, B 130, overlays 47 em Firefox headless/Marionette). Sem Windows, cliente LoL, partida real, FPS, Safari ou leitor de tela.
- Limitações abertas: overlays a 452×492 rola dentro do palco; A a 820×560 exige rolar para ver o botão SEXO2; seletor de fonte do overlay ainda lista Arial; recorte da comparação com a imagem aprovada estimado a olho.
- Visual anterior rejeitado; referência aprovada: `sexo2-operacao/overlay-aprovado.png`. Nenhuma recomendação é aprovação de produto.
