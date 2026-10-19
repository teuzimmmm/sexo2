# Branch oficial: `amolula`

Desde 19/10/2026 a branch oficial do SEXO2 é **`amolula`**. A `sexoatividade` está obsoleta: não recebe mais commits e fica só como histórico. As branches `ux/*` são trabalho integrado na `amolula` e também ficam como histórico.

- Commits e pull requests: sempre na `amolula` (ou numa branch criada a partir dela). Nunca `main` nem releases sem autorização do usuário.
- CI: `.github/workflows/release.yml` roda a validação em todo push e, em push na `amolula`, publica a build de teste sem assinatura como pré-release `teste-<commit>` (o atualizador ignora pré-releases). Releases assinados continuam sendo feitos localmente por `scripts/release_local.ps1`.
- Origem: a `amolula` parte de `ux/0.9-integracao` (fase 0.9 pre-launch: painel, Favoritas, sorteio ponderado, Swiftplay, abertura animada, ícone novo, M5b). O que a `sexoatividade` tinha em paralelo foi integrado ali; ver `docs/PROGRESSO-INTEGRACAO.md`.
- A branch padrão do GitHub e a proteção de branch são configurações do repositório e não foram alteradas por este commit.
