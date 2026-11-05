"""Leitura, somente leitura, das tabelas que o dashboard consome.

Regras:

P1. Abre o ``iris.duckdb`` com ``read_only=True`` e fecha a conexão antes de devolver.
    Por quê: o dashboard nunca escreve, e uma conexão aberta seguraria o lock do arquivo
    e faria a ingestão falhar.

P2. Não cria banco: se o arquivo não existir, se estiver em uso por outro processo ou se
    faltar tabela, gera :class:`DadosIndisponiveisError` com o que rodar antes.
    Por isso não usa ``conectar()``, que cria o arquivo.
"""

from dataclasses import dataclass
from pathlib import Path

import duckdb
import pandas as pd

from iris_species.clients.consulta import ler_tabela

CAMINHO_BANCO = Path(__file__).resolve().parents[3] / "iris.duckdb"


class DadosIndisponiveisError(Exception):
    """O banco ou as tabelas do dashboard não estão disponíveis."""


@dataclass(frozen=True)
class DadosPainel:
    """Tabelas lidas do banco para o dashboard."""

    flores: pd.DataFrame
    ocorrencias: pd.DataFrame
    panorama: pd.DataFrame


def carregar_dados(caminho: Path | None = None) -> DadosPainel:
    """Lê ``refined.flores``, ``refined.ocorrencias`` e ``analytics.panorama``.

    Args:
        caminho: Arquivo do DuckDB. Padrão: o ``iris.duckdb`` da raiz do projeto.

    Returns:
        As três tabelas como DataFrame.

    Raises:
        DadosIndisponiveisError: Se o banco não existir, estiver bloqueado ou faltar tabela.
    """
    caminho = caminho or CAMINHO_BANCO
    if not caminho.is_file():
        raise DadosIndisponiveisError(
            f"banco não encontrado em {caminho}. Rode antes: make pipeline"
        )
    try:
        con = duckdb.connect(str(caminho), read_only=True)
    except duckdb.IOException as exc:
        raise DadosIndisponiveisError(
            "o banco está em uso por outro processo (ingestão, transformação ou UI do DuckDB)."
            " Feche-o e recarregue a página"
        ) from exc
    try:
        return DadosPainel(
            flores=ler_tabela(con, "refined", "flores"),
            ocorrencias=ler_tabela(con, "refined", "ocorrencias"),
            panorama=ler_tabela(con, "analytics", "panorama"),
        )
    except duckdb.CatalogException as exc:
        raise DadosIndisponiveisError(
            "tabela da refined/analytics não encontrada. Rode antes: make transformacao"
        ) from exc
    finally:
        con.close()
