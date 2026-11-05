"""KPIs e agregações do dashboard (funções puras, sem I/O nem Streamlit).

Regras:

K1. Todo KPI sai como texto pronto para a tela, em pt-BR (milhar com ponto, decimal com
    vírgula). Sem dado para calcular, o valor é ``"—"``, nunca erro.
    Por quê: o filtro do dashboard pode deixar um recorte vazio.

K2. As linhas ``duplicada`` das flores entram nos cálculos, como na analytics (A3).

K3. As ocorrências são uma amostra (até 3.000 por espécie, as mais recentes primeiro).
    O texto de ajuda dos KPIs da GBIF diz isso.
"""

from collections.abc import Iterable
from dataclasses import dataclass

import pandas as pd

from iris_species.utils.saida import formatar_numero

SEM_VALOR = "—"
OBSERVACAO_HUMANA = "HUMAN_OBSERVATION"
_AJUDA_AMOSTRA = "Amostra da GBIF: até 3.000 registros por espécie, os mais recentes primeiro."


@dataclass(frozen=True)
class Kpi:
    """Um indicador pronto para ``st.metric``."""

    rotulo: str
    valor: str
    ajuda: str


def formatar_decimal(valor: float, casas: int = 1) -> str:
    """Formata um número com milhar em ponto e decimal em vírgula.

    Args:
        valor: Número a formatar.
        casas: Casas decimais.

    Returns:
        Texto como ``"1.234,5"``.
    """
    texto = f"{valor:,.{casas}f}"
    return texto.replace(",", "_").replace(".", ",").replace("_", ".")


def filtrar(
    df: pd.DataFrame, especies: Iterable[str], anos: tuple[int, int] | None = None
) -> pd.DataFrame:
    """Recorta por espécie e, se pedido, pelo intervalo fechado de ``ano``.

    Args:
        df: Tabela com a coluna ``especie`` (e ``ano``, se ``anos`` for informado).
        especies: Espécies mantidas.
        anos: ``(primeiro, ultimo)``, inclusive.

    Returns:
        Cópia filtrada, com o índice refeito.
    """
    mascara = df["especie"].isin(list(especies))
    if anos is not None:
        mascara &= df["ano"].between(anos[0], anos[1])
    return df.loc[mascara].reset_index(drop=True)


def razao_petala(flores: pd.DataFrame) -> tuple[str, str, float] | None:
    """Compara a maior e a menor média de comprimento da pétala entre as espécies.

    Args:
        flores: ``refined.flores`` (ou um recorte).

    Returns:
        ``(especie_maior, especie_menor, razao)`` ou ``None`` com menos de duas espécies.
    """
    medias = flores.groupby("especie")["comprimento_petala_cm"].mean().sort_values()
    if len(medias) < 2:  # noqa: PLR2004 - comparar exige duas espécies
        return None
    return str(medias.index[-1]), str(medias.index[0]), float(medias.iloc[-1] / medias.iloc[0])


def fronteira_setosa(flores: pd.DataFrame) -> tuple[float, float] | None:
    """Maior pétala da setosa e menor pétala das demais espécies.

    Args:
        flores: ``refined.flores`` (ou um recorte).

    Returns:
        ``(max_setosa, min_demais)`` ou ``None`` se faltar a setosa ou as demais.
    """
    setosa = flores["especie"] == "setosa"
    if not setosa.any() or setosa.all():
        return None
    petala = flores["comprimento_petala_cm"]
    return float(petala[setosa].max()), float(petala[~setosa].min())


