"""Transformação pura de ``raw.flores`` para ``refined.flores``.

Regras (definidas a partir de ``doc_api.md``; não fazem parte da spec original):

R1. Tipagem explícita: ``id`` vira ``Int64`` e as quatro medidas viram ``Float64``. Um
    valor que não converte gera :class:`ValidacaoError`, nunca nulo silencioso.
    Por quê: a raw guarda tudo como texto (I5); converter é uma decisão desta camada,
    e quem decide precisa falhar alto quando o dado não cabe no tipo.

R2. Colunas renomeadas para português em snake_case (``comprimento_sepala_cm``...).
    Por quê: é o vocabulário das consultas.

R3. ``Species`` vira ``especie`` sem o prefixo ``Iris-`` (``Iris-setosa`` → ``setosa``).
    Por quê: o prefixo é ruído e diverge de outras versões do dataset (ex.: scikit-learn).

R4. Nenhum valor medido é corrigido e nenhuma linha é removida, nem mesmo as linhas
    Id 35 e 38, que têm erros conhecidos. A coluna ``duplicada`` marca **todas** as linhas
    cujas medidas e espécie se repetem em outra linha.
    Por quê: corrigir ou deduplicar muda o dado de origem; sinalizar deixa a decisão para
    quem consome e mantém a contagem rastreável até a raw.

R5. Contrato validado antes de gravar: colunas esperadas presentes, ``id`` único e não
    nulo, medidas não nulas e maiores que zero, ``especie`` em {setosa, versicolor,
    virginica}. Qualquer violação gera :class:`ValidacaoError`.
    Por quê: dado fora do contrato não pode chegar calado à analytics.
"""

from collections.abc import Mapping
from types import MappingProxyType

import pandas as pd

RENOMEAR: Mapping[str, str] = MappingProxyType(
    {
        "Id": "id",
        "SepalLengthCm": "comprimento_sepala_cm",
        "SepalWidthCm": "largura_sepala_cm",
        "PetalLengthCm": "comprimento_petala_cm",
        "PetalWidthCm": "largura_petala_cm",
        "Species": "especie",
    }
)
MEDIDAS = (
    "comprimento_sepala_cm",
    "largura_sepala_cm",
    "comprimento_petala_cm",
    "largura_petala_cm",
)
ESPECIES_VALIDAS = frozenset({"setosa", "versicolor", "virginica"})
PREFIXO_ESPECIE = "Iris-"


class ValidacaoError(Exception):
    """Dado da raw fora do contrato da refined."""


def _converter(serie: pd.Series, tipo: str) -> pd.Series:
    try:
        numerica: pd.Series = pd.to_numeric(serie, errors="raise")
        return numerica.astype(pd.api.types.pandas_dtype(tipo))
    except (ValueError, TypeError) as exc:
        raise ValidacaoError(
            f"coluna {serie.name}: valor não convertido para {tipo} ({exc})"
        ) from exc


def _validar(df: pd.DataFrame) -> None:
    problemas: list[str] = []
    if df["id"].isna().any():
        problemas.append("id nulo")
    if df["id"].duplicated().any():
        problemas.append("id repetido")
    for medida in MEDIDAS:
        if df[medida].isna().any():
            problemas.append(f"{medida} nulo")
        elif (df[medida] <= 0).any():
            problemas.append(f"{medida} menor ou igual a zero")
    invalidas = sorted(set(df["especie"].dropna()) - ESPECIES_VALIDAS)
    if df["especie"].isna().any():
        problemas.append("especie nula")
    if invalidas:
        problemas.append(f"especie fora do domínio: {', '.join(invalidas)}")
    if problemas:
        raise ValidacaoError("; ".join(problemas))


def refinar_flores(raw: pd.DataFrame) -> pd.DataFrame:
    """Tipa, renomeia, padroniza a espécie e sinaliza duplicatas de ``raw.flores``.

    Args:
        raw: Conteúdo de ``raw.flores`` (todas as colunas como texto).

    Returns:
        DataFrame com ``id``, as quatro medidas, ``especie`` e ``duplicada``, na mesma
        ordem e com as mesmas linhas da raw.

    Raises:
        ValidacaoError: Se faltar coluna, algum valor não converter ou o contrato (R5)
            for violado.
    """
    ausentes = [coluna for coluna in RENOMEAR if coluna not in raw.columns]
    if ausentes:
        raise ValidacaoError(f"colunas ausentes na raw: {', '.join(ausentes)}")

    df = raw.loc[:, list(RENOMEAR)].rename(columns=dict(RENOMEAR))
    df["id"] = _converter(df["id"], "Int64")
    for medida in MEDIDAS:
        df[medida] = _converter(df[medida], "Float64")
    df["especie"] = df["especie"].str.removeprefix(PREFIXO_ESPECIE)
    _validar(df)
    df["duplicada"] = df.duplicated(subset=[*MEDIDAS, "especie"], keep=False)
    return df.reset_index(drop=True)
