# Pengu core: licença (GPL-3.0) e o que o projeto cumpre

O Pengu Loader é GPL-3.0 (`vendor/PenguLoader-1.1.6/LICENSE`). O `core.dll` redistribuído é uma obra derivada.
Não é parecer jurídico.

## Obrigações ao distribuir o `core.dll` modificado
1. **Texto da licença** junto do binário: o artefato `pengu-core` inclui `LICENSE-PenguLoader-GPL-3.0`; o instalador deve manter a GPL e os créditos.
2. **Avisos e créditos upstream** preservados (PenguLoader, e Rose como base do fork, em `LICENSE`). O patch não remove nenhum aviso.
3. **Indicar a modificação:** `native/pengu-core/0001-sexo2-config-ini-path.patch` e `LEIA-ME.md`.
4. **Fonte correspondente** a quem receber o binário: upstream no commit fixado (`native/pengu-core/UPSTREAM`) + o patch +
   o workflow de build. Publicar isso (ou oferecer por escrito) junto de cada release. O repositório é privado:
   **pendente decidir como oferecer o fonte** (ex.: anexar o patch e o UPSTREAM à release, ou repositório público do patch).
5. **Mesma licença** (GPL-3.0) para o `core.dll` modificado.

## Pendências
- O `core.dll` antigo (baseline v1.6.4, fork "ROSE-Pengu") é uma versão modificada **sem fonte publicado**; ao substituí-lo pelo novo isso deixa de valer para o core, mas o autor do fork (Alban1911/Rose) ainda distribui o binário antigo.
- `core/res/resource.rc` do upstream declara o DLL como "Microsoft Direct3D 9 Runtime". Ao distribuir, trocar por informação honesta (decisão pendente).
