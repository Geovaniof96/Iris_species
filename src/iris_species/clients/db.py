"""Conexão com o DuckDB do projeto, importada por todas as etapas do pipeline.

Spec (adaptada de ``pipeline/db.py`` para o layout ``src/`` da SKILL):

D1. Caminhos: ``PASTA_RAW`` e o ``iris.duckdb`` são resolvidos a partir da localização
    deste arquivo (a raiz do projeto, três pastas acima), nunca do diretório corrente.
    Por quê: um ``iris.duckdb`` vazio criado no lugar errado parece ingestão quebrada.

D2. Três funções e uma constante pública, nada mais. Este módulo não lê CSV, não conhece
    nome de tabela, não imprime nada e não converte tipo.
    Por quê: as etapas importam este arquivo. Regra de negócio escondida aqui valeria
    para todas sem aparecer em nenhuma spec.

D3. ``gravar`` registra o DataFrame como ``_gravar_df``, executa
    ``CREATE OR REPLACE TABLE "schema"."tabela" AS SELECT * FROM _gravar_df`` e remove o
    registro num ``finally``, mesmo se o ``CREATE`` falhar. Devolve ``count(*)`` lido do
    banco com ``fetchall()``.
    Por quê: a contagem na tela tem que ser a do que foi gravado, não a do que estava na
    memória. ``fetchall()`` e não ``fetchone()`` porque, no DuckDB 2.x, um resultado não
    consumido até o fim prende a conexão e o próximo ``gravar()`` falha.

D4. ``conectar()`` devolve a conexão aberta; quem chama é quem fecha. Não há conexão global.
    Por quê: conexão esquecida segura o lock do arquivo.
"""

from pathlib import Path

import duckdb
import pandas as pd

_RAIZ_PROJETO = Path(__file__).resolve().parents[3]
_CAMINHO_BANCO = _RAIZ_PROJETO / "iris.duckdb"

PASTA_RAW = _RAIZ_PROJETO / "raw"


def conectar() -> duckdb.DuckDBPyConnection:
    """Abre o ``iris.duckdb`` da raiz do projeto, criando o arquivo se ele não existir.

    Returns:
        Conexão aberta. Quem chama é responsável por fechá-la.
    """
    return duckdb.connect(str(_CAMINHO_BANCO))


def criar_schema(con: duckdb.DuckDBPyConnection, nome: str) -> None:
    """Cria o schema se ele ainda não existir.

    Args:
        con: Conexão aberta com o DuckDB.
        nome: Nome do schema.
    """
    con.execute(f'CREATE SCHEMA IF NOT EXISTS "{nome}"')


def gravar(con: duckdb.DuckDBPyConnection, df: pd.DataFrame, schema: str, tabela: str) -> int:
    """Grava o DataFrame substituindo a tabela e devolve a contagem lida do banco.

    Args:
        con: Conexão aberta com o DuckDB.
        df: Dados a gravar. Colunas ``str`` viram ``VARCHAR`` e nulos continuam ``NULL``.
        schema: Schema de destino (já existente).
        tabela: Nome da tabela de destino.

    Returns:
        Quantidade de linhas da tabela recém-gravada, segundo o banco.
    """
    destino = f'"{schema}"."{tabela}"'
    con.register("_gravar_df", df)
    try:
        con.execute(f"CREATE OR REPLACE TABLE {destino} AS SELECT * FROM _gravar_df")
    finally:
        con.unregister("_gravar_df")
    linhas = con.execute(f"SELECT count(*) FROM {destino}").fetchall()
    return int(linhas[0][0])
