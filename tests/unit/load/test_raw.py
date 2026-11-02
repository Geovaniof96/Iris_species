from pathlib import Path

import duckdb

from iris_species.load.raw import arquivos_faltando, ingerir, ler_csv_bruto


def test_arquivos_faltando_lista_ausentes(tmp_path: Path) -> None:
    assert arquivos_faltando(tmp_path) == ["Iris.csv"]
    (tmp_path / "Iris.csv").touch()
    assert arquivos_faltando(tmp_path) == []


def test_ler_csv_bruto_so_converte_campo_vazio_em_nulo(tmp_path: Path) -> None:
    caminho = tmp_path / "x.csv"
    caminho.write_text("a,b\nNA,\nnull,nan\n", encoding="utf-8")

    df = ler_csv_bruto(caminho)

    assert df["a"].tolist() == ["NA", "null"]
    assert df["b"].isna().tolist() == [True, False]
    assert df.loc[1, "b"] == "nan"


def test_ler_csv_bruto_nao_altera_texto_numerico(tmp_path: Path) -> None:
    caminho = tmp_path / "x.csv"
    caminho.write_text("Id,v\n001,5.10\n", encoding="utf-8")

    assert ler_csv_bruto(caminho).iloc[0].tolist() == ["001", "5.10"]


def test_ingerir_grava_tudo_como_varchar(con: duckdb.DuckDBPyConnection, csv_iris: Path) -> None:
    resultados = ingerir(con, csv_iris.parent)

    assert resultados == [("raw", "flores", 5)]
    tipos = con.execute(
        "SELECT column_name, data_type FROM information_schema.columns "
        "WHERE table_schema = 'raw' AND table_name = 'flores' ORDER BY ordinal_position"
    ).fetchall()
    assert [nome for nome, _ in tipos] == [
        "Id",
        "SepalLengthCm",
        "SepalWidthCm",
        "PetalLengthCm",
        "PetalWidthCm",
        "Species",
    ]
    assert {tipo for _, tipo in tipos} == {"VARCHAR"}
