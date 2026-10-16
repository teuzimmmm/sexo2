# SEXO2

Aplicativo personalizado para nosso grupo no League of Legends, baseado em Rose.
Um ponto de entrada no HUD reúne seleção de skins, favoritas, perfis, sorteio,
sala privada e configurações. Configurações e skins pessoais ficam fora do programa.

## Atualizações

A partir de 1.5.0, entregas para instalações existentes são patches assinados;
o helper atualiza a mesma pasta e mantém somente a última recuperação.
Não cria outra instalação ou atalhos. Veja [ATUALIZACOES.md](docs/ATUALIZACOES.md).

O código é privado em `teuzimmmm/sexo2`. Um commit mantém o código no GitHub;
as versões são compiladas e assinadas no PC, depois publicadas no GitHub.
O workflow valida o código, sem guardar a chave privada.
A primeira baseline é publicada a partir da compilação local verificada.

## Desenvolvimento

O fluxo de trabalho com agentes, incluindo critérios para delegar e economizar
cota, fica em [AGENTS.md](AGENTS.md).

Python 3.14; dependências em `requirements.txt`. Binários Pengu/LTK/mod-tools e
cloudflared são recursos de build/distribuição, não segredos ou fontes próprias.
Builds seguintes recuperam esses binários da baseline anterior do projeto.

`python -m unittest discover -s tests -q` valida serviços e recuperação.
Os testes de navegador usam cliente e servidor simulados. A aparência e o uso
real ainda precisam ser observados no cliente LoL.

## SEXO2 2.0 — arquitetura e instalação

A versão 2.0 terá instalação, dados e runtime próprios, com migração e limpeza
das versões antigas no instalador inicial. Isso é requisito para publicação;
a dependência atual de pastas Rose ainda não foi removida. A arquitetura,
as evidências e os critérios estão em [SEXO2_2_0.md](docs/SEXO2_2_0.md).

O fluxo de recomendações na seleção, importação e painel específico já está
integrado no código. Testes isolados e fontes reais foram verificados; a
validação no cliente Windows ainda está pendente. Consulte
[DESENVOLVIMENTO_2_0.md](docs/DESENVOLVIMENTO_2_0.md) para uso, testes e limites.

## Coletor LoLalytics (fase 1)

Biblioteca e CLI independentes para Ranked, ARAM e Arena, sem integração no
cliente nesta fase. Veja [uso, fontes e limites](docs/lolalytics/README.md).

## Créditos

Base Rose, Pengu Loader, LTK e dependências mantêm suas licenças/atribuições.
BORK é da Riot Games; o escudo do Galo é do Clube Atlético Mineiro.
Veja `LICENSE` e as fontes em `assets/visual-provenance.json`.
