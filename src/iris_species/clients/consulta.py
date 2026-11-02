"""Leitura de tabelas do DuckDB para DataFrame.

Fica fora de ``db.py`` porque a spec D2 limita aquele módulo a três funções e uma
constante.
"""

import duckdb
import pandas as pd


def ler_tabela(con: duckdb.DuckDBPyConnection, schema: str, tabela: str) -> pd.DataFrame:
    """Lê a tabela inteira, na ordem de inserção.

    Args:
        con: Conexão aberta com o DuckDB.
        schema: Schema da tabela.
        tabela: Nome da tabela.

    Returns:
        Conteúdo da tabela. O resultado é consumido por inteiro, o que libera a conexão.
    """
    return con.execute(f'SELECT * FROM "{schema}"."{tabela}"').df()
