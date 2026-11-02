import pandas as pd
import pytest

from iris_species.transform.refined import ValidacaoError, refinar_flores


def test_refinar_flores_tipa_e_renomeia(raw_flores: pd.DataFrame) -> None:
    df = refinar_flores(raw_flores)

    assert df.columns.tolist() == [
        "id",
        "comprimento_sepala_cm",
        "largura_sepala_cm",
        "comprimento_petala_cm",
        "largura_petala_cm",
        "especie",
        "duplicada",
    ]
    assert str(df["id"].dtype) == "Int64"
    assert str(df["comprimento_sepala_cm"].dtype) == "Float64"
    assert df.loc[0, "comprimento_sepala_cm"] == 5.1


def test_refinar_flores_remove_prefixo_da_especie(raw_flores: pd.DataFrame) -> None:
    assert refinar_flores(raw_flores)["especie"].tolist() == [
        "setosa",
        "setosa",
        "setosa",
        "versicolor",
        "virginica",
    ]


def test_refinar_flores_marca_todas_as_duplicadas_sem_remover(raw_flores: pd.DataFrame) -> None:
    df = refinar_flores(raw_flores)

    assert len(df) == len(raw_flores)
    assert df["duplicada"].tolist() == [False, True, True, False, False]


@pytest.mark.parametrize(
    ("coluna", "valor", "mensagem"),
    [
        ("SepalLengthCm", "abc", "não convertido"),
        ("Id", "1.5", "não convertido"),
        ("Id", "2", "id repetido"),
        ("PetalWidthCm", "0", "menor ou igual a zero"),
        ("PetalWidthCm", None, "largura_petala_cm nulo"),
        ("Species", "Iris-rosa", "fora do domínio: rosa"),
        ("Species", None, "especie nula"),
    ],
)
def test_refinar_flores_rejeita_dado_fora_do_contrato(
    raw_flores: pd.DataFrame, coluna: str, valor: str | None, mensagem: str
) -> None:
    raw_flores.loc[0, coluna] = valor

    with pytest.raises(ValidacaoError, match=mensagem):
        refinar_flores(raw_flores)


def test_refinar_flores_rejeita_coluna_ausente(raw_flores: pd.DataFrame) -> None:
    with pytest.raises(ValidacaoError, match="colunas ausentes na raw: Species"):
        refinar_flores(raw_flores.drop(columns="Species"))
