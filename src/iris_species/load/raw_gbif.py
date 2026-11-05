"""Carga dos arquivos de ``raw/gbif/`` para o schema ``raw`` do DuckDB.

Regras (as mesmas proibições de I2/I5 da ingestão do Kaggle):

RG1. ``raw.gbif_especies``: uma linha por arquivo de espécie, com o documento JSON
     inteiro como texto, exatamente como está no arquivo.

RG2. ``raw.gbif_ocorrencias``: uma linha por item de ``results`` de cada página, com o
     objeto JSON re-serializado (``json.dumps``, sem alterar nenhum valor). Separar a
     página em registros é só estrutura: nada é convertido, corrigido ou descartado.
     Por quê: a contagem da raw passa a ser a de ocorrências, que é o que se consulta.

RG3. Todas as colunas são ``VARCHAR``; tabelas recriadas, nunca acrescentadas (I3).
"""

import json
from pathlib import Path

import duckdb
import pandas as pd

from iris_species.clients.db import criar_schema, gravar
from iris_species.extract.gbif import ESPECIES, PASTA
from iris_species.load.raw import SCHEMA

TABELA_ESPECIES = "gbif_especies"
TABELA_OCORRENCIAS = "gbif_ocorrencias"


def _arquivo_especie(pasta_gbif: Path, especie: str) -> Path:
    return pasta_gbif / "especies" / f"{especie}.json"


def _paginas(pasta_gbif: Path, especie: str) -> list[Path]:
    return sorted((pasta_gbif / "ocorrencias" / especie).glob("pagina_*.json"))


def gbif_faltando(pasta_raw: Path) -> list[str]:
    """Lista os arquivos da GBIF que deveriam existir em ``raw/`` e não existem.

    Args:
        pasta_raw: Pasta ``raw/``.

    Returns:
        Caminhos relativos a ``raw/`` ausentes (arquivo de espécie ou páginas).
    """
    pasta_gbif = pasta_raw / PASTA
    faltando: list[str] = []
    for especie in ESPECIES:
        if not _arquivo_especie(pasta_gbif, especie).is_file():
            faltando.append(f"{PASTA}/especies/{especie}.json")
        if not _paginas(pasta_gbif, especie):
            faltando.append(f"{PASTA}/ocorrencias/{especie}/pagina_*.json")
    return faltando


def ler_especies(pasta_raw: Path) -> pd.DataFrame:
    """Lê os documentos de taxonomia como texto, sem interpretar.

    Args:
        pasta_raw: Pasta ``raw/``.

    Returns:
        DataFrame com ``especie_arquivo``, ``arquivo`` e ``documento``.
    """
    pasta_gbif = pasta_raw / PASTA
    linhas = [
        {
            "especie_arquivo": especie,
            "arquivo": f"{PASTA}/especies/{especie}.json",
            "documento": _arquivo_especie(pasta_gbif, especie).read_text(encoding="utf-8"),
        }
        for especie in ESPECIES
    ]
    return pd.DataFrame(linhas, dtype=str)


def ler_ocorrencias(pasta_raw: Path) -> pd.DataFrame:
    """Separa as páginas de ocorrências em um registro JSON por linha.

    Args:
        pasta_raw: Pasta ``raw/``.

    Returns:
        DataFrame com ``especie_arquivo``, ``arquivo`` e ``registro``.
    """
    pasta_gbif = pasta_raw / PASTA
    linhas = []
    for especie in ESPECIES:
        for pagina in _paginas(pasta_gbif, especie):
            relativo = pagina.relative_to(pasta_raw).as_posix()
            for registro in json.loads(pagina.read_text(encoding="utf-8"))["results"]:
                linhas.append(
                    {
                        "especie_arquivo": especie,
                        "arquivo": relativo,
                        "registro": json.dumps(registro, ensure_ascii=False),
                    }
                )
    return pd.DataFrame(linhas, columns=["especie_arquivo", "arquivo", "registro"], dtype=str)


def ingerir_gbif(con: duckdb.DuckDBPyConnection, pasta_raw: Path) -> list[tuple[str, str, int]]:
    """Grava ``raw.gbif_especies`` e ``raw.gbif_ocorrencias``.

    Args:
        con: Conexão aberta com o DuckDB.
        pasta_raw: Pasta ``raw/``.

    Returns:
        ``(schema, tabela, contagem)`` de cada tabela, com a contagem lida do banco.
    """
    criar_schema(con, SCHEMA)
    return [
        (SCHEMA, TABELA_ESPECIES, gravar(con, ler_especies(pasta_raw), SCHEMA, TABELA_ESPECIES)),
        (
            SCHEMA,
            TABELA_OCORRENCIAS,
            gravar(con, ler_ocorrencias(pasta_raw), SCHEMA, TABELA_OCORRENCIAS),
        ),
    ]
