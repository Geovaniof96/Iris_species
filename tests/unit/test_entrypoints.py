from collections.abc import Callable
from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from iris_species import extracao, extracao_gbif, ingestao, transformacao
from iris_species.extract.gbif import ResumoGbif
from iris_species.extract.kaggle import ExtracaoError

CSV = (
    "Id,SepalLengthCm,SepalWidthCm,PetalLengthCm,PetalWidthCm,Species\n"
    "1,5.1,3.5,1.4,0.2,Iris-setosa\n"
)


def test_extracao_mostra_caminho_e_tamanho(
    projeto_tmp: Path, mocker: MockerFixture, capsys: pytest.CaptureFixture[str]
) -> None:
    destino = projeto_tmp / "raw" / "Iris.csv"
    destino.parent.mkdir()
    destino.write_bytes(b"x" * 5107)
    mocker.patch.object(extracao, "baixar_iris", return_value=destino)

    extracao.main()

    assert capsys.readouterr().out == f"{destino}  5.107 bytes\n"
    assert not (projeto_tmp / "iris.duckdb").exists()


def test_extracao_com_falha_sai_com_codigo_1_e_dica(
    projeto_tmp: Path, mocker: MockerFixture, capsys: pytest.CaptureFixture[str]
) -> None:
    mocker.patch.object(extracao, "baixar_iris", side_effect=ExtracaoError("sem rede"))

    with pytest.raises(SystemExit) as saida:
        extracao.main()

    assert saida.value.code == 1
    erro = capsys.readouterr().err
    assert "sem rede" in erro
    assert "KAGGLE_API_TOKEN" in erro


def test_ingestao_sem_arquivo_sai_sem_criar_banco(
    projeto_tmp: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    with pytest.raises(SystemExit) as saida:
        ingestao.main()

    assert saida.value.code == 1
    erro = capsys.readouterr().err
    assert "Iris.csv" in erro
    assert str(projeto_tmp / "raw") in erro
    assert not (projeto_tmp / "iris.duckdb").exists()


def test_ingestao_e_transformacao_reexecutadas_imprimem_o_mesmo(
    projeto_tmp: Path, gravar_gbif: Callable[..., None], capsys: pytest.CaptureFixture[str]
) -> None:
    (projeto_tmp / "raw").mkdir()
    (projeto_tmp / "raw" / "Iris.csv").write_text(CSV, encoding="utf-8")
    gravar_gbif(projeto_tmp / "raw")

    saidas = []
    for _ in range(2):
        ingestao.main()
        transformacao.main()
        saidas.append(capsys.readouterr().out)

    assert saidas[0] == saidas[1]
    assert saidas[0].splitlines() == [
        f"{'raw.flores':<24} {'1':>10}",
        f"{'raw.gbif_especies':<24} {'3':>10}",
        f"{'raw.gbif_ocorrencias':<24} {'4':>10}",
        f"{'total':<24} {'8':>10}",
        f"{'refined.flores':<24} {'1':>10}",
        f"{'refined.especies':<24} {'3':>10}",
        f"{'refined.ocorrencias':<24} {'4':>10}",
        f"{'analytics.especies':<24} {'1':>10}",
        f"{'analytics.panorama':<24} {'1':>10}",
        f"{'analytics.paises':<24} {'1':>10}",
        f"{'total':<24} {'11':>10}",
    ]


def test_ingestao_sem_gbif_sai_sem_criar_banco(
    projeto_tmp: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (projeto_tmp / "raw").mkdir()
    (projeto_tmp / "raw" / "Iris.csv").write_text(CSV, encoding="utf-8")

    with pytest.raises(SystemExit) as saida:
        ingestao.main()

    assert saida.value.code == 1
    assert "gbif/especies/setosa.json" in capsys.readouterr().err
    assert not (projeto_tmp / "iris.duckdb").exists()


def test_extracao_gbif_mostra_resumo(
    projeto_tmp: Path, mocker: MockerFixture, capsys: pytest.CaptureFixture[str]
) -> None:
    resumo = ResumoGbif(projeto_tmp / "raw" / "gbif", 3, 9000, 33)
    mocker.patch.object(extracao_gbif, "baixar_gbif", return_value=resumo)

    extracao_gbif.main()

    assert capsys.readouterr().out == (
        f"{resumo.pasta}  3 espécies  9.000 ocorrências  33 arquivos\n"
    )


def test_extracao_gbif_com_falha_sai_com_codigo_1(
    projeto_tmp: Path, mocker: MockerFixture, capsys: pytest.CaptureFixture[str]
) -> None:
    mocker.patch.object(extracao_gbif, "baixar_gbif", side_effect=ExtracaoError("sem rede"))

    with pytest.raises(SystemExit) as saida:
        extracao_gbif.main()

    assert saida.value.code == 1
    assert "sem rede" in capsys.readouterr().err


def test_transformacao_sem_raw_sai_com_codigo_1(
    projeto_tmp: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    with pytest.raises(SystemExit) as saida:
        transformacao.main()

    assert saida.value.code == 1
    assert "iris_species.ingestao" in capsys.readouterr().err


def test_transformacao_com_contrato_violado_sai_com_codigo_1(
    projeto_tmp: Path, gravar_gbif: Callable[..., None], capsys: pytest.CaptureFixture[str]
) -> None:
    (projeto_tmp / "raw").mkdir()
    (projeto_tmp / "raw" / "Iris.csv").write_text(
        CSV.replace("Iris-setosa", "Iris-rosa"), encoding="utf-8"
    )
    gravar_gbif(projeto_tmp / "raw")
    ingestao.main()

    with pytest.raises(SystemExit) as saida:
        transformacao.main()

    assert saida.value.code == 1
    assert "rosa" in capsys.readouterr().err
