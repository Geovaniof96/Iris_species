from pathlib import Path

import duckdb
import pytest
from pytest_mock import MockerFixture

from iris_species.dashboard import dados


def test_carregar_dados_le_as_tres_tabelas(banco_dashboard: Path) -> None:
    painel = dados.carregar_dados(banco_dashboard)

    assert len(painel.flores) == 3
    assert len(painel.ocorrencias) == 2
    assert painel.panorama["especie"].tolist() == ["setosa", "versicolor", "virginica"]


def test_carregar_dados_usa_o_banco_padrao(
    banco_dashboard: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(dados, "CAMINHO_BANCO", banco_dashboard)

    assert len(dados.carregar_dados().flores) == 3


def test_carregar_dados_nao_cria_banco(tmp_path: Path) -> None:
    caminho = tmp_path / "iris.duckdb"

    with pytest.raises(dados.DadosIndisponiveisError, match="make pipeline"):
        dados.carregar_dados(caminho)
    assert not caminho.exists()


def test_carregar_dados_sem_tabela_pede_a_transformacao(tmp_path: Path) -> None:
    caminho = tmp_path / "iris.duckdb"
    duckdb.connect(str(caminho)).close()

    with pytest.raises(dados.DadosIndisponiveisError, match="make transformacao"):
        dados.carregar_dados(caminho)


def test_carregar_dados_banco_bloqueado(banco_dashboard: Path, mocker: MockerFixture) -> None:
    mocker.patch.object(
        dados.duckdb, "connect", side_effect=duckdb.IOException("Could not set lock on file")
    )

    with pytest.raises(dados.DadosIndisponiveisError, match="em uso"):
        dados.carregar_dados(banco_dashboard)


def test_carregar_dados_nao_escreve(banco_dashboard: Path) -> None:
    antes = banco_dashboard.stat().st_mtime_ns

    dados.carregar_dados(banco_dashboard)

    assert banco_dashboard.stat().st_mtime_ns == antes
