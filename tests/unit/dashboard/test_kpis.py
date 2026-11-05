import pandas as pd
import pytest

from iris_species.dashboard import kpis


@pytest.fixture
def flores() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "id": [1, 2, 3, 4],
            "comprimento_petala_cm": [1.0, 2.0, 3.0, 6.0],
            "largura_petala_cm": [0.2, 0.3, 1.0, 2.0],
            "especie": ["setosa", "setosa", "versicolor", "virginica"],
            "duplicada": [True, True, False, False],
        }
    )


@pytest.fixture
def ocorrencias() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "especie": ["setosa", "setosa", "versicolor", "virginica", "virginica"],
            "pais_codigo": ["RU", "RU", "US", "US", "CA"],
            "pais": ["Russia", "Russia", "USA", "USA", "Canada"],
            "ano": [2000, 2003, 2003, 2001, 2003],
            "tipo_registro": [
                "HUMAN_OBSERVATION",
                "PRESERVED_SPECIMEN",
                "HUMAN_OBSERVATION",
                "HUMAN_OBSERVATION",
                "HUMAN_OBSERVATION",
            ],
        }
    )


@pytest.mark.parametrize(
    ("valor", "casas", "esperado"),
    [(1234.56, 1, "1.234,6"), (3.8, 1, "3,8"), (0.5, 2, "0,50"), (1000000, 0, "1.000.000")],
)
def test_formatar_decimal_usa_padrao_pt_br(valor: float, casas: int, esperado: str) -> None:
    assert kpis.formatar_decimal(valor, casas) == esperado


def test_filtrar_por_especie_e_periodo_inclusivo(ocorrencias: pd.DataFrame) -> None:
    recorte = kpis.filtrar(ocorrencias, ["setosa", "virginica"], (2001, 2003))

    assert recorte["especie"].tolist() == ["setosa", "virginica", "virginica"]
    assert recorte.index.tolist() == [0, 1, 2]


def test_razao_petala_compara_maior_e_menor_media(flores: pd.DataFrame) -> None:
    assert kpis.razao_petala(flores) == ("virginica", "setosa", 4.0)


def test_razao_petala_none_com_uma_especie(flores: pd.DataFrame) -> None:
    assert kpis.razao_petala(kpis.filtrar(flores, ["setosa"])) is None


def test_fronteira_setosa(flores: pd.DataFrame) -> None:
    assert kpis.fronteira_setosa(flores) == (2.0, 3.0)


@pytest.mark.parametrize("especies", [["setosa"], ["versicolor", "virginica"]])
def test_fronteira_setosa_none_sem_os_dois_lados(flores: pd.DataFrame, especies: list[str]) -> None:
    assert kpis.fronteira_setosa(kpis.filtrar(flores, especies)) is None


def test_kpis_flores(flores: pd.DataFrame) -> None:
    resultado = {k.rotulo: k for k in kpis.kpis_flores(flores)}

    assert resultado["Flores medidas"].valor == "4"
    assert resultado["Linhas duplicadas"].valor == "2"
    assert resultado["Pétala: maior ÷ menor média"].valor == "4,0x"
    assert resultado["Pétala: setosa | demais"].valor == "2,0 | 3,0 cm"
    assert "já separa a setosa" in resultado["Pétala: setosa | demais"].ajuda


def test_kpis_flores_avisa_sobreposicao(flores: pd.DataFrame) -> None:
    flores.loc[0, "comprimento_petala_cm"] = 5.0

    fronteira = kpis.kpis_flores(flores)[3]

    assert "se sobrepõem" in fronteira.ajuda


def test_kpis_flores_recorte_vazio_nao_quebra(flores: pd.DataFrame) -> None:
    valores = [k.valor for k in kpis.kpis_flores(flores.iloc[0:0])]

    assert valores == ["0", "0", kpis.SEM_VALOR, kpis.SEM_VALOR]


def test_kpis_ocorrencias(ocorrencias: pd.DataFrame) -> None:
    valores = [k.valor for k in kpis.kpis_ocorrencias(ocorrencias)]

    assert valores == ["5", "3", "2000-2003", "80,0%"]


def test_kpis_ocorrencias_recorte_vazio(ocorrencias: pd.DataFrame) -> None:
    valores = [k.valor for k in kpis.kpis_ocorrencias(ocorrencias.iloc[0:0])]

    assert valores == ["0", "0", kpis.SEM_VALOR, kpis.SEM_VALOR]


def test_ocorrencias_por_ano_preenche_anos_sem_registro(ocorrencias: pd.DataFrame) -> None:
    por_ano = kpis.ocorrencias_por_ano(ocorrencias)
    setosa = por_ano[por_ano["especie"] == "setosa"]

    assert setosa["ano"].tolist() == [2000, 2001, 2002, 2003]
    assert setosa["quantidade"].tolist() == [1, 0, 0, 1]
    assert len(por_ano) == 3 * 4


def test_ocorrencias_por_ano_vazio(ocorrencias: pd.DataFrame) -> None:
    por_ano = kpis.ocorrencias_por_ano(ocorrencias.iloc[0:0])

    assert por_ano.empty
    assert por_ano.columns.tolist() == ["especie", "ano", "quantidade"]


def test_top_paises_ordena_pelo_total_e_limita(ocorrencias: pd.DataFrame) -> None:
    ocorrencias.loc[4, "pais"] = "USA"  # USA 3, Russia 2, sem empate

    top = kpis.top_paises(ocorrencias, n=2)

    assert top["pais"].tolist() == ["USA", "USA", "Russia"]
    assert top["especie"].tolist() == ["versicolor", "virginica", "setosa"]
    assert top["quantidade"].tolist() == [1, 2, 2]
