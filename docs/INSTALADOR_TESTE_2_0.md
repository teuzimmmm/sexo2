# Instalador de teste da 2.0

Plano registrado antes da implementação desta rodada, em 16/10/2026.

Objetivo: produzir um instalador convencional para testar o fluxo de builds no
Windows, com arquivos atuais, sem publicar uma versão estável ou usar a chave de
assinatura. O instalador usa AppId, diretório de programa e atalhos de teste
próprios, bloqueia a instalação enquanto SEXO2/Rose estiver aberto e não remove
cadastros, pastas ou atalhos de versões anteriores.

## Decisão sobre o legado

Esta é uma instalação de **teste funcional**, não o executor da migração final.
Os dados/runtime atuais ainda ficam em `LocalAppData/Rose`: o contrato de leitura
de `config.ini` pelo `core.dll` distribuído não foi comprovado para outro caminho.
Mudar somente Python poderia deixar a seleção sem plugins. Portanto, manter a
compatibilidade nesta edição; não declarar independência de Rose nem autorizar
apagar essas pastas. O uso do aplicativo pode gravar suas preferências e páginas
gerenciadas normalmente. O instalador não copia dados pessoais para o pacote.

A migração e limpeza definitiva continuam conforme `SEXO2_2_0.md`, após validar
as dependências nativas. O instalador de teste não encerra o LoL à força, não
desinstala um Pengu externo e não altera a tarefa de inicialização herdada.

## Etapas e critérios

1. Substituir o `.iss` antigo do SEXO2 por uma edição de teste parametrizada,
   sem caminhos de build pessoais, backup integral acumulativo ou remoções por nome.
2. Criar build Windows a partir de snapshot limpo do Git; recuperar somente
   binários nativos permitidos de uma baseline existente, preservando os plugins
   atuais do checkout. Nenhum INI, datastore, token ou chave entra no staging.
3. Auditar os módulos congelados e todos os plugins antes de executar Inno Setup.
   Gerar `.exe`, SHA-256 e relatório de origem sem credenciais/caminhos pessoais.
4. Desabilitar atualização estável automática nesta edição para impedir que uma
   atualização antiga substitua o código novo. Identificar a versão de teste nas
   configurações sem mudar o protocolo herdado.
5. Cobrir seleção de arquivos, travessias/links, limites, identidade de teste,
   bloqueio de atualização e contratos do instalador com testes offline.
6. Preparar job Windows privado para gerar artefato de teste, sem release ou
   chave privada. Push/execução remota dependem da autorização aplicável.

Conclusão: código revisado e testes pertinentes passam; build nativo só será
anunciado como produzido após compilar e conferir o arquivo real. Neste checkout
Linux não existem Inno Setup, runtime Windows ou binários Pengu/LTK/mod-tools.

## Compilação local no Windows

Com Python 3.14 x64, Git, dependências e Inno Setup 6 instalados, em um checkout
com alterações registradas no Git:

```powershell
python -m pip install -r requirements.txt
python scripts/build_test_installer.py --base "C:\pacotes\SEXO2-baseline.zip" --version 2.0.0.1
```

`--base` também aceita uma pasta existente do SEXO2 contendo `_internal`.
A origem é somente leitura; os únicos arquivos recuperados são binários nativos
permitidos. Os fontes vão para staging temporário a partir dos arquivos rastreados;
arquivos locais ignorados não entram no pacote. A assinatura privada não é usada.

A saída fica em `build-test-installer/output`: instalador `.exe`, arquivo
`.sha256` e relatório `.json`. O nome contém versão e commit do código.
O pipeline recusa código rastreado sem commit, baseline incompleta, binários
inválidos, links, caminhos inseguros e auditoria de código congelado divergente.
Não basta o compilador retornar sucesso: o arquivo final deve existir e ter
cabeçalho PE antes de produzir o hash e o relatório.

## Compilação privada pelo GitHub Actions

O workflow `Build private test installer` usa Windows x64, baixa a baseline
`v1.6.4` do próprio repositório, roda testes, compila, audita e guarda o artefato
`SEXO2-2.0-Teste` por sete dias. O token do job só aparece na etapa de download;
não entra no staging nem no instalador. Não cria release nem atualiza a branch
principal. Pode ser disparado por push na branch `test/installer-2.0` ou manualmente
quando o workflow estiver disponível no repositório remoto.

O workflow precisa que a baseline contenha os componentes nativos já usados pelo
projeto, incluindo o patcher existente; não baixa substitutos de outras origens.
Nenhum build usa o pacote de atualização para sobrepor plugins ao código novo.

## Instalação e teste

Abra o instalador e siga o fluxo convencional. Ele instala em
`%LOCALAPPDATA%\Programs\SEXO2-2.0-Teste`, com cadastro próprio e atalho
`SEXO2 2.0 Teste`. Feche o SEXO2/Rose antes de instalar e de abrir a outra edição;
as duas não podem controlar o LoL ao mesmo tempo. O instalador não fecha processos
à força nem abre o programa automaticamente por padrão.

Na seleção, abra `SEXO2 · Builds`, consulte WR/Common e importe explicitamente
runas/itens. Ao finalizar o draft, escolha um adversário. A edição aparece como
`2.0.0.1 (teste)` nas configurações. Se houver um Pengu externo ativo, aplica-se a
limitação de sincronização descrita em `DESENVOLVIMENTO_2_0.md`; não sobrescrevemos
uma instalação externa silenciosamente.

Desinstalar esta edição remove os arquivos instalados e seus atalhos próprios;
não remove os dados compartilhados, versões anteriores nem um Pengu externo.
O suporte final a instalação independente e limpeza permanece pendente.

## Verificação desta rodada

- 15 testes novos de identidade, seleção de arquivos, caminhos/links, limites,
  separação do canal de teste e contratos de instalação passaram no Linux.
- Testes focados de instalador, atualização e configurações: 30 passaram.
- Suíte geral: 439 testes, sem falhas de asserção, com o mesmo erro preexistente
  de `ctypes.windll` ausente neste Linux e um teste nativo de Windows ignorado.
- A baseline privada `v1.6.4` foi baixada em diretório temporário. Doze binários
  nativos foram selecionados e seus cabeçalhos PE conferidos; não se restauraram
  configurações, tokens, datastore ou plugins antigos.
- O YAML do workflow foi analisado: repositório somente leitura no job, token
  limitado à etapa de download e publicação restrita ao artefato de teste.
- Compilação efetiva de PyInstaller/Inno Setup permanece dependente de Windows.
  Não foi produzido um `.exe` neste ambiente Linux.

O primeiro job Windows identificou a mudança do limite de recursão JSON no Python
3.14 e a normalização de nomes ZIP pela stdlib no Windows. O cliente agora limita
explicitamente a profundidade do cache a 128 contêineres; um cache inválido vira
miss e é buscado novamente. O empacotador verifica também o nome original do ZIP,
e o teste constrói cabeçalhos realmente malformados nas duas plataformas.
