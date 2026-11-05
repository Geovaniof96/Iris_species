import json

import pandas as pd
import pytest

from iris_species.transform.gbif import refinar_especies, refinar_ocorrencias
from iris_species.transform.refined import ValidacaoError


def _documento(especie: str, **extra: object) -> str:
    base = {
        "usageKey": len(especie),
        "scientificName": f"Iris {especie} L.",
        "canonicalName": f"Iris {especie}",
        "rank": "SPECIES",
        "status": "ACCEPTED",
        "family": "Iridaceae",
        "genus": "Iris",
    }
    return json.dumps({**base, **extra})


def _raw_especies(**extra_setosa: object) -> pd.DataFrame:
    linhas = [
        ("setosa", "gbif/especies/setosa.json", _documento("setosa", **extra_setosa)),
        ("versicolor", "gbif/especies/versicolor.json", _documento("versicolor")),
        ("virginica", "gbif/especies/virginica.json", _documento("virginica")),
    ]
    return pd.DataFrame(linhas, columns=["especie_arquivo", "arquivo", "documento"], dtype=str)


def _registro(gbif_id: object, **extra: object) -> str:
    base = {
        "key": gbif_id,
        "countryCode": "US",
        "country": "United States of America",
        "stateProvince": None,
        "year": 2024,
        "month": None,
        "decimalLatitude": 40.1,
        "decimalLongitude": -75.2,
        "basisOfRecord": "HUMAN_OBSERVATION",
        "license": "CC_BY_4_0",
    }
    return json.dumps({**base, **extra})


def _raw_ocorrencias(*registros: str, especie: str = "virginica") -> pd.DataFrame:
    linhas = [(especie, "gbif/ocorrencias/x/pagina_000.json", r) for r in registros]
    return pd.DataFrame(linhas, columns=["especie_arquivo", "arquivo", "registro"], dtype=str)


def test_refinar_especies_extrai_taxonomia() -> None:
    df = refinar_especies(_raw_especies())

    assert df.columns.tolist() == [
        "especie",
        "gbif_codigo",
        "nome_cientifico",
        "familia",
        "genero",
        "status",
    ]
    assert df.loc[0].tolist() == ["setosa", 6, "Iris setosa L.", "Iridaceae", "Iris", "ACCEPTED"]
    assert str(df["gbif_codigo"].dtype) == "Int64"


@pytest.mark.parametrize(
    ("extra", "mensagem"),
    [
        ({"canonicalName": "Iris pumila"}, "esperado Iris setosa"),
        ({"rank": "GENUS"}, "SPECIES"),
    ],
)
def test_refinar_especies_rejeita_taxonomia_errada(extra: dict[str, object], mensagem: str) -> None:
    with pytest.raises(ValidacaoError, match=mensagem):
        refinar_especies(_raw_especies(**extra))


def test_refinar_especies_exige_as_tres_especies() -> None:
    with pytest.raises(ValidacaoError, match="diferentes"):
        refinar_especies(_raw_especies().iloc[:2])


def test_refinar_especies_rejeita_json_invalido() -> None:
    raw = _raw_especies()
    raw.loc[0, "documento"] = "{quebrado"

    with pytest.raises(ValidacaoError, match="JSON inválido"):
        refinar_especies(raw)


def test_refinar_ocorrencias_tipa_e_preserva_nulos() -> None:
    df = refinar_ocorrencias(_raw_ocorrencias(_registro(10)))

    linha = df.loc[0]
    assert (linha["gbif_id"], linha["especie"], linha["ano"], linha["latitude"]) == (
        10,
        "virginica",
        2024,
        40.1,
    )
    assert pd.isna(linha["estado"])
    assert pd.isna(linha["mes"])
    assert str(df["latitude"].dtype) == "Float64"


def test_refinar_ocorrencias_remove_gbif_id_repetido() -> None:
    df = refinar_ocorrencias(
        _raw_ocorrencias(_registro(1), _registro(2), _registro(1, country="Canada"))
    )

    assert df["gbif_id"].tolist() == [1, 2]
    assert df.loc[0, "pais"] == "United States of America"


@pytest.mark.parametrize(
    ("registro", "mensagem"),
    [
        (_registro(None), "gbif_id nulo"),
        (_registro(1, decimalLatitude=95.0), "latitude fora"),
        (_registro(1, decimalLongitude=None), "longitude nula"),
        (_registro("abc"), "não convertido"),
    ],
)
def test_refinar_ocorrencias_rejeita_fora_do_contrato(registro: str, mensagem: str) -> None:
    with pytest.raises(ValidacaoError, match=mensagem):
        refinar_ocorrencias(_raw_ocorrencias(registro))


def test_refinar_ocorrencias_rejeita_especie_fora_do_dominio() -> None:
    with pytest.raises(ValidacaoError, match="especie fora do domínio"):
        refinar_ocorrencias(_raw_ocorrencias(_registro(1), especie="pumila"))
