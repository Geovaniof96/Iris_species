from collections.abc import Iterator
from pathlib import Path

import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

from iris_species.dashboard import app, dados

ARQUIVO_APP = str(Path(app.__file__))


@pytest.fixture(autouse=True)
def limpar_cache() -> Iterator[None]:
    st.cache_data.clear()
    yield
    st.cache_data.clear()


def _rodar(monkeypatch: pytest.MonkeyPatch, caminho: Path) -> AppTest:
    monkeypatch.setattr(dados, "CAMINHO_BANCO", caminho)
    return AppTest.from_file(ARQUIVO_APP, default_timeout=30).run()


def test_app_mostra_kpis_e_graficos(monkeypatch: pytest.MonkeyPatch, banco_dashboard: Path) -> None:
    pagina = _rodar(monkeypatch, banco_dashboard)

    assert not pagina.exception
    rotulos = {metrica.label: metrica.value for metrica in pagina.metric}
    assert rotulos["Flores medidas"] == "3"
    assert rotulos["Ocorrências GBIF"] == "2"
    assert rotulos["Período dos registros"] == "2020-2024"
    assert len(pagina.get("plotly_chart")) == 5


def test_app_filtro_de_especie_recalcula_kpis(
    monkeypatch: pytest.MonkeyPatch, banco_dashboard: Path
) -> None:
    pagina = _rodar(monkeypatch, banco_dashboard)

    pagina.multiselect[0].set_value(["setosa"]).run()

    rotulos = {metrica.label: metrica.value for metrica in pagina.metric}
    assert rotulos["Flores medidas"] == "1"
    assert rotulos["Ocorrências GBIF"] == "1"
    assert rotulos["Pétala: maior ÷ menor média"] == "—"


def test_app_sem_especie_pede_selecao(
    monkeypatch: pytest.MonkeyPatch, banco_dashboard: Path
) -> None:
    pagina = _rodar(monkeypatch, banco_dashboard)

    pagina.multiselect[0].set_value([]).run()

    assert pagina.info[0].value == "Selecione ao menos uma espécie."
    assert not pagina.metric


def test_app_sem_banco_mostra_erro(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    pagina = _rodar(monkeypatch, tmp_path / "iris.duckdb")

    assert not pagina.exception
    assert "make pipeline" in pagina.error[0].value
