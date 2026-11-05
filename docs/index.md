# iris-species

Pipeline de dados sobre o dataset público [Iris do Kaggle](https://www.kaggle.com/datasets/uciml/iris).

1. **Extração**: baixa o `Iris.csv` do Kaggle e a taxonomia e as ocorrências da GBIF para `raw/`, intactos.
2. **Ingestão**: grava os arquivos no schema `raw` do `iris.duckdb`, tudo como texto.
3. **Transformação**: gera a `refined` (dados tipados e validados) e a `analytics`, com os JOINs entre as fontes (`panorama` e `paises`).
4. **UI**: abre a interface do DuckDB no navegador para consultar as tabelas.

Veja o [Guia de uso](guia.md) para rodar e a [Arquitetura](arquitetura.md) para as regras de cada camada.
