import subprocess
import sys
from pathlib import Path

import duckdb
import pandas as pd
import pytest

from iris_species.clients import db

RAIZ = Path(__file__).resolve().parents[3]


def test_caminhos_resolvidos_a_partir_da_raiz_do_projeto() -> None:
    assert (RAIZ / "pyproject.toml").is_file()
    assert db.PASTA_RAW == RAIZ / "raw"
    assert db._CAMINHO_BANCO == RAIZ / "iris.duckdb"


def test_importar_db_nao_cria_arquivo(tmp_path: Path) -> None:
    subprocess.run(
        [sys.executable, "-c", "import iris_species.clients.db"], cwd=tmp_path, check=True
    )
    assert list(tmp_path.iterdir()) == []


def test_conectar_cria_banco_no_caminho_do_projeto_e_nao_na_pasta_corrente(
    projeto_tmp: Path, tmp_path_factory: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    outra_pasta = tmp_path_factory.mktemp("cwd")
    monkeypatch.chdir(outra_pasta)

    db.conectar().close()

    assert (projeto_tmp / "iris.duckdb").is_file()
    assert list(outra_pasta.iterdir()) == []


def test_criar_schema_e_idempotente(con: duckdb.DuckDBPyConnection) -> None:
    db.criar_schema(con, "raw")
    db.criar_schema(con, "raw")
    schemas = con.execute(
        "SELECT schema_name FROM information_schema.schemata WHERE schema_name = 'raw'"
    ).fetchall()
    assert schemas == [("raw",)]


def test_gravar_devolve_contagem_do_banco_mesmo_reexecutando(
    con: duckdb.DuckDBPyConnection,
) -> None:
    db.criar_schema(con, "raw")
    df = pd.DataFrame({"a": ["1", "2", "3"]})

    assert db.gravar(con, df, "raw", "t") == 3
    assert db.gravar(con, df, "raw", "t") == 3


def test_gravar_mantem_nulo_como_null_e_nao_deixa_view(con: duckdb.DuckDBPyConnection) -> None:
    db.criar_schema(con, "raw")
    df = pd.DataFrame({"texto": ["x", None, "z"]}, dtype=str)

    db.gravar(con, df, "raw", "t")

    assert con.execute('SELECT count(*) FROM raw.t WHERE "texto" IS NULL').fetchall() == [(1,)]
    tipo = con.execute(
        "SELECT data_type FROM information_schema.columns WHERE table_name = 't'"
    ).fetchall()
    assert tipo == [("VARCHAR",)]
    assert con.execute("SELECT count(*) FROM duckdb_views() WHERE NOT internal").fetchall() == [
        (0,)
    ]


def test_gravar_remove_registro_mesmo_quando_create_falha(
    con: duckdb.DuckDBPyConnection,
) -> None:
    with pytest.raises(duckdb.CatalogException):
        db.gravar(con, pd.DataFrame({"a": [1]}), "schema_inexistente", "t")

    with pytest.raises(duckdb.CatalogException):
        con.execute("SELECT * FROM _gravar_df")
