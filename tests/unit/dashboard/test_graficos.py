import pandas as pd
import plotly.graph_objects as go
import pytest

from iris_species.dashboard import graficos, kpis


@pytest.fixture
def flores() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "id": [1, 2, 3],
            "comprimento_sepala_cm": [5.1, 7.0, 6.3],
            "largura_sepala_cm": [3.5, 3.2, 3.3],
            "comprimento_petala_cm": [1.4, 4.7, 6.0],
            "largura_petala_cm": [0.2, 1.4, 2.5],
            "especie": ["setosa", "versicolor", "virginica"],
            "duplicada": [False, False, False],
        }
    )


@pytest.fixture
def ocorrencias() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "especie": ["setosa", "virginica", "virginica"],
            "pais": ["Russia", "USA", "Canada"],
            "estado": [None, "Ohio", None],
            "ano": [2020, 2021, 2021],
            "latitude": [55.0, 40.0, 45.0],
            "longitude": [37.0, -82.0, -75.0],
        }
    )


def _cores(figura: go.Figure) -> dict[str, str]:
    return {trace.name: trace.marker.color for trace in figura.data}


def test_cor_segue_a_especie_mesmo_com_filtro(flores: pd.DataFrame) -> None:
    so_virginica = kpis.filtrar(flores, ["virginica"])

    assert _cores(graficos.dispersao_petala(flores)) == dict(graficos.CORES_ESPECIES)
    assert _cores(graficos.dispersao_petala(so_virginica)) == {
        "virginica": graficos.CORES_ESPECIES["virginica"]
    }


@pytest.mark.parametrize("medida", list(graficos.ROTULOS_MEDIDAS))
def test_distribuicao_medida_usa_o_rotulo_da_medida(flores: pd.DataFrame, medida: str) -> None:
    figura = graficos.distribuicao_medida(flores, medida)

    assert figura.layout.yaxis.title.text == graficos.ROTULOS_MEDIDAS[medida]
    assert len(figura.data) == 3


def test_linha_ocorrencias_ano_uma_linha_por_especie(ocorrencias: pd.DataFrame) -> None:
    figura = graficos.linha_ocorrencias_ano(kpis.ocorrencias_por_ano(ocorrencias))

    assert [trace.name for trace in figura.data] == ["setosa", "virginica"]
    assert all(trace.line.width == 2 for trace in figura.data)


def test_barras_top_paises_mantem_ordem_e_espaco_entre_segmentos(
    ocorrencias: pd.DataFrame,
) -> None:
    top = kpis.top_paises(ocorrencias)

    figura = graficos.barras_top_paises(top)

    # O Plotly desenha o categoryarray de baixo para cima: o maior país fica no topo.
    assert list(figura.layout.yaxis.categoryarray)[::-1] == list(dict.fromkeys(top["pais"]))
    assert all(trace.marker.line.color == graficos.SUPERFICIE for trace in figura.data)


def test_mapa_ocorrencias_plota_todos_os_pontos(ocorrencias: pd.DataFrame) -> None:
    figura = graficos.mapa_ocorrencias(ocorrencias)

    assert sum(len(trace.lat) for trace in figura.data) == 3
    assert figura.layout.geo.projection.type == "natural earth"
