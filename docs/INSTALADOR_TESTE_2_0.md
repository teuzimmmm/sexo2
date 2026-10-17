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

Com Python 3.14 x64, Git, Rust stable com ferramentas C++ do Windows,
dependências e Inno Setup 6 instalados, em um checkout
com alterações registradas no Git:

```powershell
python -m pip install -r requirements.txt
python scripts/build_test_installer.py --base "C:\pacotes\SEXO2-baseline.zip" --version 2.0.0.6
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
Após compilar, o job instala, reinstala e desinstala em um usuário descartável,
sem abrir SEXO2/Pengu/LoL. Confere versão, commit, plugin instalado, ausência de
credenciais e preservação de sentinelas sintéticas em Local/Roaming/Registro.
O relatório `installer-smoke.json` é incluído somente se a verificação passar.

## Instalação e teste

Abra o instalador e siga o fluxo convencional. Ele instala em
`%LOCALAPPDATA%\Programs\SEXO2-2.0-Teste`, com cadastro próprio e atalho
`SEXO2 2.0 Teste`. Feche o SEXO2/Rose antes de instalar e de abrir a outra edição;
as duas não podem controlar o LoL ao mesmo tempo. Para carregar a correção do painel,
feche também o cliente do LoL antes de instalar e abra-o novamente depois.
O instalador não fecha processos
à força nem abre o programa automaticamente por padrão.

Na seleção, abra `SEXO2 · Builds`, consulte WR/Common e importe explicitamente
runas/itens. Ao finalizar o draft, escolha um adversário. A edição aparece como
`2.0.0.6 (teste)` nas configurações. Se houver um Pengu externo ativo, aplica-se a
limitação de sincronização descrita em `DESENVOLVIMENTO_2_0.md`; não sobrescrevemos
uma instalação externa silenciosamente.

A partir de 2.0.0.3, a janela de partida usa as sugestões preparadas na seleção.
Em janela/sem bordas, F8 expande/recolhe, F9 troca a sugestão e F10 percorre o texto.
A opção **Mostrar builds durante a partida** fica nas configurações. O componente
não usa Pengu para desenhar sobre a partida; veja [OVERLAY_PARTIDA.md](OVERLAY_PARTIDA.md).

Na 2.0.0.4, Arena consulta popularidade durante a partida, sem painel de seleção.
As configurações incluem diagnóstico e **Testar janela (20 s)**; use essa prévia
para distinguir problemas de desenho e leitura da partida. Veja
[OVERLAY_CORRECOES.md](OVERLAY_CORRECOES.md) para testes, dados e limites.

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
  Não foi produzido um `.exe` por compilação neste ambiente Linux.

### Validação posterior em Windows — 2.0.0.2

O [job privado 38993159782](https://github.com/teuzimmmm/sexo2/actions/runs/38993159782)
compilou o código `6974b506e578ab2bd070c57c8c84c951cd6373b9` com sucesso.
Passaram 447 testes Python, o teste do painel em navegador isolado, a auditoria
do pacote e instalação/reinstalação/desinstalação em Windows descartável.
Os marcadores sintéticos do legado foram preservados. Não houve execução do LoL.

O artefato `12086445291` contém `SEXO2-2.0.0.2-Teste-6974b506.exe`.
O download foi conferido contra o checksum e o relatório de compilação:
SHA-256 `4aa76f54012b7c63f15fa4df98883e7b0ab2c19cb07a36d3ebd4fe6704ebca1a`.
Essas verificações substituem a pendência de compilação acima para essa edição
de teste; a validação no cliente real e a migração definitiva continuam pendentes.

O relato posterior do usuário distingue ausência do painel na seleção e de uma
interface durante a partida. Esta edição corrige a condição de exibição na
seleção; não contém uma interface sobre a partida. O plugin fecha ao sair de
ChampSelect. Importar conjuntos de itens pelo LCU não cria um overlay dentro do
jogo. Uma interface em partida requer projeto e implementação próprios.

O primeiro job Windows identificou a mudança do limite de recursão JSON no Python
3.14 e a normalização de nomes ZIP pela stdlib no Windows. O cliente agora limita
explicitamente a profundidade do cache a 128 contêineres; um cache inválido vira
miss e é buscado novamente. O empacotador verifica também o nome original do ZIP,
e o teste constrói cabeçalhos realmente malformados nas duas plataformas.

### Plano da edição 2.0.0.5 — leitor de cartas

Registrar a nova identidade de teste, compilar no Windows com o leitor OCR nativo
e conferir a auditoria dos módulos, helper e licenças antes de empacotar. Rodar
os testes do projeto, painel em navegador isolado e instalação/reinstalação/
desinstalação; baixar o artefato e comparar seu SHA-256 com o relatório.

Esta edição incorpora o reconhecimento dos três títulos visíveis na oferta,
confirmação em duas leituras e expiração da leitura. Arena associa pick rate e
jogos somente às cartas reconhecidas; Mayhem não recebe estatísticas de Arena.
O helper usa OCR local do Windows, sem salvar capturas. A validação anterior
foi sintética em Windows, conforme [OVERLAY_MOTOR.md](OVERLAY_MOTOR.md).

O renderer visual continua sendo o anterior, que falhou no teste do usuário.
Este instalador não comprova correção de visibilidade no LoL nem leitura de
cartas reais; o host DX11 experimental não é integrado ou injetado no jogo.
A migração/limpeza de Rose continua reservada à fase final.

### Validação Windows — 2.0.0.5

O [job privado 39003468347](https://github.com/teuzimmmm/sexo2/actions/runs/39003468347)
compilou o commit `ec69311758873441aff78f63ec23c365fd710244`. A suíte executou
499 testes (sete ignorados), sem falhas; passaram também quatro testes da janela
Windows e os testes do painel em Chromium isolado. A auditoria confirmou módulos,
plugins, helper OCR e avisos de dependências no pacote PyInstaller. Instalação,
reinstalação e desinstalação passaram, preservando sentinelas sintéticas do legado.
Nenhum SEXO2, Pengu ou LoL foi aberto pelo teste do instalador.

Artefato privado `12089573335`: `SEXO2-2.0.0.5-Teste-ec693117.exe` (61.027.346 bytes).
O download foi conferido contra checksum, identidade e relatórios de compilação/
instalação: SHA-256 `e22534d8c0a32fe818d87de42923d6663d77fa99aacc8b39a289dd47145ebfb6`.
O helper incluído tem SHA-256
`57b9d49766b36e4c1adf8294dc029dba596fbfc7b76df15becc7efca212fdb0d`.
Os limites visuais/no jogo descritos no plano da edição continuam pendentes.

### Plano 2.0.0.6 — DirectComposition

Edição para testar o novo renderer DirectComposition/D3D11/Direct2D/DirectWrite,
sem GDI de desenho, hooks ou integração com Game Bar/Overwolf/Electron.
A DLL pertence somente ao processo SEXO2; não é carregada no LoL. O instalador
compila a DLL com MSVC/Windows SDK e audita seu hash. O smoke confere a DLL
instalada e a carrega/desenha em um HWND sintético antes de desinstalar.
Ver [OVERLAY_MOTOR.md](OVERLAY_MOTOR.md#correção-de-composição--plano-antes-do-código-17102026).

O controlador reafirma o z-order mesmo sem novos dados, usa pixels físicos e
abre o painel expandido. A espera pelo OCR e a perda do LCU têm avisos visíveis
somente sobre o processo do jogo em primeiro plano; não exibem dados antigos
ou ofertas presumidas. Janela/sem bordas é o caminho previsto. Tela cheia
exclusiva e uma partida real do LoL não foram validadas neste runner.

### Validação Windows — 2.0.0.6

O [job privado 39004586918](https://github.com/teuzimmmm/sexo2/actions/runs/39004586918)
compilou `abc17e58d7b0f51556881b36a8081b953f6703f6`. A suíte executou 501 testes
(oito ignorados), sem falhas; passaram cinco testes nativos, incluindo pixels e
recuperação do z-order sem repaint, e o painel em Chromium isolado. A auditoria
comparou a DLL e os módulos com o staging. O smoke conferiu o hash da DLL
instalada, carregou-a e desenhou em um HWND sintético no próprio processo Python.
Instalação, reinstalação e desinstalação passaram, sem abrir SEXO2/Pengu/LoL.

Artefato privado `12090396803`: `SEXO2-2.0.0.6-Teste-abc17e58.exe` (61.083.333 bytes).
Download conferido contra checksum, commit, versão e recibo de instalação:
SHA-256 `09d63fc083a03e1b93dcda420eea66ea4fa7cc168aecdea16bcf8652f0c661ce`.
DLL incluída: `a45c43197b82897f1117a27737dc9581f3db84a56debc61b6eaa06a9c91d4400`.
O leitor OCR continua incluído. Não houve validação de partida real; a janela
externa destina-se a janela/sem bordas e não garante tela cheia exclusiva.

### Validação Windows — 2.0.0.7

Novo pacote de itens por modo, comparação de inventários e três faixas de PR.
CI 39007544851 aprovado, incluindo instalação/reinstalação/desinstalação e DLL
instalada renderizando sobre janela sintética. Código `3042968326042f87661bd0ebbf69ac94a6298a88`.
Resultados, hash, download e limites na [matriz atual](FUNCIONALIDADE_PARTIDAS.md#pacote-auditado--2007).

### Validação Windows — 2.0.0.9

Renderer CPU em processo separado; antigo renderer/DLL excluídos. CI
[39046087887](https://github.com/teuzimmmm/sexo2/actions/runs/39046087887) e
revalidação da janela instalada no CI
[39046631608](https://github.com/teuzimmmm/sexo2/actions/runs/39046631608) passaram.
Programa de `30334790675d64de4d950a798cb157714ead5e75`. Download, hashes e limites:
[OVERLAY_ISOLADO.md](OVERLAY_ISOLADO.md#pacote-validado--2009). Sem validação no LoL.
