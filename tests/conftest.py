from collections.abc import Iterator
from pathlib import Path

import duckdb
import pandas as pd
import pytest

from iris_species.clients import db

CABECALHO = "Id,SepalLengthCm,SepalWidthCm,PetalLengthCm,PetalWidthCm,Species\n"
LINHAS_CSV = (
    "1,5.1,3.5,1.4,0.2,Iris-setosa\n"
    "2,4.9,3.0,1.4,0.2,Iris-setosa\n"
    "3,4.9,3.0,1.4,0.2,Iris-setosa\n"
    "51,7.0,3.2,4.7,1.4,Iris-versicolor\n"
    "101,6.3,3.3,6.0,2.5,Iris-virginica\n"
)


@pytest.fixture
def con() -> Iterator[duckdb.DuckDBPyConnection]:
    conexao = duckdb.connect(":memory:")
    yield conexao
    conexao.close()


@pytest.fixture
def csv_iris(tmp_path: Path) -> Path:
    caminho = tmp_path / "Iris.csv"
    caminho.write_text(CABECALHO + LINHAS_CSV, encoding="utf-8")
    return caminho


@pytest.fixture
def raw_flores() -> pd.DataFrame:
    linhas = [linha.split(",") for linha in LINHAS_CSV.strip().splitlines()]
    return pd.DataFrame(linhas, columns=CABECALHO.strip().split(","), dtype=str)


@pytest.fixture
def projeto_tmp(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Aponta raw/ e iris.duckdb do pipeline para uma pasta temporária."""
    monkeypatch.setattr(db, "PASTA_RAW", tmp_path / "raw")
    monkeypatch.setattr(db, "_CAMINHO_BANCO", tmp_path / "iris.duckdb")
    return tmp_path
