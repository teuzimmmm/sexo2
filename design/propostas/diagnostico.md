# Diagnóstico UX — proposta, 18/10/2026

Escopo: leitura dos oito módulos em `replica-source/`, réplica estática e documentos remotos de `teuzimmmm/sexo2@galinacio`. Não é teste de usabilidade nem validação no cliente Windows. Novos nomes, organização e comportamentos abaixo estão **pendentes**, sem alterar decisões aprovadas.

| Evidência observada | Implicação e proposta |
|---|---|
| `ROSE-Hub.js:119–179`: lateral já existe, com Skins/Mods/Sala/Configurações/Diagnóstico. Skins contém quatro destinos. | A precisa melhorar hierarquia e continuidade; trocar topo por lateral não seria novidade real. |
| `ROSE-Hub.js:178–180` abre Preparo ao escolher Diagnóstico; `ROSE-Amigos.js:346–371` mistura autoaceite e prontidão. | Separar preferência de partida de resolução de falhas. Autoaceite em Seleção; prontidão em suporte. |
| `ROSE-Amigos.js:591–597`: gerar relatório e abrir pasta aparecem no rodapé comum; `SEXO2-Settings.js:174–182` repete diagnóstico e biblioteca. | Concentrar diagnóstico, erros e caminhos em suporte único. Atalhos contextuais levam ao mesmo destino e preservam contexto. |
| `ROSE-Amigos.js:372–422`: perfil é conjunto por campeão, não identidade de usuário; `423–451`: entrar no sorteio desliga perfil. | Mostrar conjunto ativo, escolhas e efeito antes de ativar. Separar sorteio pessoal e coordenado, explicitar conflito com perfil. Não inventar restauração automática. |
| `SEXO2-Settings.js:91–138`: campos operacionais, overlays, pasta, idioma e salvar ficam juntos; idioma salva imediatamente. | Agrupar por tarefa e mostrar alcance da alteração; resolver diferença entre edição pendente e imediata. Configuração completa continua acessível. |
| `SEXO2-Assistant.js:337–438,450–486`: recomendações, editor e outros trios já existem; cards importam runas. | Preservar clique com efeito real D-015. Não adicionar confirmação intermediária nem representar trio observado como build completa de seis itens. |
| `SEXO2-ModLibrary.js:269–300`: importação pode exigir campeão/skin-base ou aguardar fim da seleção. | Biblioteca cuida dos arquivos; champselect só aplica opções compatíveis e comunica indisponibilidade. |

Cobertura: Hub, skins/favoritas/cromas, perfis, automático, sorteio, sala, biblioteca/importações, configurações, diagnóstico, assistente/runas/itens, categorias legadas de custom mods e overlays. Inventário factual auxiliar: réplica `index.html:3043–3071,4074–4145,4333–4734` mantém categorias skins/mapas/fontes/anunciadores/interface/voz/carregamento/VFX/SFX/outros; não devem desaparecer por simplificação visual.

Limites: README da réplica declara dados fictícios, memória volátil, rede bloqueada, Hub 820×560 e assistente 452×492; overlays HTML/SVG aproximados, sem OCR/FPS/cliques reais. Auditoria estrutural por código, sem nova inspeção visual no LoL. AGENTS.md remoto retornou 404; AGENTS.md local foi lido. CLAUDE, decisões, glossário, tokens e wireframes remotos foram lidos. Skill `sexo2-ui` aplicada; UI UX Pro Max lida como referência, sem consulta externa de recomendações nem geração de design system.
