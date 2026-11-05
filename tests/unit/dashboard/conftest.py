from pathlib import Path

import duckdb
import pytest

FLORES = """
    SELECT * FROM (VALUES
        (1, 5.1, 3.5, 1.4, 0.2, 'setosa', false),
        (51, 7.0, 3.2, 4.7, 1.4, 'versicolor', false),
        (101, 6.3, 3.3, 6.0, 2.5, 'virginica', false)
    ) AS t(id, comprimento_sepala_cm, largura_sepala_cm, comprimento_petala_cm,
           largura_petala_cm, especie, duplicada)
"""
OCORRENCIAS = """
    SELECT * FROM (VALUES
        (1, 'setosa', 'RU', 'Russia', NULL, 2020, 5, 55.0, 37.0, 'HUMAN_OBSERVATION', 'cc'),
        (2, 'virginica', 'US', 'USA', 'Ohio', 2024, 6, 40.0, -82.0, 'HUMAN_OBSERVATION', 'cc')
    ) AS t(gbif_id, especie, pais_codigo, pais, estado, ano, mes, latitude, longitude,
           tipo_registro, licenca)
"""
PANORAMA = """
    SELECT * FROM (VALUES
        ('setosa', 'Iris setosa', 1.4, 1),
        ('versicolor', 'Iris versicolor', 4.7, NULL),
        ('virginica', 'Iris virginica', 6.0, 1)
    ) AS t(especie, nome_cientifico, media_comprimento_petala_cm, quantidade_ocorrencias)
"""


@pytest.fixture
def banco_dashboard(tmp_path: Path) -> Path:
    """``iris.duckdb`` temporário com as três tabelas que o dashboard lê."""
    caminho = tmp_path / "iris.duckdb"
    con = duckdb.connect(str(caminho))
    try:
        for schema in ("refined", "analytics"):
            con.execute(f"CREATE SCHEMA {schema}")
        con.execute(f"CREATE TABLE refined.flores AS {FLORES}")
        con.execute(f"CREATE TABLE refined.ocorrencias AS {OCORRENCIAS}")
        con.execute(f"CREATE TABLE analytics.panorama AS {PANORAMA}")
    finally:
        con.close()
    return caminho
