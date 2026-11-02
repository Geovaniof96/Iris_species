from pathlib import Path

import duckdb
import pytest

from iris_species.load.camadas import ler_sql, processar_camadas
from iris_species.load.raw import ingerir
from iris_species.load.raw_gbif import ingerir_gbif
from iris_species.transform.refined import ValidacaoError

ESPERADO = [
    ("refined", "flores", 5),
    ("refined", "especies", 3),
    ("refined", "ocorrencias", 4),
    ("analytics", "especies", 3),
    ("analytics", "panorama", 3),
    ("analytics", "paises", 3),
]


def _ingerir_tudo(con: duckdb.DuckDBPyConnection, pasta_raw: Path) -> None:
    ingerir(con, pasta_raw)
    ingerir_gbif(con, pasta_raw)


def test_processar_camadas_grava_as_seis_tabelas_e_e_idempotente(
    con: duckdb.DuckDBPyConnection, pasta_raw_completa: Path
) -> None:
    _ingerir_tudo(con, pasta_raw_completa)

    assert processar_camadas(con) == ESPERADO
    assert processar_camadas(con) == ESPERADO


def test_panorama_junta_flores_taxonomia_e_ocorrencias(
    con: duckdb.DuckDBPyConnection, pasta_raw_completa: Path
) -> None:
    _ingerir_tudo(con, pasta_raw_completa)
    processar_camadas(con)

    setosa = con.execute(
        "SELECT nome_cientifico, gbif_codigo, quantidade_flores, quantidade_ocorrencias, "
        "quantidade_paises, pais_mais_frequente FROM analytics.panorama WHERE especie = 'setosa'"
    ).fetchall()
    assert setosa == [("Iris setosa L.", 5298796, 3, 2, 1, "Russian Federation")]


def test_paises_traz_media_da_petala_das_flores(
    con: duckdb.DuckDBPyConnection, pasta_raw_completa: Path
) -> None:
    _ingerir_tudo(con, pasta_raw_completa)
    processar_camadas(con)

    linhas = con.execute(
        "SELECT especie, pais_codigo, quantidade_ocorrencias, media_comprimento_petala_cm "
        "FROM analytics.paises ORDER BY especie"
    ).fetchall()
    assert [linha[:3] for linha in linhas] == [
        ("setosa", "RU", 2),
        ("versicolor", "US", 1),
        ("virginica", "CA", 1),
    ]
    assert [linha[3] for linha in linhas] == pytest.approx([1.4, 4.7, 6.0])


def test_processar_camadas_sem_raw_levanta_catalog_exception(
    con: duckdb.DuckDBPyConnection,
) -> None:
    with pytest.raises(duckdb.CatalogException):
        processar_camadas(con)


def test_processar_camadas_com_contrato_violado_nao_grava(
    con: duckdb.DuckDBPyConnection, pasta_raw_completa: Path
) -> None:
    (pasta_raw_completa / "Iris.csv").write_text(
        "Id,SepalLengthCm,SepalWidthCm,PetalLengthCm,PetalWidthCm,Species\n"
        "1,abc,3.5,1.4,0.2,Iris-setosa\n",
        encoding="utf-8",
    )
    _ingerir_tudo(con, pasta_raw_completa)

    with pytest.raises(ValidacaoError):
        processar_camadas(con)

    schemas = con.execute("SELECT schema_name FROM information_schema.schemata").fetchall()
    assert ("refined",) not in schemas


@pytest.mark.parametrize("nome", ["panorama", "paises"])
def test_ler_sql_encontra_as_consultas_do_pacote(nome: str) -> None:
    assert "JOIN" in ler_sql(nome)
