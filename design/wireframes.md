# Templates de wireframe (ASCII)

Use estes moldes para propor telas. Eles mostram estrutura e hierarquia, não decisões visuais: cores,
tamanhos e nomes continuam pendentes até constarem em `docs/produto/decisoes.md`. Marque cada texto
ainda não aprovado com `‹proposta›`.

## Painel com cabeçalho e abas
```
┌──────────────────────────────────────────────┐
│ TÍTULO ‹proposta›                        [×] │
│ Aba 1   Aba 2   Aba 3                        │
├──────────────────────────────────────────────┤
│ conteúdo                                     │
└──────────────────────────────────────────────┘
```

## Lista densa (linha por item)
```
│ [ícone] Nome do item                 56,8  ⓘ │
│ [ícone] Nome do item                 53,9  ⓘ │
```
Coluna numérica alinhada à direita, com algarismos tabulares (D-007).

## Duas opções lado a lado
```
┌──────────────────────┐ ┌──────────────────────┐
│ OPÇÃO A ‹proposta›   │ │ OPÇÃO B ‹proposta›   │
│ valor principal      │ │ valor principal      │
│ detalhe              │ │ detalhe              │
└──────────────────────┘ └──────────────────────┘
```

## Seletor segmentado
```
[ Opção 1 | Opção 2 | Opção 3 ]
```

## Aviso em linha
```
│ O que aconteceu. O que fazer.                │
```
Uma linha, sem exclamação nem emoji (regras de linguagem pendentes em D-107).

## Checklist da proposta
- Componentes usados: só os do catálogo aprovado.
- Itens **novos** (nome, componente, texto, comportamento): listados explicitamente.
- Decisões pendentes afetadas: IDs de `decisoes.md`.
