# Arquiteturas A e B — propostas pendentes

Preservar Oswald/Inter, componentes e painel compacto aprovados (D-007/014/017), importação de runas D-015, itens D-018/019/120 e overlays D-009/020/117/119. Nomes novos neste documento são rótulos de proposta.

## A — evolução do Hub

| Navegação lateral | Conteúdo |
|---|---|
| Skins | Coleção/favoritas/cromas; automático; conjuntos salvos (Perfis); sorteio pessoal. Escolha manual preservada e estado do conjunto ativo visíveis. |
| Mods | Biblioteca, categorias existentes, busca, importar em lote, revisar campeão/skin-base, editar, remover, exportar. |
| Sala | Criar/conectar/copiar/sair/reconectar; participantes, prontidão e sorteio coordenado. Não criar uma segunda tela de sorteio de grupo. |
| Configurações | Geral: início/idioma/atualizações; Seleção: autoaceite e preferências; Overlays: ouro/aprimoramentos. Tempos e pasta em seção avançada; acesso ao suporte. |
| Suporte | Prontidão, erros, repetir verificação, diagnóstico sem chave e acesso organizado às pastas. Um destino, atalhos contextuais; Biblioteca continua dona das ações de importação/exportação. |

## B — workspace por atividade

Entrada apresenta três atividades; não reaproveita uma lista lateral das telas A. Após escolher atividade, o workspace mantém retorno à entrada e o contexto atual.

| Atividade | Organização interna |
|---|---|
| Preparar partida | Etapas Antes da fila → Na seleção → Em jogo. Resumo do conjunto ativo; autoaceite e sala antes da fila; campeão/skin/runas/trio na seleção; prévia e preferências de overlays em jogo. Sala e sorteio coordenado são contexto do preparo. Etapas são navegação demonstrativa, sem novo automatismo de produção. |
| Personalizar coleção | Navegador por campeão/conjunto/categoria, detalhe editável ao lado. Reúne skins/cromas/favoritas/perfis e arquivos de mods. Criar conjunto parte das escolhas visíveis; aplicar mostra o estado resultante. |
| Resolver problema | Mesmo suporte central da A, com retorno à atividade de origem e falha já contextualizada. Preferências completas acessíveis por ação global discreta, sem abrir uma quarta atividade concorrente. |

## Contratos comuns e estados críticos

- **Champselect:** manter geometria e ancoragem D-017. Painel rápido contém Runas/Itens/Mods e acesso às skins do campeão; não remover categorias legadas. Ajustes contextuais: rota/confronto, comparação de fontes e preferência da sessão. “Todas as configurações” leva à configuração completa, preservando rascunho e caminho de volta. Não carregar toda a administração dentro do painel de 452×492.
- **Fontes:** preferência reduz decisões frequentes; comparação permite Lolalytics e Onetricks simultâneos, cada qual com seu próprio resultado/amostra/patch em detalhes. Mostrar Onetricks como simulação futura no protótipo; indisponibilidade não produz números substitutos. Não agregar WR nem amostras incompatíveis. Mudança de preferência não importa runas sozinha. Branding/origem visível proposto depende de compatibilizar D-008/016; produção mantém origem e natureza estatística nos tooltips conforme aprovado.
- **Runas:** recomendação visível não importa; clique importa a original imediatamente; edições válidas são agrupadas e a mais recente vence; nunca sobrescrever páginas pessoais. Representar importando/sucesso/falha e `no_free_page` sem apagar página pessoal.
- **Itens:** Outras builds lista **trios observados**, mais jogados primeiro, com ícones, WR conjunto, partidas e busca por item. Escolha põe trio antes das seções padrão; Voltar ao padrão desfaz. Não completar seis slots por invenção. Preservar importação automática ao confirmar campeão.
- **Ponderação futura:** explicar entradas, elegibilidade e resultado ilustrativo, sem score/fórmula funcional nem superioridade alegada. Primeiro excluir incompatíveis; caso Exalted com croma que desativa CTRL5 é inelegível. Estado precisa dizer o motivo, sem tratar como chance baixa. Confirmar semântica e catálogo com Claude antes de implementar.
- **Perfis/sorteio:** conjuntos salvos com prévia, campeões abrangidos e ativo/inativo. Antes de entrar no sorteio coordenado, mostrar que desliga o perfil. Sorteio pessoal no contexto do campeão; grupo no contexto da sala. Não inventar precedência entre manual/perfil/sorteio sem contrato documentado.
- **Arena Bravura:** ação revelar → resultado visível → sortear novamente, sem revelar antes da ação nem conceder estatísticas inventadas. Proposta futura independente das cartas de aprimoramentos: estas mostram só opções realmente oferecidas, admitem correção manual e nunca são escolhidas pelo app (D-020). Estados sem dados e não reconhecida permanecem distintos.
- **Overlays:** prévia explícita; ouro no placar, Arena/Mayhem separados. WR/PR/partidas apenas quando disponíveis. Opções globais gravam ao salvar, sem reiniciar; requisito tela sem bordas mantido.

## Verificação dos protótipos

Percursos mínimos: escolher atividade/destino e voltar; editar/aplicar conjunto; importar mod e resolver skin-base; criar/sair de sala; sorteio com conflito de perfil; abrir suporte por erro e retornar; comparar fontes com Onetricks simulado; outra runa/importação recusada; trio/busca/restaurar padrão; Exalted inelegível; Bravura antes/depois da revelação; overlays e preferências completas/contextuais. Não representam testes de produção.
