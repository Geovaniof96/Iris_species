"""Carga das camadas ``refined`` e ``analytics`` a partir de ``raw.flores``.

Regras (extras à spec original):

C1. Lê ``raw.flores``, grava ``refined.flores`` e depois ``analytics.especies``,
    as duas com ``CREATE OR REPLACE`` (via ``gravar``).
    Por quê: reexecutar dá sempre o mesmo resultado, sem acumular linhas.

C2. A validação da refined roda antes de qualquer gravação.
    Por quê: se o contrato falhar, as camadas que já existiam ficam intactas.
"""

import duckdb

from iris_species.clients.consulta import ler_tabela
from iris_species.clients.db import criar_schema, gravar
from iris_species.load.raw import SCHEMA as SCHEMA_RAW
from iris_species.transform.analytics import resumir_especies
from iris_species.transform.refined import refinar_flores

TABELA_ORIGEM = "flores"
SCHEMA_REFINED = "refined"
TABELA_REFINED = "flores"
SCHEMA_ANALYTICS = "analytics"
TABELA_ANALYTICS = "especies"


def processar_camadas(con: duckdb.DuckDBPyConnection) -> list[tuple[str, str, int]]:
    """Gera ``refined.flores`` e ``analytics.especies`` a partir de ``raw.flores``.

    Args:
        con: Conexão aberta com o DuckDB, já com ``raw.flores`` gravada.

    Returns:
        ``(schema, tabela, contagem)`` de cada tabela gravada, com a contagem lida do banco.

    Raises:
        iris_species.transform.refined.ValidacaoError: Se a raw violar o contrato.
    """
    refined = refinar_flores(ler_tabela(con, SCHEMA_RAW, TABELA_ORIGEM))
    analytics = resumir_especies(refined)

    criar_schema(con, SCHEMA_REFINED)
    criar_schema(con, SCHEMA_ANALYTICS)
    return [
        (SCHEMA_REFINED, TABELA_REFINED, gravar(con, refined, SCHEMA_REFINED, TABELA_REFINED)),
        (
            SCHEMA_ANALYTICS,
            TABELA_ANALYTICS,
            gravar(con, analytics, SCHEMA_ANALYTICS, TABELA_ANALYTICS),
        ),
    ]
