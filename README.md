# SEXO2

Aplicativo personalizado para nosso grupo no League of Legends, baseado em Rose.
Um ponto de entrada no HUD reúne seleção de skins, favoritas, perfis, sorteio,
sala privada e configurações. Configurações e skins pessoais ficam fora do programa.

## Atualizações

A partir de 1.5.0, entregas para instalações existentes são patches assinados;
o helper atualiza a mesma pasta e mantém somente a última recuperação.
Não cria outra instalação ou atalhos. Veja [ATUALIZACOES.md](docs/ATUALIZACOES.md).

O código é privado em `teuzimmmm/sexo2`. Um commit mantém o código no GitHub;
uma tag `vX.Y.Z` solicita build/testes/publicação pelo workflow de release.
A primeira baseline é publicada a partir da compilação local verificada.

## Desenvolvimento

Python 3.14; dependências em `requirements.txt`. Binários Pengu/LTK/mod-tools e
cloudflared são recursos de build/distribuição, não segredos ou fontes próprias.
Builds seguintes recuperam esses binários da baseline anterior do projeto.

`python -m unittest discover -s tests -q` valida serviços e recuperação.
Os testes de navegador usam cliente e servidor simulados. A aparência e o uso
real ainda precisam ser observados no cliente LoL.

## Créditos

Base Rose, Pengu Loader, LTK e dependências mantêm suas licenças/atribuições.
BORK é da Riot Games; o escudo do Galo é do Clube Atlético Mineiro.
Veja `LICENSE` e as fontes em `assets/visual-provenance.json`.
