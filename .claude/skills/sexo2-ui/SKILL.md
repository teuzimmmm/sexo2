---
name: sexo2-ui
description: Use before proposing, changing or implementing any SEXO2 user interface — Pengu plugins, the champion-select assistant, overlays, settings, tray texts, names, menus, colours, fonts or user-facing messages. Keeps the agent on approved decisions and stops it before inventing new product decisions.
---

# Interface do SEXO2

1. Leia `docs/produto/decisoes.md` e `docs/produto/glossario.md`. O que está **aprovado** vale. O que está **pendente** não pode ser implementado como definitivo.
2. Visual: use apenas `design/tokens.css` (gerado de `design/tokens.json` por `python design/build_tokens.py`). Fontes: Oswald e Inter (D-007), nunca outra família nem fonte remota. Cores, escala e componentes só depois de aprovados (D-101 a D-103).
3. Para propor, monte a tela com os moldes de `design/wireframes.md` (ASCII) ou um HTML estático em `design/propostas/` que importe `../tokens.css`. Nunca gere imagens.
4. Antes de implementar, liste tudo o que for **novo**: nomes, textos, menus, componentes, cores, comportamentos automáticos. Se a lista não estiver vazia, pare. Registre como pendente em `decisoes.md` e peça aprovação, agrupando as decisões relacionadas.
5. Ao implementar algo aprovado:
   - reaproveite os componentes existentes;
   - não acrescente polling nem observadores amplos (regras de desempenho no `CLAUDE.md`);
   - use textos em português brasileiro natural, sem emojis nem exclamações;
   - não exponha nomes internos ao usuário.
6. Mudanças técnicas internas que preservam a interface e o comportamento não precisam de aprovação.
