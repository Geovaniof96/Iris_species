# Arquitetura

```
Kaggle (uciml/iris)
   │  extracao        kagglehub, download atômico
   ▼
raw/Iris.csv          arquivo exatamente como chegou
   │  ingestao        pandas (dtype=str)
   ▼
raw.flores            6 colunas VARCHAR, sem nenhuma correção
   │  transformacao   tipagem + validação de contrato
   ▼
refined.flores        id, 4 medidas DOUBLE, especie, duplicada
   │                  agregação por espécie
   ▼
analytics.especies    quantidade, duplicadas, média/mín/máx de cada medida
```

Cada etapa é reexecutável isoladamente e recria as tabelas com `CREATE OR REPLACE`.
A extração não abre o banco, e a ingestão e a transformação não acessam a rede.

## Módulos

| Módulo | Responsabilidade |
|---|---|
| `clients/db.py` | Conexão com o `iris.duckdb`, criação de schema e gravação (`PASTA_RAW`, `conectar`, `criar_schema`, `gravar`) |
| `clients/consulta.py` | Leitura de tabela para DataFrame |
| `extract/kaggle.py` | Download do `Iris.csv` para `raw/` |
| `load/raw.py` | Leitura bruta do CSV e carga do schema `raw` |
| `load/camadas.py` | Carga de `refined` e `analytics` |
| `transform/refined.py` | Tipagem, renomeação, padronização da espécie, duplicatas e contrato (funções puras) |
| `transform/analytics.py` | Resumo por espécie (função pura) |
| `utils/saida.py` | utf-8, logging na tela e formatação de números |
| `extracao.py`, `ingestao.py`, `transformacao.py` | Entrypoints: só orquestram |
| `ui.py` | Interface do DuckDB; não importa nada do pacote |

## Camadas

### raw.flores

O dado como chegou: as colunas originais do CSV, todas `VARCHAR`. Só o campo vazio
vira `NULL`; `"NA"`, `"null"` e `"nan"` continuam texto.

### refined.flores

| Coluna | Tipo | Origem |
|---|---|---|
| `id` | BIGINT | `Id` |
| `comprimento_sepala_cm` | DOUBLE | `SepalLengthCm` |
| `largura_sepala_cm` | DOUBLE | `SepalWidthCm` |
| `comprimento_petala_cm` | DOUBLE | `PetalLengthCm` |
| `largura_petala_cm` | DOUBLE | `PetalWidthCm` |
| `especie` | VARCHAR | `Species` sem o prefixo `Iris-` |
| `duplicada` | BOOLEAN | `true` em todas as linhas cujas medidas e espécie se repetem |

Nenhum valor medido é corrigido e nenhuma linha é removida. As linhas Id 35 e 38, que
têm erros conhecidos em relação ao artigo de Fisher, ficam como vieram. Hoje, as linhas
10, 35, 38, 102 e 143 têm `duplicada = true`.

Contrato: `id` único e não nulo, medidas não nulas e `> 0`, `especie` em
{setosa, versicolor, virginica}. Se houver violação, nada é gravado.

### analytics.especies

Uma linha por espécie, com `quantidade`, `quantidade_duplicadas` e
`media_*`, `min_*` e `max_*` para cada medida, sem arredondamento.
