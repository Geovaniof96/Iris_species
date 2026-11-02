from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from iris_species.extract import kaggle
from iris_species.extract.kaggle import ARQUIVO, ExtracaoError, baixar_iris

CONTEUDO = b"Id,Species\r\n1,Iris-setosa\r\n"


def _simular_download(devolver_pasta: bool = False):  # type: ignore[no-untyped-def]
    def baixar(handle: str, path: str, *, force_download: bool, output_dir: str) -> str:
        assert (handle, path, force_download) == ("uciml/iris", ARQUIVO, True)
        arquivo = Path(output_dir) / ARQUIVO
        arquivo.write_bytes(CONTEUDO)
        return str(arquivo.parent if devolver_pasta else arquivo)

    return baixar


def _temporarias(pasta: Path) -> list[Path]:
    return list(pasta.glob(".download_*"))


@pytest.mark.parametrize("devolver_pasta", [False, True])
def test_baixar_iris_grava_bytes_intactos_aceitando_arquivo_ou_pasta(
    tmp_path: Path, mocker: MockerFixture, devolver_pasta: bool
) -> None:
    mocker.patch.object(kaggle.kagglehub, "dataset_download", _simular_download(devolver_pasta))
    raw = tmp_path / "raw"

    destino = baixar_iris(raw)

    assert destino == raw / ARQUIVO
    assert destino.read_bytes() == CONTEUDO
    assert _temporarias(raw) == []


def test_baixar_iris_substitui_arquivo_existente(tmp_path: Path, mocker: MockerFixture) -> None:
    mocker.patch.object(kaggle.kagglehub, "dataset_download", _simular_download())
    (tmp_path / ARQUIVO).write_bytes(b"antigo")

    baixar_iris(tmp_path)

    assert (tmp_path / ARQUIVO).read_bytes() == CONTEUDO


def test_baixar_iris_com_falha_preserva_arquivo_e_limpa_temporaria(
    tmp_path: Path, mocker: MockerFixture
) -> None:
    mocker.patch.object(
        kaggle.kagglehub, "dataset_download", side_effect=ConnectionError("sem rede")
    )
    (tmp_path / ARQUIVO).write_bytes(b"existente")

    with pytest.raises(ExtracaoError, match="sem rede"):
        baixar_iris(tmp_path)

    assert (tmp_path / ARQUIVO).read_bytes() == b"existente"
    assert _temporarias(tmp_path) == []


def test_baixar_iris_sem_iris_csv_no_download_falha(tmp_path: Path, mocker: MockerFixture) -> None:
    mocker.patch.object(
        kaggle.kagglehub,
        "dataset_download",
        side_effect=lambda *_, output_dir, **__: output_dir,
    )

    with pytest.raises(ExtracaoError, match="ausente"):
        baixar_iris(tmp_path)

    assert list(tmp_path.iterdir()) == []
