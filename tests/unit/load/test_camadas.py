from pathlib import Path

import duckdb
import pytest

from iris_species.load.camadas import processar_camadas
from iris_species.load.raw import ingerir
from iris_species.transform.refined import ValidacaoError


def test_processar_camadas_grava_refined_e_analytics(
    con: duckdb.DuckDBPyConnection, csv_iris: Path
) -> None:
    ingerir(con, csv_iris.parent)

    assert processar_camadas(con) == [("refined", "flores", 5), ("analytics", "especies", 3)]
    assert processar_camadas(con) == [("refined", "flores", 5), ("analytics", "especies", 3)]


def test_processar_camadas_sem_raw_levanta_catalog_exception(
    con: duckdb.DuckDBPyConnection,
) -> None:
    with pytest.raises(duckdb.CatalogException):
        processar_camadas(con)


def test_processar_camadas_com_contrato_violado_nao_grava(
    con: duckdb.DuckDBPyConnection, tmp_path: Path
) -> None:
    (tmp_path / "Iris.csv").write_text(
        "Id,SepalLengthCm,SepalWidthCm,PetalLengthCm,PetalWidthCm,Species\n"
        "1,abc,3.5,1.4,0.2,Iris-setosa\n",
        encoding="utf-8",
    )
    ingerir(con, tmp_path)

    with pytest.raises(ValidacaoError):
        processar_camadas(con)

    schemas = con.execute("SELECT schema_name FROM information_schema.schemata").fetchall()
    assert ("refined",) not in schemas
