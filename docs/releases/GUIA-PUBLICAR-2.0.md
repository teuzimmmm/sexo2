# Guia para publicar o SEXO2 2.0

Tudo isto é feito no **seu PC Windows**, onde está a chave de assinatura. Nada aqui publica sozinho: a única linha que publica é o passo 7.
Estado do código: a `gunderfrank` está na 2.0.0 (ícone do galo, aba Equipe, instalador). As versões 1.9.1 e 1.9.2 nunca foram publicadas; a última release no GitHub é a **v1.9.0**, e a 2.0 é a próxima que seus amigos recebem.

## O que você precisa ter

| Item | Onde / como conferir |
|---|---|
| Chave de assinatura | `release-secrets\signing.key` dentro da pasta do projeto (fora do Git). **Não gere outra**: quem já tem o SEXO2 só aceita atualização assinada pela mesma chave. |
| Token de leitura dos amigos | `assets\update-access.json` (fora do Git), ou a variável `SEXO2_DOWNLOAD_TOKEN` na janela do PowerShell, **antes** do passo 3. Sem ele, o app 2.0 não consegue baixar as próximas atualizações. |
| Pasta do app da última release (1.9.0) | A pasta compilada que serviu de base da 1.9.0, algo como `dist-sexo2-1.9.0\SEXO2`, com `SEXO2.exe` dentro. É o `-BaseFolder` do passo 3. |
| Inno Setup 6 | https://jrsoftware.org/isdl.php (o script avisa se faltar). |
| Python + dependências + PyInstaller | os mesmos das releases anteriores (`pip install -r requirements.txt pyinstaller`). |
| Login do Git com permissão de escrita | `git credential fill` precisa devolver sua credencial do GitHub (Git Credential Manager). Teste com `git ls-remote origin`. |

## Passo a passo

### 1. Trazer o código da 2.0
```powershell
cd <pasta do projeto>
git fetch origin
git status                      # deve estar limpo (sem alterações suas)
git switch gunderfrank
git pull --ff-only origin gunderfrank
```
Confira: `python -c "from sexo2.version import RELEASE_VERSION as v; print(v)"` deve imprimir `2.0.0`.

### 2. Alinhar a `main` (precisa da sua decisão)
O publicador cria a tag `v2.0.0` apontando para a **`main`**. Hoje a `main` está na 1.9.0, e ela é ancestral da `gunderfrank`, então basta avançar sem merge:
```powershell
git switch main
git merge --ff-only origin/gunderfrank
git push origin main
```
Se preferir não mexer na `main` agora, não publique: a tag sairia no código antigo. Não fiz isso por mim; é a única mudança em `main`/`galinacio`, e só você a autoriza.

### 3. Compilar e assinar (≈ 10 a 20 min)
```powershell
powershell -ExecutionPolicy Bypass -File scripts\release_local.ps1 -Version 2.0.0 -BaseFolder "<pasta do app 1.9.0>"
```
O script faz, em ordem: restaura os binários da base, **roda todos os testes** (para se algum falhar), compila o app e o atualizador com PyInstaller, audita o pacote, monta o pacote de atualização, gera o instalador, assina o patch e gera as atualizações retroativas. No fim imprime `Local signed release ready: ..\SEXO2-2.0.0`.

Nota: corrigi o `scripts\prepare_release.py`, que não reconhecia mais a versão com aspas duplas em `sexo2\version.py` e deixaria a 2.0 com número errado. Está no commit.

Observação: os testes em Windows devem passar sem as 3 falhas e 13 erros que aparecem no Linux (são do ambiente). Se algum falhar no seu PC, **pare** e me mande a saída.

### 4. Conferir a pasta gerada
`..\SEXO2-2.0.0` deve ter pelo menos:
- `SEXO2-Instalador-2.0.0.exe`
- `SEXO2-update.zip`
- `SEXO2-baseline.zip`
- `SEXO2 Update.exe`
- `SEXO2-update-from-*.zip` e `SEXO2-Atualizacao-*.zip` (um por versão antiga compatível)

Se faltar o instalador ou o `SEXO2-update.zip`, **não publique**: o atualizador dos amigos usa a release mais recente (`/releases/latest`), e uma release incompleta quebra a atualização deles.

### 5. Testar antes de publicar
1. Em outra pasta (ou numa VM), execute `SEXO2-Instalador-2.0.0.exe`, abra o SEXO2 e confira: ícone do galo no atalho, na barra de tarefas e na bandeja; painel em Configurações mostrando **2.0.0**; abertura animada com o galo.
2. Se tiver uma instalação 1.9.0 de teste, aplique `SEXO2-update.zip` pelo atualizador e confira que os dados em `%LOCALAPPDATA%\SEXO2` continuam.
3. Abra o LoL e veja a seleção de campeões com a aba Equipe.

### 6. Notas da release
```powershell
Copy-Item docs\releases\2.0.0.md ..\SEXO2-2.0.0\release-notes.md
```
O publicador coloca sozinho, no topo, as instruções "Primeira instalação / Quem já tem".

### 7. Publicar
```powershell
python scripts\publish_local.py --version 2.0.0 --folder ..\SEXO2-2.0.0
```
Ele cria a release como **rascunho**, envia os arquivos, publica e **confere tamanho e SHA-256 de cada arquivo**. No fim imprime `Verified private release: <link>`; o relatório fica em `..\SEXO2-2.0.0\github-release-verification.json`. Se cair no meio, a release continua rascunho: rode o mesmo comando de novo (ele pula o que já subiu).

### 8. Depois de publicar
- Numa instalação 1.9.0, abra Configurações > Atualizações e confira que ela oferece a 2.0.0.
- Os pré-lançamentos `teste-<commit>` do CI não afetam ninguém (o atualizador os ignora).
- Guarde a pasta `..\SEXO2-2.0.0` e a pasta compilada: são a base da próxima versão.

## Se algo der errado
| Sintoma | O que fazer |
|---|---|
| `Local signing key is missing` | A chave não está em `release-secrets\signing.key`. Restaure o backup; **não** gere outra. |
| Falha de teste no passo 3 | Pare e me envie a saída. Não use `-SkipTests` nem edite o script. |
| `Inno Setup 6 not found` | Instale o Inno Setup e rode o passo 3 de novo. |
| `Retroactive updates failed` | Não publique; me envie a saída. |
| `git credential fill` sem senha | Faça `git ls-remote origin` uma vez para o Git Credential Manager pedir o login e repita o passo 7. |
| Publicou algo errado | A release fica como a última; apague-a no GitHub (Releases > v2.0.0 > Delete) **antes** de os amigos atualizarem e repita. |

## O que eu não consegui verificar
Não tenho Windows, a chave nem o Inno Setup aqui. Verifiquei no Linux: testes (as mesmas 3 falhas e 13 erros de ambiente já existentes), `ruff`, tokens, plugins JS e os testes do ícone. A compilação, o instalador, a assinatura e o ícone no Windows real só aparecem nos passos 3 a 5.
