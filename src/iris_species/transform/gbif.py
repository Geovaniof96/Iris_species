"""Transformações puras de ``raw.gbif_*`` para ``refined.especies`` e ``refined.ocorrencias``.

Regras:

RG4. ``refined.especies``: uma linha por espécie, com ``especie`` (a chave de ligação com
     ``refined.flores``), ``gbif_codigo``, ``nome_cientifico``, ``familia``, ``genero`` e
     ``status``. Exige exatamente setosa, versicolor e virginica, cada uma com
     ``canonicalName == "Iris <especie>"`` e ``rank == "SPECIES"``.
     Por quê: se a GBIF devolver outra espécie, o JOIN ligaria flores a dados errados.

RG5. ``refined.ocorrencias``: uma linha por ocorrência, com ``gbif_id``, ``especie``,
     país, estado, ``ano``, ``mes``, ``latitude``, ``longitude``, ``tipo_registro`` e
     ``licenca``. A ``especie`` é a consultada (o arquivo), não o campo ``species``.
     Por quê: a busca por ``taxonKey`` inclui subespécies e sinônimos, que pertencem à
     espécie consultada.

RG6. ``gbif_id`` repetido é removido (fica a primeira ocorrência).
     Por quê: diferente das flores, aqui a repetição é artefato da paginação (o mesmo
     registro em duas páginas), não um dado.

RG7. Contrato: ``gbif_id`` não nulo, latitude em [-90, 90] e longitude em [-180, 180],
     ambas não nulas. Violação gera :class:`ValidacaoError`.
"""

import json
from collections.abc import Mapping
from types import MappingProxyType
from typing import Any

import pandas as pd

from iris_species.transform.refined import ESPECIES_VALIDAS, ValidacaoError

CAMPOS_OCORRENCIA: Mapping[str, str] = MappingProxyType(
    {
        "key": "gbif_id",
        "countryCode": "pais_codigo",
        "country": "pais",
        "stateProvince": "estado",
        "year": "ano",
        "month": "mes",
        "decimalLatitude": "latitude",
        "decimalLongitude": "longitude",
        "basisOfRecord": "tipo_registro",
        "license": "licenca",
    }
)
TIPOS_OCORRENCIA: Mapping[str, str] = MappingProxyType(
    {
        "gbif_id": "Int64",
        "ano": "Int64",
        "mes": "Int64",
        "latitude": "Float64",
        "longitude": "Float64",
    }
)
COLUNAS_TEXTO_OCORRENCIA = ("pais_codigo", "pais", "estado", "tipo_registro", "licenca")


def _ler_json(texto: str, origem: str) -> dict[str, Any]:
    try:
        dados = json.loads(texto)
    except (json.JSONDecodeError, TypeError) as exc:
        raise ValidacaoError(f"{origem}: JSON inválido") from exc
    if not isinstance(dados, dict):
        raise ValidacaoError(f"{origem}: esperado um objeto JSON")
    return dados


def refinar_especies(raw: pd.DataFrame) -> pd.DataFrame:
    """Extrai a taxonomia de cada espécie de ``raw.gbif_especies``.

    Args:
        raw: Conteúdo de ``raw.gbif_especies``.

    Returns:
        Uma linha por espécie, ordenada por ``especie``.

    Raises:
        ValidacaoError: Se o conjunto de espécies ou a taxonomia fugirem do contrato (RG4).
    """
    linhas = []
    for especie, arquivo, documento in raw[["especie_arquivo", "arquivo", "documento"]].itertuples(
        index=False
    ):
        dados = _ler_json(documento, arquivo)
        esperado = f"Iris {especie}"
        if dados.get("canonicalName") != esperado or dados.get("rank") != "SPECIES":
            raise ValidacaoError(
                f"{arquivo}: esperado {esperado} (SPECIES), veio "
                f"{dados.get('canonicalName')} ({dados.get('rank')})"
            )
        linhas.append(
            {
                "especie": especie,
                "gbif_codigo": dados.get("usageKey"),
                "nome_cientifico": dados.get("scientificName"),
                "familia": dados.get("family"),
                "genero": dados.get("genus"),
                "status": dados.get("status"),
            }
        )

    colunas = ["especie", "gbif_codigo", "nome_cientifico", "familia", "genero", "status"]
    df = pd.DataFrame(linhas, columns=colunas)
    if sorted(df["especie"]) != sorted(ESPECIES_VALIDAS):
        raise ValidacaoError(f"espécies da GBIF diferentes de {sorted(ESPECIES_VALIDAS)}")
    df["gbif_codigo"] = df["gbif_codigo"].astype(pd.api.types.pandas_dtype("Int64"))
    return df.sort_values("especie").reset_index(drop=True)


def refinar_ocorrencias(raw: pd.DataFrame) -> pd.DataFrame:
    """Extrai os campos de cada ocorrência de ``raw.gbif_ocorrencias``.

    Args:
        raw: Conteúdo de ``raw.gbif_ocorrencias``.

    Returns:
        Uma linha por ``gbif_id``, na ordem de chegada.

    Raises:
        ValidacaoError: Se algum registro violar o contrato (RG7).
    """
    linhas = []
    for especie, arquivo, registro in raw[["especie_arquivo", "arquivo", "registro"]].itertuples(
        index=False
    ):
        dados = _ler_json(registro, arquivo)
        linha: dict[str, Any] = {"especie": especie}
        linha.update({destino: dados.get(origem) for origem, destino in CAMPOS_OCORRENCIA.items()})
        linhas.append(linha)

    colunas = ["gbif_id", "especie", *[c for c in CAMPOS_OCORRENCIA.values() if c != "gbif_id"]]
    df = pd.DataFrame(linhas, columns=colunas)
    for coluna, tipo in TIPOS_OCORRENCIA.items():
        try:
            df[coluna] = pd.to_numeric(df[coluna], errors="raise").astype(
                pd.api.types.pandas_dtype(tipo)
            )
        except (ValueError, TypeError) as exc:
            raise ValidacaoError(f"coluna {coluna}: valor não convertido para {tipo}") from exc
    for coluna in COLUNAS_TEXTO_OCORRENCIA:
        df[coluna] = df[coluna].astype(pd.api.types.pandas_dtype("str"))

    _validar_ocorrencias(df)
    return df.drop_duplicates(subset="gbif_id", keep="first").reset_index(drop=True)


def _validar_ocorrencias(df: pd.DataFrame) -> None:
    problemas: list[str] = []
    if df["gbif_id"].isna().any():
        problemas.append("gbif_id nulo")
    if not df["especie"].isin(ESPECIES_VALIDAS).all():
        problemas.append("especie fora do domínio")
    for coluna, limite in (("latitude", 90), ("longitude", 180)):
        if df[coluna].isna().any():
            problemas.append(f"{coluna} nula")
        elif (df[coluna].abs() > limite).any():
            problemas.append(f"{coluna} fora de [-{limite}, {limite}]")
    if problemas:
        raise ValidacaoError("; ".join(problemas))
