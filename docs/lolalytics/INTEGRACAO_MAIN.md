# API LoLalytics na main — 17/10/2026

Autorização: levar somente a API funcional à main, mantendo parado o trabalho
no overlay e no instalador. Base: main 64dae18; origem: 814815a.

Plano e contrato antes da integração:
1. Copiar o pacote independente lolalytics, seus testes/fixtures sanitizados,
   probes explícitos e documentação. Incluir builds, matchups e risco local.
2. Não transferir adaptadores da aplicação, configurações, Pengu, importador LCU,
   overlay, instalador, atualizador nem binários. Esses componentes não são
   dependências do coletor e não fazem parte desta autorização.
3. Manter o aplicativo existente e requirements.txt. A biblioteca usa somente
   requests (já presente) e a biblioteca padrão; não muda fluxos de inicialização.
4. Revisar o diff, executar testes offline na árvore isolada e amostras públicas
   limitadas sem credenciais. Registrar falhas reais sem preencher lacunas.
5. Criar um único commit baseado na main e fazer push normal, sem force ou tag.
   O workflow da main apenas valida; não compila ou publica releases.

Conclusão exige diff restrito, testes pertinentes aprovados, limitações explícitas
e confirmação do mesmo commit na main remota. Testes offline não comprovam o
site atual nem qualquer importação/overlay no LoL.

## Resultado da revisão

- Os 15 módulos do pacote são idênticos à origem revisada 814815a. Sem import
  de módulos da aplicação/LCU/Pengu. A árvore base do aplicativo permanece igual.
- 156 testes offline da API passaram, incluindo Ahri/Jinx Swiftplay extraídos
  das fixtures reais sem depender do adaptador comunitário de Mayhem.
- 373 regressões passaram em Python 3.12/Linux (uma ignorada pelo próprio teste).
  O módulo test_startup_policy foi excluído dessa execução por depender de
  ctypes.windll; a suíte completa do Windows continua no workflow da main.
- Cinco cenários reais passaram, 7 GETs, uma tentativa por GET, sem
  credenciais ou cache em disco: builds Ahri/middle condicionadas à runa, Jinx
  ARAM, popularidade Ahri/Arena, summaries Jinx/Swiftplay e matchup Ahri×Annie.
  Patch resolvido 16.20 em todos. Relatório: [main-live-2026-10-17.json](main-live-2026-10-17.json).

Reprodução das consultas na raiz do checkout:

```sh
python -m unittest discover -s tests -p 'test_lolalytics*.py' -q
python -m lolalytics ahri --lane middle --builds
python -m lolalytics jinx --mode aram
python -m lolalytics ahri --mode arena --recommend
python -m lolalytics jinx --mode swift --builds
python -m lolalytics ahri --lane middle --matchup --opponent annie --opponent-lane middle
```

Limites preservados: Arena usa pick rate, sem WR de itens/aprimoramentos; Swiftplay
usa summaries gerais, sem condicionamento por runa. A fonte Mayhem comunitária
não integra este pacote. Sugestões não comprovam WR conjunta das nove runas nem
uma sequência conjunta de seis itens. Não há escrita no cliente do LoL.
Nenhuma versão, binário, workflow ou instalador foi alterado.
