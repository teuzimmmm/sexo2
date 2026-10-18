# Documentação do SEXO2

Índice do que existe em `docs/`, `design/` e na raiz. Para regras de trabalho, comece por
[`CLAUDE.md`](../CLAUDE.md). Como a documentação é organizada e mantida:
[organizacao/documentacao.md](organizacao/documentacao.md).

## Por onde começar

| Preciso de... | Leia |
|---|---|
| Saber o que foi decidido (nomes, interface, comportamento) | [produto/decisoes.md](produto/decisoes.md), a fonte única |
| Termos aprovados da interface | [produto/glossario.md](produto/glossario.md) |
| Saber o que não pode quebrar e qual teste cobre | [comportamentos.md](comportamentos.md) |
| Ver o estado dos marcos | [ROADMAP.md](ROADMAP.md) |
| Entender por que a arquitetura é assim | [adr/README.md](adr/README.md) |
| Medir desempenho antes e depois de uma mudança | [MEDICAO.md](MEDICAO.md) |
| Validar uma entrega no Windows com o LoL real | [VALIDACAO_WINDOWS.md](VALIDACAO_WINDOWS.md) |
| Entender atualização, assinatura e publicação | [ATUALIZACOES.md](ATUALIZACOES.md) |
| Propor ou mexer na interface | skill `sexo2-ui`, [../design/wireframes.md](../design/wireframes.md), [../design/propostas/sexo2-v1/README.md](../design/propostas/sexo2-v1/README.md) |
| Usar a biblioteca LoLalytics | [lolalytics/README.md](lolalytics/README.md) |

## Vivos (mantidos junto com o código)

| Documento | Para quê |
|---|---|
| [produto/decisoes.md](produto/decisoes.md) | Decisões aprovadas, pendentes e rejeitadas. |
| [produto/glossario.md](produto/glossario.md) | Termos da interface e identificador interno. |
| [comportamentos.md](comportamentos.md) | Funções protegidas, onde estão e qual teste as cobre. |
| [ROADMAP.md](ROADMAP.md) | Marcos, estado de cada um e pendências técnicas. |
| [adr/README.md](adr/README.md) | Decisões de arquitetura (ADR-1 em diante). |
| [MEDICAO.md](MEDICAO.md) | Protocolo da linha de base de desempenho. |
| [VALIDACAO_WINDOWS.md](VALIDACAO_WINDOWS.md) | Roteiro de testes que só rodam no cliente real. |
| [ATUALIZACOES.md](ATUALIZACOES.md) | Atualizador assinado, central privada, publicação e compatibilidade. |
| [../design/wireframes.md](../design/wireframes.md) | Moldes ASCII para propor telas. |
| [../design/fonts/ORIGEM.md](../design/fonts/ORIGEM.md) | Origem e licença das fontes. |
| [../design/propostas/sexo2-v1/README.md](../design/propostas/sexo2-v1/README.md) | Protótipo estático da interface. |

## Notas de entrega e investigação

Registram o que foi feito ou descoberto numa versão ou pedido. Os números de versão e caminhos são
os da época; em conflito, vale o código e depois os documentos vivos.

| Documento | Assunto |
|---|---|
| [ARENA_BRAVURA.md](ARENA_BRAVURA.md) | Detecção do Bravura no Arena e troca de skin (1.6.1). |
| [PERFORMANCE_1_6_3.md](PERFORMANCE_1_6_3.md) | Investigação e alterações de desempenho da 1.6.3. |
| [MODS_E_AIRDROP.md](MODS_E_AIRDROP.md) | Biblioteca de mods em lote e transferência pela sala (pedido de 13/10/2026). |

## LoLalytics (`docs/lolalytics/`)

Ponto de entrada: [lolalytics/README.md](lolalytics/README.md). O restante da pasta está classificado em
[organizacao/documentacao.md](organizacao/documentacao.md): referência de uso, planos de 16/10/2026 já
executados, validações, investigações HTTP e os JSON de evidência.

## Arquivo (`docs/arquivo/`)

Documentos superados, mantidos como histórico. Cada um começa com uma linha dizendo por que foi
arquivado.

| Documento | Motivo |
|---|---|
| [arquivo/DECISOES.md](arquivo/DECISOES.md) | Histórico da entrega r6, anterior ao registro de decisões. |
| [arquivo/PROJETO_SEXO2.md](arquivo/PROJETO_SEXO2.md) | Plano inicial de 13/10/2026. |
| [arquivo/PLANO_CINCO_TAREFAS.md](arquivo/PLANO_CINCO_TAREFAS.md) | Plano e avanços até a 1.6.4. |

## Verificar os links

```
python scripts/check_doc_links.py
```
