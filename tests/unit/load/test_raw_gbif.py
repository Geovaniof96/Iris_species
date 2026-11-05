import json
from pathlib import Path

import duckdb

from iris_species.load.raw_gbif import gbif_faltando, ingerir_gbif, ler_especies, ler_ocorrencias


def test_gbif_faltando_lista_especie_e_paginas_ausentes(tmp_path: Path) -> None:
    assert gbif_faltando(tmp_path) == [
        "gbif/especies/setosa.json",
        "gbif/ocorrencias/setosa/pagina_*.json",
        "gbif/especies/versicolor.json",
        "gbif/ocorrencias/versicolor/pagina_*.json",
        "gbif/especies/virginica.json",
        "gbif/ocorrencias/virginica/pagina_*.json",
    ]


def test_gbif_faltando_vazio_com_raw_completa(pasta_raw_completa: Path) -> None:
    assert gbif_faltando(pasta_raw_completa) == []


def test_ler_especies_guarda_documento_como_texto_intacto(pasta_raw_completa: Path) -> None:
    df = ler_especies(pasta_raw_completa)

    arquivo = pasta_raw_completa / "gbif" / "especies" / "setosa.json"
    assert df.loc[0, "documento"] == arquivo.read_text(encoding="utf-8")
    assert df["especie_arquivo"].tolist() == ["setosa", "versicolor", "virginica"]


def test_ler_ocorrencias_um_registro_por_linha_sem_alterar_valores(
    pasta_raw_completa: Path,
) -> None:
    df = ler_ocorrencias(pasta_raw_completa)

    assert len(df) == 4
    assert df.loc[0, "arquivo"] == "gbif/ocorrencias/setosa/pagina_000.json"
    registro = json.loads(df.loc[0, "registro"])
    assert (registro["key"], registro["decimalLatitude"], registro["stateProvince"]) == (
        1,
        45.5,
        None,
    )


def test_ingerir_gbif_grava_tudo_como_varchar(
    con: duckdb.DuckDBPyConnection, pasta_raw_completa: Path
) -> None:
    assert ingerir_gbif(con, pasta_raw_completa) == [
        ("raw", "gbif_especies", 3),
        ("raw", "gbif_ocorrencias", 4),
    ]
    tipos = con.execute(
        "SELECT DISTINCT data_type FROM information_schema.columns WHERE table_schema = 'raw'"
    ).fetchall()
    assert tipos == [("VARCHAR",)]
