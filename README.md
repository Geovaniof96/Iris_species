# iris-species

Pipeline de dados do dataset [Iris (Kaggle)](https://www.kaggle.com/datasets/uciml/iris): extração para `raw/` e camadas `raw`, `refined` e `analytics` no DuckDB (`iris.duckdb`).

## Instalar

```bash
poetry install
```

## Rodar (a partir da raiz do projeto)

```bash
poetry run python -m iris_species.extracao
poetry run python -m iris_species.ingestao
poetry run python -m iris_species.transformacao
poetry run python -m iris_species.ui            # http://localhost:4213, Ctrl+C para encerrar
```

Ou use `make pipeline` e `make ui`.

## Testar

```bash
make check   # ruff, mypy, pytest (cobertura >= 50%) e mkdocs build --strict
```

## Documentação

`poetry run mkdocs serve`. O conteúdo fica em [docs/](docs/), e o dicionário de dados do dataset está em [doc_api.md](doc_api.md).
