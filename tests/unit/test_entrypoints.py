from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from iris_species import extracao, ingestao, transformacao
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
    projeto_tmp: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (projeto_tmp / "raw").mkdir()
    (projeto_tmp / "raw" / "Iris.csv").write_text(CSV, encoding="utf-8")

    saidas = []
    for _ in range(2):
        ingestao.main()
        transformacao.main()
        saidas.append(capsys.readouterr().out)

    assert saidas[0] == saidas[1]
    assert saidas[0].splitlines() == [
        f"{'raw.flores':<24} {'1':>10}",
        f"{'total':<24} {'1':>10}",
        f"{'refined.flores':<24} {'1':>10}",
        f"{'analytics.especies':<24} {'1':>10}",
        f"{'total':<24} {'2':>10}",
    ]


def test_transformacao_sem_raw_sai_com_codigo_1(
    projeto_tmp: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    with pytest.raises(SystemExit) as saida:
        transformacao.main()

    assert saida.value.code == 1
    assert "iris_species.ingestao" in capsys.readouterr().err


def test_transformacao_com_contrato_violado_sai_com_codigo_1(
    projeto_tmp: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (projeto_tmp / "raw").mkdir()
    (projeto_tmp / "raw" / "Iris.csv").write_text(
        CSV.replace("Iris-setosa", "Iris-rosa"), encoding="utf-8"
    )
    ingestao.main()

    with pytest.raises(SystemExit) as saida:
        transformacao.main()

    assert saida.value.code == 1
    assert "rosa" in capsys.readouterr().err
