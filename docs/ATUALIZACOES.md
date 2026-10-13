# SEXO2 — atualizações

## Entrega inicial

A versão 1.5.0 adiciona configurações próprias, BORK preto, Galo na abertura e
atualizador independente. O pacote de transição contém `SEXO2 Update.exe` e patches
assinados para r2/r3. Extraia, feche apenas SEXO2, execute o helper novo. Ele tenta achar
a instalação pelo cadastro existente e o pacote pelo hash do executável. Nada é
reinstalado ou registrado novamente. Se precisar, escolha a pasta instalada.

Dados continuam em LocalAppData/Rose. O helper nunca inclui essas preferências
nem as skins pessoais nos arquivos de atualização. Um backup da última troca é
mantido em `.sexo2-update/rollback`; backups antigos dos instaladores não são
apagados automaticamente.

## Central privada

Repositório: https://github.com/teuzimmmm/sexo2 (privado).
Ao abrir o SEXO2, a consulta ocorre em segundo plano. O painel também oferece
Verificar atualização, Atualizar e Abrir GitHub do projeto. Uma atualização só é
aplicada pelo helper após fechar apenas o aplicativo. O LoL pode permanecer
aberto. Não há fechamento forçado.

Acesso de publicação e de download são separados. O usuário autorizou incluir
um token compartilhado de leitura no aplicativo para seu grupo. Esse token deve
ser fine-grained, limitado a `teuzimmmm/sexo2`, Contents: Read-only; pode ser
extraído do pacote. O token de publicação nunca é incluído. Salvar o token de leitura localmente em `assets/update-access.json`, ignorado
no Git; a rotina de build inclui esse arquivo no aplicativo. Também pode receber
`SEXO2_DOWNLOAD_TOKEN` apenas no ambiente de compilação local. Não colar tokens no chat.
Sem esse token, o botão GitHub funciona para contas autorizadas, mas a consulta
anônima ao repositório privado não consegue baixar seus lançamentos.

## Publicar

O primeiro lançamento inclui uma baseline gerada localmente e o patch de
transição. Os próximos são gerados localmente e publicados como `vX.Y.Z`. Commits sem tag não chegam automaticamente aos amigos.

Decisão final do usuário: chave somente no PC. O GitHub valida o código; não
compila/assina/publica sozinho. `scripts/release_local.ps1` prepara, testa, compila,
audita e assina localmente. Depois o pacote pronto é enviado à release privada.
A chave privada está em `release-secrets/signing.key`, ignorada no Git e ausente
dos pacotes. Não apagar nem substituí-la para clientes já distribuídos.
Nenhum secret de assinatura foi criado no GitHub.

## Recuperação e limites

Assinatura Ed25519, SHA-256 por arquivo, validação do estado anterior e caminhos
restritos antes de gravar. Mudanças são serializadas por trava do sistema. Após
falha ou interrupção, o journal mantém uma transação recuperável. Somente arquivos
declarados podem ser trocados; arquivos pessoais e hashes.game.txt são protegidos.
Testes isolados cobrem assinatura inválida, versão divergente, caminhos proibidos,
falha durante troca, conservação dos dados e retenção de somente um backup.
A aparência real ainda depende das fontes e do cliente LoL em execução.


Acesso de leitura configurado pelo usuário em 13/10/2026. Versão 1.5.1 inclui
o acesso e o patch de transição. Token validado na API, sem reprodução em logs.
Para publicar uma release assinada localmente, usar `scripts/publish_local.py`
com `--version` e `--folder`; utiliza a autenticação de publicação já guardada
pelo Git Credential Manager, não o token de leitura distribuído.
GitHub CI aprovou os commits de validação da central e da versão 1.5.1.

## Compatibilidade obrigatória a partir de 1.5.2

scripts/compatibility_bases.json registra cada baseline suportada. release_local
gera SEXO2-update-from-<base>.zip para todas e falha se faltar uma pasta; nunca
apagar baseline sem definir migração. A versão recém-gerada é registrada para as
próximas releases. publish_local envia os deltas e o ZIP com helper junto da
release. O cliente novo escolhe o delta por versão. Clientes anteriores escolhem
só o primary: quem ficou várias versões atrás deve usar uma vez o ZIP com helper
novo, que identifica o executável por hash. Depois pode saltar versões no painel.
Assinatura e validação de cada arquivo continuam obrigatórias.

## LoL aberto durante atualização — 1.5.3

Removida a exigência geral de fechar LeagueClient/LeagueClientUx e o jogo.
Somente SEXO2/Rose em execução bloqueia a substituição do aplicativo. O helper
não encerra processos. A regra antiga permanece nos helpers já distribuídos:
para a primeira atualização sem fechar o LoL, abrir o helper novo externo.
Depois de receber 1.5.3, o helper do painel já usa a regra nova. Código dos plugins
já carregados no client pode continuar antigo até seu próximo carregamento.
Arquivos em uso continuam sujeitos à proteção de transação/recuperação do updater;
a mudança não força substituição de DLL bloqueada nem reinicia o LoL.
