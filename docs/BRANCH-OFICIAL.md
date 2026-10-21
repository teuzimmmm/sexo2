# Branch oficial: `galinacio`

Desde 20/10/2026 a branch oficial do SEXO2 é **`galinacio`**. A `amolula` (oficial de 19 a 20/10/2026) e a `sexoatividade` ficam só como histórico: não recebem mais commits. As branches `ux/*` são trabalho integrado e também ficam como histórico.

- Commits e pull requests: sempre na `galinacio` (ou numa branch criada a partir dela). Nunca `main` nem releases sem autorização do usuário.
- CI: `.github/workflows/release.yml` roda a validação em todo push e, em push na `galinacio`, publica a build de teste sem assinatura como pré-release `teste-<commit>` (o atualizador ignora pré-releases). Releases assinados continuam sendo feitos localmente por `scripts/release_local.ps1`.
- Origem: a `galinacio` recebeu o trabalho da `amolula` (merge de 20/10/2026) e mantém os protótipos de design que já tinha (`design/propostas/`). A `amolula` parte de `ux/0.9-integracao`; ver `docs/PROGRESSO-INTEGRACAO.md`.
- A branch padrão do GitHub e a proteção de branch são configurações do repositório e não foram alteradas.
