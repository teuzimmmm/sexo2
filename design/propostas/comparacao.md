# Comparação e recomendação — proposta pendente

| Critério | A: Hub evoluído | B: atividades |
|---|---|---|
| Modelo | Destinos estáveis por recurso, lateral existente reorganizada | Entrada por objetivo, workspace e etapas de preparo |
| Encontrar recurso conhecido | Direto; baixo reaprendizado | Exige reconhecer a atividade correspondente |
| Preparar uma partida | Navega entre skins, sala e preferências | Uma jornada reúne decisões e contexto |
| Manutenção | Menor mudança de composição/eventos | Maior trabalho de estado, retorno, rascunhos e contexto compartilhado |
| Risco | Continuar fragmentando sem hierarquia clara | Esconder administração em atividades ou duplicar recursos entre etapas |
| Custom mods | Biblioteca evidente e painel contextual separado | Coleção unificada exige distinção clara entre arquivo e aplicação |
| Janela compacta | Ajustes incrementais no Hub | Workspace requer validação maior de densidade/rolagem |
| Custo relativo | Baixo a médio, sem estimativa em dias | Médio a alto, sem propor reescrever núcleo |

Recomendação: A como caminho incremental para produção; B como experimento realmente distinto para comparar preparo e descoberta. Não chamar B de vencedora sem observar usuários executando os mesmos percursos. Ambas podem usar o mesmo núcleo Python/ponte e componentes, sem Electron ou serviço novo.

Escolha sobre configurações: configuração completa fora do fluxo rápido e controles contextuais no champselect. Oferecer as duas atende administração e pressão de tempo; colocar tudo no assistente agrava densidade, oferecer só contexto oculta opções.

Escolha sobre fontes: preferência para uso habitual, comparação simultânea sob demanda. Onetricks é futuro simulado. Mostrar duas fontes sempre aumenta volume e induz falsa equivalência; mostrar só uma impede comparação. Não mesclar amostras/WR nem mudar importação implicitamente.

## Dependências para Claude e aprovação

1. Validar produto: navegação D-104, destino de mods D-105, textos D-107, conjuntos/perfis e conflito do sorteio. Manter mudanças como pendentes até aprovação; não editar registro oficial nesta proposta.
2. Mapear contratos reais de prontidão, erros, pastas e importação. Unificar entrada de suporte sem trocar chaves de sala, paths de dados, mensagens da ponte ou recuperação.
3. Especificar provedor Onetricks, cache/patch/amostra e indisponibilidade no Python; compatibilizar apresentação de fonte com D-008/016. A proposta não adiciona integração.
4. Definir algoritmo ponderado, elegibilidade Exalted/CTRL5 e metadados de cromas antes de qualquer implementação; sem score simulado apresentado como cálculo real.
5. Definir o contrato de Arena Bravura e sua revelação, separado de OCR/aprimoramentos; dados de Arena/Mayhem não se misturam.
6. Antes de produção, testes dos comportamentos tocados e checks de CLAUDE; depois validar cliente Windows, ancoragem real, teclado, viewport e overlays. Nenhum desempenho ou ganho de cliques foi medido aqui.

Base consultada: `teuzimmmm/sexo2@galinacio` — CLAUDE.md; docs/produto/decisoes.md (inclui D-120 e D-118 obsoleta), glossario.md; design/tokens.css; design/wireframes.md; .claude/skills/sexo2-ui/SKILL.md. AGENTS.md remoto: 404. Evidências locais e limitações em `diagnostico.md`.

## Rodada v2 (Claude A/B/overlays) — rejeição visual e referência aprovada

- O usuário rejeitou a direção visual dos HTMLs anteriores (rascunhos de comportamento). A v2 corrige só a identidade: base neutra `#0d0e10/#15171a/#22252a/#2a2d32/#ececec`, Oswald (títulos) + Inter (texto), WOFF2 locais, sem serifa e sem azul na interface.
- Exceção aprovada: `sexo2-operacao/overlay-aprovado.png` = modo B de `sexo2-overlays/index.html#b` (padrão inicial). Blitz e Original A seguem como estudos secundários, não aprovados.
- A organiza por recurso (Skins, Mods, Sala, Configurações, Suporte); B por atividade (Preparar partida, Personalizar coleção, Resolver problema). Evidências: `QA.md` e `evidencias/` de cada pasta.
- Nada aqui é aprovação de produto; dados, Onetricks, Bravura, sala e importações são simulações.
