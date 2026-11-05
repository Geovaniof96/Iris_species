import json
from collections.abc import Callable, Iterator
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


def documento_especie(especie: str, codigo: int) -> dict[str, object]:
    return {
        "usageKey": codigo,
        "scientificName": f"Iris {especie} L.",
        "canonicalName": f"Iris {especie}",
        "rank": "SPECIES",
        "status": "ACCEPTED",
        "family": "Iridaceae",
        "genus": "Iris",
        "matchType": "EXACT",
    }


def ocorrencia(gbif_id: int, pais_codigo: str, pais: str, ano: int = 2020) -> dict[str, object]:
    return {
        "key": gbif_id,
        "countryCode": pais_codigo,
        "country": pais,
        "stateProvince": None,
        "year": ano,
        "month": 5,
        "decimalLatitude": 45.5,
        "decimalLongitude": -73.25,
        "basisOfRecord": "HUMAN_OBSERVATION",
        "license": "http://creativecommons.org/licenses/by/4.0/legalcode",
    }


OCORRENCIAS_PADRAO = {
    "setosa": [
        ocorrencia(1, "RU", "Russian Federation"),
        ocorrencia(2, "RU", "Russian Federation"),
    ],
    "versicolor": [ocorrencia(3, "US", "United States of America")],
    "virginica": [ocorrencia(4, "CA", "Canada", ano=2024)],
}
CODIGOS = {"setosa": 5298796, "versicolor": 5298019, "virginica": 5298008}


def escrever_gbif(
    pasta_raw: Path, ocorrencias: dict[str, list[dict[str, object]]] | None = None
) -> None:
    """Grava raw/gbif no formato da extração, como a API devolveria."""
    for especie, registros in (ocorrencias or OCORRENCIAS_PADRAO).items():
        arquivo = pasta_raw / "gbif" / "especies" / f"{especie}.json"
        arquivo.parent.mkdir(parents=True, exist_ok=True)
        arquivo.write_text(json.dumps(documento_especie(especie, CODIGOS[especie])), "utf-8")
        pagina = pasta_raw / "gbif" / "ocorrencias" / especie / "pagina_000.json"
        pagina.parent.mkdir(parents=True, exist_ok=True)
        pagina.write_text(
            json.dumps({"count": len(registros), "endOfRecords": True, "results": registros}),
            "utf-8",
        )


@pytest.fixture
def pasta_raw_completa(tmp_path: Path) -> Path:
    """raw/ com o Iris.csv de exemplo e a GBIF com 4 ocorrências."""
    pasta = tmp_path / "raw"
    pasta.mkdir()
    (pasta / "Iris.csv").write_text(CABECALHO + LINHAS_CSV, encoding="utf-8")
    escrever_gbif(pasta)
    return pasta


@pytest.fixture
def gravar_gbif() -> Callable[..., None]:
    """Devolve :func:`escrever_gbif` para testes que montam a raw/ na hora."""
    return escrever_gbif
