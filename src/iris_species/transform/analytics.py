"""Transformação pura de ``refined.flores`` para ``analytics.especies``.

Regras (extras à spec original):

A1. Uma linha por espécie, em ordem alfabética, com ``quantidade``,
    ``quantidade_duplicadas`` e média, mínimo e máximo de cada medida.
    Por quê: é o resumo da ``doc_api.md`` (seção 4) que se consulta com mais frequência.

A2. Sem arredondamento: os valores são gravados com a precisão de ``DOUBLE``.
    Por quê: arredondar é decisão de apresentação, não do dado.

A3. As linhas marcadas como ``duplicada`` entram nos cálculos.
    Por quê: a refined não remove linhas (R4); ``quantidade_duplicadas`` mostra quantas
    entraram em cada grupo.
"""

import pandas as pd

from iris_species.transform.refined import MEDIDAS

AGREGACOES = ("mean", "min", "max")
_PREFIXOS = {"mean": "media", "min": "min", "max": "max"}


def resumir_especies(refined: pd.DataFrame) -> pd.DataFrame:
    """Agrega as medidas da refined por espécie.

    Args:
        refined: Saída de :func:`iris_species.transform.refined.refinar_flores`.

    Returns:
        DataFrame com ``especie``, ``quantidade``, ``quantidade_duplicadas`` e
        ``<media|min|max>_<medida>`` para cada medida.
    """
    agregacoes: dict[str, tuple[str, str]] = {
        "quantidade": ("id", "count"),
        "quantidade_duplicadas": ("duplicada", "sum"),
    }
    for medida in MEDIDAS:
        for funcao in AGREGACOES:
            agregacoes[f"{_PREFIXOS[funcao]}_{medida}"] = (medida, funcao)

    resumo = refined.groupby("especie", sort=True).agg(**agregacoes).reset_index()
    return resumo.astype({"quantidade": "int64", "quantidade_duplicadas": "int64"})
