# iris-species

Pipeline de dados que junta duas fontes pela espécie da flor: as 150 flores medidas do [Iris (Kaggle)](https://www.kaggle.com/datasets/uciml/iris) e a taxonomia e as ocorrências no mundo da [GBIF](https://www.gbif.org). Extração para `raw/` e camadas `raw`, `refined` e `analytics` no DuckDB (`iris.duckdb`), terminando em JOINs entre as fontes.

## Instalar

```bash
poetry install
```

## Rodar (a partir da raiz do projeto)

```bash
poetry run python -m iris_species.extracao
poetry run python -m iris_species.extracao_gbif
poetry run python -m iris_species.ingestao
poetry run python -m iris_species.transformacao
poetry run python -m iris_species.ui            # http://localhost:4213, Ctrl+C para encerrar
poetry run streamlit run src/iris_species/dashboard/app.py   # dashboard em http://localhost:8501
```

Ou use `make pipeline`, `make ui` e `make dashboard`.

## Testar

```bash
make check   # ruff, mypy, pytest (cobertura >= 50%) e mkdocs build --strict
```

## Documentação

`poetry run mkdocs serve`. O conteúdo fica em [docs/](docs/), e o dicionário de dados do dataset está em [doc_api.md](doc_api.md).
