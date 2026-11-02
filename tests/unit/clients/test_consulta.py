import duckdb

from iris_species.clients.consulta import ler_tabela


def test_ler_tabela_devolve_conteudo_na_ordem_de_insercao(
    con: duckdb.DuckDBPyConnection,
) -> None:
    con.execute("CREATE SCHEMA s")
    con.execute("CREATE TABLE s.t AS SELECT * FROM (VALUES (3), (1), (2)) v(x)")

    assert ler_tabela(con, "s", "t")["x"].tolist() == [3, 1, 2]
