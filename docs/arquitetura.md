# Arquitetura

O pipeline junta duas fontes pela espécie da flor:

- **Kaggle `uciml/iris`**: 150 flores medidas (sépala e pétala).
- **GBIF** (api.gbif.org): taxonomia de cada espécie e até 3.000 ocorrências
  georreferenciadas por espécie.

```
Kaggle Iris.csv ───────► raw.flores ───────────► refined.flores ──────┐
GBIF species/match ───► raw.gbif_especies ────► refined.especies ────┼─► analytics.especies
GBIF occurrence/search ► raw.gbif_ocorrencias ─► refined.ocorrencias ─┼─► analytics.panorama (JOIN)
                                                                     └─► analytics.paises   (JOIN)
```

Cada etapa é reexecutável isoladamente e recria as tabelas com `CREATE OR REPLACE`.
As extrações não abrem o banco, e a ingestão e a transformação não acessam a rede.

## Módulos

| Módulo | Responsabilidade |
|---|---|
| `clients/db.py` | Conexão com o `iris.duckdb`, criação de schema e gravação |
| `clients/consulta.py` | Leitura de tabela para DataFrame |
| `extract/kaggle.py` | Download do `Iris.csv` para `raw/` |
| `extract/gbif.py` | Download da taxonomia e das ocorrências para `raw/gbif/` |
| `load/raw.py`, `load/raw_gbif.py` | Carga do schema `raw`, tudo como texto |
| `load/camadas.py` | Carga de `refined` e `analytics`, e execução dos JOINs em SQL |
| `transform/refined.py`, `transform/gbif.py` | Tipagem, validação e padronização (funções puras) |
| `transform/analytics.py` | Resumo das flores por espécie (função pura) |
| `transform/sql/*.sql` | Os JOINs entre as fontes |
| `utils/saida.py` | utf-8, logging na tela e formatação de números |
| `extracao.py`, `extracao_gbif.py`, `ingestao.py`, `transformacao.py` | Entrypoints: só orquestram |
| `ui.py` | Interface do DuckDB; não importa nada do pacote |
| `dashboard/dados.py` | Leitura somente leitura das tabelas do dashboard |
| `dashboard/kpis.py` | KPIs, filtros e agregações do dashboard (funções puras) |
| `dashboard/graficos.py` | Figuras Plotly, com uma cor fixa por espécie (funções puras) |
| `dashboard/app.py` | Página Streamlit: só orquestra |

## Camadas

### raw

O dado como chegou, tudo `VARCHAR`.

| Tabela | Conteúdo |
|---|---|
| `raw.flores` | as colunas originais do CSV |
| `raw.gbif_especies` | `especie_arquivo`, `arquivo` e `documento` (o JSON da resposta, inteiro) |
| `raw.gbif_ocorrencias` | `especie_arquivo`, `arquivo` e `registro` (um JSON por ocorrência) |

### refined.flores

| Coluna | Tipo | Origem |
|---|---|---|
| `id` | BIGINT | `Id` |
| `comprimento_sepala_cm`, `largura_sepala_cm` | DOUBLE | `SepalLengthCm`, `SepalWidthCm` |
| `comprimento_petala_cm`, `largura_petala_cm` | DOUBLE | `PetalLengthCm`, `PetalWidthCm` |
| `especie` | VARCHAR | `Species` sem o prefixo `Iris-` |
| `duplicada` | BOOLEAN | `true` em todas as linhas cujas medidas e espécie se repetem |

Nenhum valor medido é corrigido e nenhuma linha é removida.

### refined.especies (GBIF)

`especie`, `gbif_codigo`, `nome_cientifico` (com autor, ex.: `Iris setosa Pall. ex Link`),
`familia`, `genero` e `status`. Exige exatamente as três espécies com correspondência exata.

### refined.ocorrencias (GBIF)

`gbif_id`, `especie`, `pais_codigo`, `pais`, `estado`, `ano`, `mes`, `latitude`,
`longitude`, `tipo_registro` e `licenca`. Um `gbif_id` repetido (o mesmo registro em duas
páginas) é removido, e campos ausentes na GBIF continuam `NULL`.

A `especie` é a consultada: a busca por código de táxon inclui subespécies e sinônimos.

### analytics

| Tabela | Linhas | O que tem |
|---|---|---|
| `analytics.especies` | 3 | média, mínimo e máximo das medidas das flores |
| `analytics.panorama` | 3 | taxonomia + medidas + ocorrências (quantidade, países, país mais frequente, anos, latitude média) |
| `analytics.paises` | 1 por espécie e país | ocorrências por país + nome científico + média da pétala |

`panorama` e `paises` são os JOINs entre as fontes, em `transform/sql/panorama.sql` e
`transform/sql/paises.sql`.

## Limites conhecidos

- A GBIF devolve primeiro os registros mais recentes. Com o limite de 3.000 por espécie,
  versicolor e virginica (que têm mais de 3.000 registros) ficam concentradas nos últimos
  anos; a setosa, com cerca de 4.200, cobre um período maior.
- Os dados da GBIF mudam com o tempo; duas extrações em dias diferentes podem trazer
  registros diferentes.
- Cada ocorrência tem a própria licença (coluna `licenca`). Ao publicar resultados,
  cite a GBIF e respeite as licenças CC BY-NC dos registros que as tiverem.
