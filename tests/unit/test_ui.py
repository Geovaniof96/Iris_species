import ast
from pathlib import Path

import duckdb
import pytest
from pytest_mock import MockerFixture

from iris_species import ui

RAIZ = Path(__file__).resolve().parents[2]


@pytest.fixture
def banco_tmp(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    caminho = tmp_path / "iris.duckdb"
    monkeypatch.setattr(ui, "_CAMINHO_BANCO", caminho)
    return caminho


def test_ui_aponta_para_o_banco_da_raiz() -> None:
    assert ui._CAMINHO_BANCO == RAIZ / "iris.duckdb"


def test_ui_nao_importa_nada_do_pacote() -> None:
    arvore = ast.parse(Path(ui.__file__).read_text(encoding="utf-8"))
    modulos = [no.module or "" for no in ast.walk(arvore) if isinstance(no, ast.ImportFrom)] + [
        nome.name for no in ast.walk(arvore) if isinstance(no, ast.Import) for nome in no.names
    ]
    assert not [m for m in modulos if m.startswith("iris_species")]


def test_ui_sem_banco_sai_sem_criar_arquivo(
    banco_tmp: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    with pytest.raises(SystemExit) as saida:
        ui.main()

    assert saida.value.code == 1
    assert "iris_species.ingestao" in capsys.readouterr().err
    assert not banco_tmp.exists()


def test_ui_sem_extensao_sai_com_codigo_1_e_fecha_conexao(
    banco_tmp: Path, mocker: MockerFixture, capsys: pytest.CaptureFixture[str]
) -> None:
    banco_tmp.touch()
    conexao = mocker.MagicMock()
    conexao.execute.side_effect = duckdb.IOException("Failed to download\nextension ui")
    mocker.patch.object(ui.duckdb, "connect", return_value=conexao)

    with pytest.raises(SystemExit) as saida:
        ui.main()

    assert saida.value.code == 1
    erro = capsys.readouterr().err
    assert "extensão ui" in erro
    assert "Failed to download extension ui" in erro
    conexao.close.assert_called_once()


def test_ui_ctrl_c_fecha_conexao_sem_traceback(
    banco_tmp: Path, mocker: MockerFixture, capsys: pytest.CaptureFixture[str]
) -> None:
    banco_tmp.touch()
    conexao = mocker.MagicMock()
    mocker.patch.object(ui.duckdb, "connect", return_value=conexao)
    mocker.patch.object(ui.time, "sleep", side_effect=KeyboardInterrupt)

    ui.main()

    executados = [chamada.args[0] for chamada in conexao.execute.call_args_list]
    assert executados == ["INSTALL ui", "LOAD ui", "CALL start_ui()"]
    assert capsys.readouterr().out == "http://localhost:4213\nCtrl+C para encerrar\n"
    conexao.close.assert_called_once()
