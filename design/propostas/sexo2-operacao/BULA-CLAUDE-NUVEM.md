# BULA — implementar a UX aprovada da proposta A em `sexoatividade` (execução autônoma, baixo consumo)

Cole este texto para o Claude na nuvem. Modelo: **Sonnet, esforço médio, sozinho** (sem subagentes, sem Opus, sem /goal extra). Branch de trabalho: `sexoatividade`. Nunca `main`, release, force push, merge em outra branch ou alteração de CI/dependências.

## Objetivo
Levar para o produto real as decisões de UX aprovadas pelo usuário na proposta A (laboratório em `teuzimmmm/sexo2@galinacio`, pasta `design/propostas/sexo2-ux-a/`). A proposta é protótipo HTML com dados fictícios: copie as DECISÕES, não o código do protótipo; o visual vem do código atual do app (skill `sexo2-ui`). Leia só: `CLAUDE.md`, `docs/comportamentos.md`, a skill `sexo2-ui`, `sexo2-ux-a/NOTAS-PARA-CODIGO.md`, `sexo2-ux-a/PROGRESSO.md` e as telas do código que for tocar. NÃO leia `index.html` do protótipo inteiro (1+ MB nas réplicas; use grep/offset), nem pesquise de novo decisões já tomadas.

## Decisões aprovadas (implementar, nesta ordem, um commit pequeno por item)
1. Painel SEXO2: cantos retos (sem border-radius) e cabeçalho só "SEXO2" — sem rótulo ao lado da marca. Fonte Oswald em "SEXO2" na seleção de campeões; Inter no resto.
2. Menus do painel, nesta ordem: Sala, Favoritas, Configurações, Suporte, Swiftplay (este só aparece no modo Swiftplay). Abrir o painel cai em Sala. Sem destaque de sorteio, sem "Conjunto ativo/Skin aplicada", sem "elegível ao sorteio".
3. Favoritas: todos os campeões do LoL, busca por nome de campeão E de skin; clicar no campeão abre as skins dele; clicar na skin a seleciona e expande os cromas; só o botão "Favoritar". Favoritar skin NÃO favorita croma por padrão; croma é favoritável separadamente. Usar dados/catálogo que o app já tem; imagem (snippet) da skin só se já existir fonte no código — senão placeholder e registrar como pendência.
4. Swiftplay: SEMPRE 2 campeões travados; escolher a skin de cada um; sem mexer em nada, sorteia como a Bravura, favoritas primeiro. Só implemente se o modo Swiftplay for detectável com dados reais já usados pelo app; senão deixe documentado como bloqueio.
5. Assistente na seleção (452×492, ancorado, regra D-017): sem cabeçalho de campeão/skin; no topo Rota, Confronto, Fonte (Lolalytics/Onetricks — Onetricks só se existir provedor; senão indisponível honesto). Abas: Runas, Itens, Mods (só mods), Preferências rápidas, Todas as configurações. Sem aba Skins. Sem o texto "Ver a recomendação não altera o cliente…". Manter "Build padrão" com Inicial/Essenciais/Situacionais e Outras builds/trios.
6. Overlay de ouro em itens: topo mostra só a diferença total (ex.: -210), sem "ITENS" nem "ouro".

## Fora do escopo (só registrar em `docs/produto/decisoes.md` como pendente / nota para equipe)
- Remover Conjuntos e Sorteio como funções/menus: o usuário os considera inúteis, mas o sorteio é usado pela Bravura e há testes protegidos. Retire apenas da UI; remoção de código só com testes provando equivalência — senão deixe nota.
- Renomear "Hub"/"Atividades" (o usuário acha feio; aguardar nomes dele). Proposta B foi descartada: ignore `sexo2-ux-b/`.
- Imagens de skins de mods, algoritmo ponderado, qualquer rede nova.

## Regras duras
- Compatibilidade e comportamentos protegidos conforme `CLAUDE.md` (dados `%LOCALAPPDATA%\Rose`, mensagens da ponte, mutex etc.). Toque numa área só com o teste correspondente passando antes e depois.
- Nomes/menus/layout novos exigem aprovação: registre em `docs/produto/decisoes.md` como "proposto pelo usuário na sessão de design de 18/10/2026; pendente de confirmação formal" e implemente apenas os itens acima.
- Sem polling/timers novos. Sem imagens geradas. Oswald+Inter locais, sem azul, sem serifa.
- Commits pequenos por finalidade; formatação separada. Push só em `sexoatividade`, sem force.

## Verificação (rodar antes de cada push; critério final é o CI Windows)
```
python scripts/run_tests.py -q
node --test tests/test_*.cjs
ruff check . && ruff format --check .
python design/build_tokens.py --check
```
Teste simulado não substitui validação no cliente real: declare isso no relatório.

## Economia de consumo (obrigatório)
- Sem subagentes. Leia apenas os arquivos necessários, em trechos; não releia o que já leu.
- Checagens por script, não por revisão do modelo. Sem screenshots salvo falha visual real.
- Uma rodada de correção por item. Teto: 20 turnos por item; se 3 turnos seguidos sem progresso verificável (testes), salve estado parcial, registre o bloqueio em `docs/PROGRESSO-UX.md` (≤40 linhas) e passe ao próximo item.
- Não aumente gastos, créditos ou limites. Não pergunte nada: decisões rotineiras estão autorizadas; só pare por bloqueio real de permissão.

## Entrega
Ao final: `docs/PROGRESSO-UX.md` com, por item 1–6, estado (feito/parcial/bloqueado), testes rodados e resultado, commits, e o que NÃO foi validado (Windows/cliente real/partida). Não declare sucesso por atingir o teto.