def kpis_flores(flores: pd.DataFrame) -> list[Kpi]:
    """KPIs das flores medidas (Kaggle).

    Args:
        flores: ``refined.flores`` (ou um recorte).

    Returns:
        Flores medidas, linhas duplicadas, razão da pétala e fronteira da setosa.
    """
    razao = razao_petala(flores)
    fronteira = fronteira_setosa(flores)

    if fronteira is None:
        valor_fronteira, ajuda_fronteira = SEM_VALOR, "Selecione a setosa e outra espécie."
    else:
        maximo, minimo = fronteira
        valor_fronteira = f"{formatar_decimal(maximo)} | {formatar_decimal(minimo)} cm"
        ajuda_fronteira = (
            f"Maior pétala da setosa | menor pétala das demais. Folga de "
            f"{formatar_decimal(minimo - maximo)} cm: só o comprimento da pétala já separa a "
            "setosa."
            if minimo > maximo
            else "As faixas de pétala se sobrepõem: a pétala sozinha não separa a setosa."
        )

    return [
        Kpi(
            "Flores medidas",
            formatar_numero(len(flores)),
            "Linhas de refined.flores (Kaggle) no recorte.",
        ),
        Kpi(
            "Linhas duplicadas",
            formatar_numero(int(flores["duplicada"].sum())),
            "Medidas e espécie idênticas a outra linha. Ficam na base e entram nos cálculos.",
        ),
        Kpi(
            "Pétala: maior ÷ menor média",
            SEM_VALOR if razao is None else f"{formatar_decimal(razao[2])}x",
            "Selecione ao menos duas espécies."
            if razao is None
            else f"Média do comprimento da pétala da {razao[0]} sobre a da {razao[1]}.",
        ),
        Kpi("Pétala: setosa | demais", valor_fronteira, ajuda_fronteira),
    ]


def kpis_ocorrencias(ocorrencias: pd.DataFrame) -> list[Kpi]:
    """KPIs das ocorrências no mundo (GBIF).

    Args:
        ocorrencias: ``refined.ocorrencias`` (ou um recorte).

    Returns:
        Ocorrências, países, período e participação de observação humana.
    """
    total = len(ocorrencias)
    anos = ocorrencias["ano"].dropna()
    periodo = SEM_VALOR if anos.empty else f"{int(anos.min())}-{int(anos.max())}"
    parcela_humana = (ocorrencias["tipo_registro"] == OBSERVACAO_HUMANA).mean()
    humana = SEM_VALOR if total == 0 else f"{formatar_decimal(100 * parcela_humana)}%"
    return [
        Kpi("Ocorrências GBIF", formatar_numero(total), _AJUDA_AMOSTRA),
        Kpi(
            "Países com registro",
            formatar_numero(int(ocorrencias["pais_codigo"].nunique())),
            "Países distintos nas ocorrências do recorte.",
        ),
        Kpi("Período dos registros", periodo, f"Primeiro e último ano. {_AJUDA_AMOSTRA}"),
        Kpi(
            "Observação humana",
            humana,
            "Parcela registrada por observação em campo (ex.: apps de ciência cidadã), "
            "e não por espécime de herbário.",
        ),
    ]


def ocorrencias_por_ano(ocorrencias: pd.DataFrame) -> pd.DataFrame:
    """Conta ocorrências por espécie e ano, com zero nos anos sem registro.

    Args:
        ocorrencias: ``refined.ocorrencias`` (ou um recorte).

    Returns:
        ``especie``, ``ano`` e ``quantidade``, ordenado por espécie e ano.
    """
    colunas = ["especie", "ano", "quantidade"]
    validas = ocorrencias.dropna(subset=["ano"])
    if validas.empty:
        return pd.DataFrame(columns=colunas)
    contagem = validas.groupby(["especie", validas["ano"].astype(int)]).size()
    anos = range(int(validas["ano"].min()), int(validas["ano"].max()) + 1)
    grade = pd.MultiIndex.from_product(
        [sorted(validas["especie"].unique()), anos], names=["especie", "ano"]
    )
    return contagem.reindex(grade, fill_value=0).rename("quantidade").reset_index()[colunas]


def top_paises(ocorrencias: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    """Os ``n`` países com mais ocorrências, abertos por espécie.

    Args:
        ocorrencias: ``refined.ocorrencias`` (ou um recorte).
        n: Quantidade de países.

    Returns:
        ``pais``, ``especie`` e ``quantidade``, do país com mais ocorrências ao com menos.
    """
    validas = ocorrencias.dropna(subset=["pais"])
    principais = validas["pais"].value_counts().head(n).index
    contagem = (
        validas[validas["pais"].isin(principais)]
        .groupby(["pais", "especie"])
        .size()
        .rename("quantidade")
        .reset_index()
    )
    ordem = {pais: posicao for posicao, pais in enumerate(principais)}
    contagem["_ordem"] = contagem["pais"].map(ordem)
    return contagem.sort_values(["_ordem", "especie"]).drop(columns="_ordem").reset_index(drop=True)
