# iris-species

Pipeline de dados sobre o dataset público [Iris do Kaggle](https://www.kaggle.com/datasets/uciml/iris).

1. **Extração**: baixa o `Iris.csv` para `raw/`, intacto.
2. **Ingestão**: grava o arquivo no schema `raw` do `iris.duckdb`, tudo como texto.
3. **Transformação**: gera `refined.flores` (dados tipados e validados) e `analytics.especies` (resumo por espécie).
4. **UI**: abre a interface do DuckDB no navegador para consultar as tabelas.

Veja o [Guia de uso](guia.md) para rodar e a [Arquitetura](arquitetura.md) para as regras de cada camada.
