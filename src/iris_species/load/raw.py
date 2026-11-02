"""Carga dos arquivos de ``raw/`` para o schema ``raw`` do DuckDB.

Spec:

I1. Schema ``raw``. Mapa arquivo → tabela, completo e literal: ``Iris.csv`` → ``flores``.
    Por quê: o nome em português é o vocabulário usado nas consultas.

I2. Nenhuma conversão de tipo, nenhuma linha descartada ou deduplicada, nenhum nome de
    coluna alterado, nenhum valor corrigido, preenchido ou normalizado. Nulo continua nulo.
    Por quê: a fronteira entre "o dado que chegou" e "o dado que eu decidi" fica na
    passagem de raw para refined.

I3. Tabela recriada (``CREATE OR REPLACE``, via ``gravar``), nunca acrescentada.

I4. ``pd.read_csv`` com ``encoding="utf-8"``, ``dtype=str``, ``keep_default_na=False`` e
    ``na_values=[""]``: só o campo vazio vira nulo; ``"NA"``, ``"null"``, ``"nan"`` etc.
    continuam texto.
    Por quê: transformar ``"NA"`` em nulo seria corrigir valor (I2).

I5. Toda coluna entra como texto, sem inferência.
    Por quê: a inferência decide sozinha e sem aviso; a conversão acontece na refined,
    onde é uma decisão registrada.
"""

from collections.abc import Mapping
from pathlib import Path
from types import MappingProxyType

import duckdb
import pandas as pd

from iris_species.clients.db import criar_schema, gravar

SCHEMA = "raw"
MAPA_ARQUIVOS: Mapping[str, str] = MappingProxyType({"Iris.csv": "flores"})


def arquivos_faltando(pasta: Path) -> list[str]:
    """Lista os arquivos do mapa que não existem na pasta.

    Args:
        pasta: Pasta onde os arquivos deveriam estar.

    Returns:
        Nomes dos arquivos ausentes, na ordem do mapa.
    """
    return [arquivo for arquivo in MAPA_ARQUIVOS if not (pasta / arquivo).is_file()]


def ler_csv_bruto(caminho: Path) -> pd.DataFrame:
    """Lê o CSV com todas as colunas como texto; só o campo vazio vira nulo.

    Args:
        caminho: Arquivo CSV.

    Returns:
        DataFrame sem nenhuma conversão de tipo.
    """
    return pd.read_csv(caminho, encoding="utf-8", dtype=str, keep_default_na=False, na_values=[""])


def ingerir(con: duckdb.DuckDBPyConnection, pasta: Path) -> list[tuple[str, str, int]]:
    """Grava cada arquivo do mapa na sua tabela do schema ``raw``.

    Args:
        con: Conexão aberta com o DuckDB.
        pasta: Pasta com os arquivos brutos.

    Returns:
        ``(schema, tabela, contagem)`` para cada tabela, com a contagem lida do banco.
    """
    criar_schema(con, SCHEMA)
    return [
        (SCHEMA, tabela, gravar(con, ler_csv_bruto(pasta / arquivo), SCHEMA, tabela))
        for arquivo, tabela in MAPA_ARQUIVOS.items()
    ]
