# Integração da fase 0.9 (branch ux/0.9-integracao)

Ordem: ux/v0.9-prelaunch, ux/v0.9-m5b-rename, ux/abertura, ux/icone-novo (1dc67bb). Sem squash; merges `--no-ff`.

## Como os conflitos foram resolvidos
- A sexoatividade já tinha, em paralelo, assistente (452x492, Outras builds/runas), ouro estilo Blitz, Favoritas com
  imagens e plugins formatados. Nesses arquivos prevaleceu a sexoatividade (`SEXO2-Assistant`, `assistant.py`,
  `gold_overlay.py`, `SEXO2-Settings`, `SEXO2-Amigos`) e as partes novas foram reaplicadas: painel D-115 em
  `SEXO2-Hub` (menus Sala, Favoritas, Configurações, Suporte e Swiftplay; abre em Sala), busca por skin em Favoritas
  (`skin-index`), biblioteca de mods fora de Configurações. Sorteio ponderado e Swiftplay entraram sem conflito.
- Renomeação: os plugins formatados receberam as mesmas trocas de tokens do M5b (transformação verificada contra
  os arquivos do M5b); `pengu_loader` usa `app_activated`/`restore_after_app`.
- Pasta de dados: a migração Rose -> SEXO2 da sexoatividade prevalece sobre "pasta Rose mantida" do M5b.
- IDs: D-115..D-120 antigos da sexoatividade viraram D-125..D-129; D-122 = M5b, D-123 = ícone, D-124 = abertura.
- Ícone: `icon.png`/`sexo2.svg` no item de menu (`SEXO2-UI`); `hub_icon.png` e Galo/BORK removidos.

## Pendências conhecidas
- Aba "Preferências rápidas" e "Todas as configurações" do assistente (D-117) não estão na versão da sexoatividade.
- Sem Node local: testes `.cjs` rodam só no CI.
