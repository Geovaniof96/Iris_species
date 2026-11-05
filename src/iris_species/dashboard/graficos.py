"""Figuras Plotly do dashboard (funções puras: DataFrame entra, figura sai).

Regras:

G1. Cada espécie tem uma cor fixa (:data:`CORES_ESPECIES`), seja qual for o filtro.
    Por quê: a cor segue a entidade; filtrar não pode repintar as que sobram.
    As três cores são as três primeiras da paleta categórica de referência, validadas
    para daltonismo em todos os pares (o gráfico de dispersão compara todas com todas).

G2. Um eixo y por gráfico, grade fina e discreta, legenda sempre visível (sem título),
    textos na cor de texto e nunca na cor da série.
"""

from collections.abc import Mapping
from types import MappingProxyType

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from iris_species.transform.refined import MEDIDAS

ORDEM_ESPECIES = ("setosa", "versicolor", "virginica")
CORES_ESPECIES: Mapping[str, str] = MappingProxyType(
    {"setosa": "#2a78d6", "versicolor": "#eb6834", "virginica": "#1baf7a"}
)
ROTULOS_MEDIDAS: Mapping[str, str] = MappingProxyType(
    dict(
        zip(
            MEDIDAS,
            (
                "Comprimento da sépala (cm)",
                "Largura da sépala (cm)",
                "Comprimento da pétala (cm)",
                "Largura da pétala (cm)",
            ),
            strict=True,
        )
    )
)

SUPERFICIE = "#fcfcfb"
_TINTA = "#0b0b0b"
_TINTA_SECUNDARIA = "#52514e"
_GRADE = "#e1e0d9"
_EIXO = "#c3c2b7"
_FONTE = 'system-ui, -apple-system, "Segoe UI", sans-serif'
_ROTULOS = MappingProxyType(
    {**ROTULOS_MEDIDAS, "especie": "Espécie", "ano": "Ano", "quantidade": "Ocorrências"}
)
_CORES = {
    "color_discrete_map": dict(CORES_ESPECIES),
    "category_orders": {"especie": ORDEM_ESPECIES},
}


def _estilizar(fig: go.Figure, altura: int = 380) -> go.Figure:
    fig.update_layout(
        height=altura,
        paper_bgcolor=SUPERFICIE,
        plot_bgcolor=SUPERFICIE,
        font={"family": _FONTE, "color": _TINTA_SECUNDARIA, "size": 13},
        legend={"title": None, "orientation": "h", "y": 1.02, "yanchor": "bottom", "x": 0},
        margin={"l": 8, "r": 8, "t": 40, "b": 8},
        hoverlabel={"bgcolor": "#ffffff", "font": {"family": _FONTE, "color": _TINTA}},
    )
    eixos = {"gridcolor": _GRADE, "gridwidth": 1, "linecolor": _EIXO, "zeroline": False}
    fig.update_xaxes(**eixos)
    fig.update_yaxes(**eixos)
    return fig


def dispersao_petala(flores: pd.DataFrame) -> go.Figure:
    """Comprimento x largura da pétala, uma cor por espécie.

    Args:
        flores: ``refined.flores`` (ou um recorte).

    Returns:
        Gráfico de dispersão.
    """
    fig = px.scatter(
        flores,
        x="comprimento_petala_cm",
        y="largura_petala_cm",
        color="especie",
        hover_data={"id": True, "duplicada": True},
        labels=dict(_ROTULOS),
        **_CORES,
    )
    # O anel de 2px na cor da superfície separa os pontos sobrepostos.
    fig.update_traces(
        marker={"size": 10, "opacity": 0.85, "line": {"width": 2, "color": SUPERFICIE}}
    )
    return _estilizar(fig)


def distribuicao_medida(flores: pd.DataFrame, medida: str) -> go.Figure:
    """Distribuição de uma medida por espécie (box plot com todos os pontos).

    Args:
        flores: ``refined.flores`` (ou um recorte).
        medida: Uma das colunas de :data:`iris_species.transform.refined.MEDIDAS`.

    Returns:
        Box plot.
    """
    fig = px.box(
        flores,
        x="especie",
        y=medida,
        color="especie",
        points="all",
        hover_data={"id": True},
        labels=dict(_ROTULOS),
        **_CORES,
    )
    fig.update_traces(marker={"size": 6, "opacity": 0.6}, line={"width": 2})
    fig.update_layout(showlegend=False)
    return _estilizar(fig)


def linha_ocorrencias_ano(por_ano: pd.DataFrame) -> go.Figure:
    """Ocorrências por ano, uma linha por espécie.

    Args:
        por_ano: Saída de :func:`iris_species.dashboard.kpis.ocorrencias_por_ano`.

    Returns:
        Gráfico de linhas com tooltip unificado por ano.
    """
    fig = px.line(
        por_ano, x="ano", y="quantidade", color="especie", labels=dict(_ROTULOS), **_CORES
    )
    fig.update_traces(line={"width": 2}, hovertemplate="%{y:,}")
    fig.update_layout(hovermode="x unified", separators=",.")
    fig.update_xaxes(showspikes=True, spikecolor=_EIXO, spikethickness=1, spikedash="solid")
    return _estilizar(fig)


def barras_top_paises(top: pd.DataFrame) -> go.Figure:
    """Países com mais ocorrências, em barras horizontais empilhadas por espécie.

    Args:
        top: Saída de :func:`iris_species.dashboard.kpis.top_paises`.

    Returns:
        Gráfico de barras, do país com mais ocorrências (no topo) ao com menos.
    """
    paises = list(dict.fromkeys(top["pais"]))
    fig = px.bar(
        top,
        x="quantidade",
        y="pais",
        color="especie",
        orientation="h",
        labels={**_ROTULOS, "pais": "País"},
        category_orders={"especie": ORDEM_ESPECIES, "pais": paises},
        color_discrete_map=dict(CORES_ESPECIES),
    )
    # A borda na cor da superfície é o espaço de 2px entre os segmentos empilhados.
    fig.update_traces(marker_line={"width": 2, "color": SUPERFICIE})
    fig.update_layout(bargap=0.45, separators=",.")
    fig.update_yaxes(title=None)
    return _estilizar(fig, altura=max(260, 34 * len(paises) + 90))


def mapa_ocorrencias(ocorrencias: pd.DataFrame) -> go.Figure:
    """Onde cada ocorrência foi registrada.

    Args:
        ocorrencias: ``refined.ocorrencias`` (ou um recorte).

    Returns:
        Mapa de pontos (projeção Natural Earth, sem depender de tiles externos).
    """
    fig = px.scatter_geo(
        ocorrencias,
        lat="latitude",
        lon="longitude",
        color="especie",
        hover_name="pais",
        hover_data={"ano": True, "estado": True, "latitude": ":.2f", "longitude": ":.2f"},
        projection="natural earth",
        labels=dict(_ROTULOS),
        **_CORES,
    )
    fig.update_traces(
        marker={"size": 6, "opacity": 0.6, "line": {"width": 0.5, "color": SUPERFICIE}}
    )
    fig.update_geos(
        showcountries=True,
        countrycolor=_EIXO,
        coastlinecolor=_EIXO,
        landcolor="#f0efec",
        bgcolor=SUPERFICIE,
        showframe=False,
    )
    return _estilizar(fig, altura=460)
