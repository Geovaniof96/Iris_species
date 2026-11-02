import pandas as pd
import pytest

from iris_species.transform.analytics import resumir_especies
from iris_species.transform.refined import refinar_flores


def test_resumir_especies_uma_linha_por_especie_em_ordem(raw_flores: pd.DataFrame) -> None:
    resumo = resumir_especies(refinar_flores(raw_flores))

    assert resumo["especie"].tolist() == ["setosa", "versicolor", "virginica"]
    assert resumo["quantidade"].tolist() == [3, 1, 1]
    assert resumo["quantidade_duplicadas"].tolist() == [2, 0, 0]


def test_resumir_especies_calcula_media_min_max(raw_flores: pd.DataFrame) -> None:
    setosa = resumir_especies(refinar_flores(raw_flores)).iloc[0]

    assert setosa["media_comprimento_sepala_cm"] == pytest.approx((5.1 + 4.9 + 4.9) / 3)
    assert setosa["min_comprimento_sepala_cm"] == 4.9
    assert setosa["max_comprimento_sepala_cm"] == 5.1


def test_resumir_especies_tem_colunas_de_todas_as_medidas(raw_flores: pd.DataFrame) -> None:
    resumo = resumir_especies(refinar_flores(raw_flores))

    assert len(resumo.columns) == 3 + 4 * 3
