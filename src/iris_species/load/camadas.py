"""Carga das camadas ``refined`` e ``analytics`` a partir do schema ``raw``.

Regras (extras à spec original):

C1. Lê ``raw.flores``, ``raw.gbif_especies`` e ``raw.gbif_ocorrencias`` e grava, nesta
    ordem: ``refined.flores``, ``refined.especies``, ``refined.ocorrencias``,
    ``analytics.especies``, ``analytics.panorama`` e ``analytics.paises``, todas com
    ``CREATE OR REPLACE`` (via ``gravar``).
    Por quê: reexecutar dá sempre o mesmo resultado, sem acumular linhas.

C2. Todas as transformações em pandas (e suas validações) rodam antes da primeira
    gravação.
    Por quê: se um contrato falhar, as camadas que já existiam ficam intactas.

C3. ``analytics.panorama`` e ``analytics.paises`` são consultas SQL com JOIN entre as
    duas fontes (``transform/sql/*.sql``), executadas depois que as tabelas de que
    dependem foram gravadas.
    Por quê: o JOIN é o objetivo do projeto e fica legível e reaproveitável em SQL.
"""

import logging
from importlib import resources

import duckdb

from iris_species.clients.consulta import ler_tabela
from iris_species.clients.db import criar_schema, gravar
from iris_species.load.raw import SCHEMA as SCHEMA_RAW
from iris_species.load.raw_gbif import TABELA_ESPECIES as RAW_GBIF_ESPECIES
from iris_species.load.raw_gbif import TABELA_OCORRENCIAS as RAW_GBIF_OCORRENCIAS
from iris_species.transform.analytics import resumir_especies
from iris_species.transform.gbif import refinar_especies, refinar_ocorrencias
from iris_species.transform.refined import refinar_flores

logger = logging.getLogger(__name__)

TABELA_ORIGEM = "flores"
SCHEMA_REFINED = "refined"
SCHEMA_ANALYTICS = "analytics"
CONSULTAS_ANALYTICS = ("panorama", "paises")


def ler_sql(nome: str) -> str:
    """Lê uma consulta de ``iris_species/transform/sql/<nome>.sql``.

    Args:
        nome: Nome do arquivo, sem extensão.

    Returns:
        Texto da consulta.
    """
    return (
        resources.files("iris_species.transform.sql")
        .joinpath(f"{nome}.sql")
        .read_text(encoding="utf-8")
    )


def processar_camadas(con: duckdb.DuckDBPyConnection) -> list[tuple[str, str, int]]:
    """Gera as camadas refined e analytics a partir do schema raw.

    Args:
        con: Conexão aberta com o DuckDB, já com as três tabelas da raw gravadas.

    Returns:
        ``(schema, tabela, contagem)`` de cada tabela gravada, com a contagem lida do banco.

    Raises:
        iris_species.transform.refined.ValidacaoError: Se a raw violar algum contrato.
        duckdb.CatalogException: Se faltar tabela na raw.
    """
    flores = refinar_flores(ler_tabela(con, SCHEMA_RAW, TABELA_ORIGEM))
    resumo = resumir_especies(flores)
    especies = refinar_especies(ler_tabela(con, SCHEMA_RAW, RAW_GBIF_ESPECIES))
    raw_ocorrencias = ler_tabela(con, SCHEMA_RAW, RAW_GBIF_OCORRENCIAS)
    ocorrencias = refinar_ocorrencias(raw_ocorrencias)

    repetidas = len(raw_ocorrencias) - len(ocorrencias)
    if repetidas:
        logger.info("refined.ocorrencias: %s registros com gbif_id repetido removidos", repetidas)

    criar_schema(con, SCHEMA_REFINED)
    criar_schema(con, SCHEMA_ANALYTICS)
    gravacoes = [
        (SCHEMA_REFINED, "flores", flores),
        (SCHEMA_REFINED, "especies", especies),
        (SCHEMA_REFINED, "ocorrencias", ocorrencias),
        (SCHEMA_ANALYTICS, "especies", resumo),
    ]
    resultados = [(s, t, gravar(con, df, s, t)) for s, t, df in gravacoes]

    for nome in CONSULTAS_ANALYTICS:
        df = con.execute(ler_sql(nome)).df()
        resultados.append((SCHEMA_ANALYTICS, nome, gravar(con, df, SCHEMA_ANALYTICS, nome)))
    return resultados
