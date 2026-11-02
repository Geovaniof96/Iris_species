# Makefile — só chama `poetry run ...`
.PHONY: install lint format typecheck test docs check extracao ingestao transformacao pipeline ui

install:
	poetry install

lint:
	poetry run ruff check .
	poetry run ruff format --check .

format:
	poetry run ruff check . --fix
	poetry run ruff format .

typecheck:
	poetry run mypy src

test:
	poetry run pytest

docs:
	poetry run mkdocs build --strict

check: lint typecheck test docs

extracao:
	poetry run python -m iris_species.extracao

ingestao:
	poetry run python -m iris_species.ingestao

transformacao:
	poetry run python -m iris_species.transformacao

pipeline: extracao ingestao transformacao

ui:
	poetry run python -m iris_species.ui
