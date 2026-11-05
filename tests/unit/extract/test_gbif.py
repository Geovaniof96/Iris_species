import json
import urllib.error
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest
from pytest_mock import MockerFixture

from iris_species.extract import gbif
from iris_species.extract.gbif import baixar_gbif, url_especie, url_ocorrencias
from iris_species.extract.kaggle import ExtracaoError

CODIGOS = {"Iris setosa": 1, "Iris versicolor": 2, "Iris virginica": 3}


@pytest.fixture(autouse=True)
def sem_espera(mocker: MockerFixture):  # type: ignore[no-untyped-def]
    """As novas tentativas não esperam de verdade nos testes."""
    return mocker.patch.object(gbif.time, "sleep")


def _api_falsa(total_por_especie: int, match_type: str = "EXACT"):  # type: ignore[no-untyped-def]
    """Simula a API: species/match e occurrence/search paginado sobre `total_por_especie`."""
    chamadas: list[str] = []

    def baixar(url: str) -> bytes:
        chamadas.append(url)
        consulta = parse_qs(urlparse(url).query)
        if "/species/match" in url:
            nome = consulta["name"][0]
            return json.dumps({"usageKey": CODIGOS[nome], "matchType": match_type}).encode()
        offset, limite = int(consulta["offset"][0]), int(consulta["limit"][0])
        fim = min(offset + limite, total_por_especie)
        codigo = int(consulta["taxonKey"][0])
        resultados = [{"key": codigo * 100_000 + i} for i in range(offset, fim)]
        corpo = {"count": total_por_especie, "endOfRecords": fim >= total_por_especie}
        return json.dumps({**corpo, "results": resultados}).encode()

    return baixar, chamadas


def test_urls_usam_taxon_coordenada_e_paginacao() -> None:
    assert url_especie("Iris setosa").endswith("/species/match?name=Iris+setosa")
    consulta = parse_qs(urlparse(url_ocorrencias(5, 300, 200)).query)
    assert consulta["taxonKey"] == ["5"]
    assert consulta["hasCoordinate"] == ["true"]
    assert (consulta["offset"], consulta["limit"]) == (["300"], ["200"])


def test_baixar_gbif_pagina_ate_o_limite_e_grava_bytes_intactos(
    tmp_path: Path, mocker: MockerFixture
) -> None:
    baixar, chamadas = _api_falsa(total_por_especie=10_000)
    mocker.patch.object(gbif, "_baixar", side_effect=baixar)

    resumo = baixar_gbif(tmp_path, limite=650)

    # 650 por espécie = páginas de 300, 300 e 50.
    assert (resumo.especies, resumo.ocorrencias, resumo.arquivos) == (3, 1950, 12)
    paginas = sorted((tmp_path / "gbif" / "ocorrencias" / "setosa").iterdir())
    assert [p.name for p in paginas] == ["pagina_000.json", "pagina_001.json", "pagina_002.json"]
    assert len(json.loads(paginas[-1].read_text())["results"]) == 50
    assert (tmp_path / "gbif" / "especies" / "setosa.json").read_bytes() == baixar(chamadas[0])
    assert list(tmp_path.glob(".download_gbif_*")) == []


def test_baixar_gbif_para_no_fim_dos_registros(tmp_path: Path, mocker: MockerFixture) -> None:
    baixar, _ = _api_falsa(total_por_especie=120)
    mocker.patch.object(gbif, "_baixar", side_effect=baixar)

    resumo = baixar_gbif(tmp_path, limite=3000)

    assert (resumo.ocorrencias, resumo.arquivos) == (360, 6)


def test_baixar_gbif_substitui_pasta_anterior(tmp_path: Path, mocker: MockerFixture) -> None:
    antigo = tmp_path / "gbif" / "antigo.txt"
    antigo.parent.mkdir()
    antigo.write_text("x")
    baixar, _ = _api_falsa(total_por_especie=1)
    mocker.patch.object(gbif, "_baixar", side_effect=baixar)

    baixar_gbif(tmp_path)

    assert not antigo.exists()
    assert (tmp_path / "gbif" / "especies" / "virginica.json").is_file()


@pytest.mark.parametrize(
    "falha",
    [urllib.error.URLError("sem rede"), TimeoutError("demorou"), b"isto nao e json", b"[1, 2]"],
)
def test_baixar_gbif_com_falha_preserva_pasta_anterior(
    tmp_path: Path, mocker: MockerFixture, falha: Exception | bytes
) -> None:
    anterior = tmp_path / "gbif" / "especies" / "setosa.json"
    anterior.parent.mkdir(parents=True)
    anterior.write_text("versão anterior")
    if isinstance(falha, bytes):
        mocker.patch.object(gbif, "_baixar", return_value=falha)
    else:
        mocker.patch.object(gbif, "_baixar", side_effect=falha)

    with pytest.raises(ExtracaoError):
        baixar_gbif(tmp_path)

    assert anterior.read_text() == "versão anterior"
    assert list(tmp_path.glob(".download_gbif_*")) == []


def test_baixar_gbif_rejeita_correspondencia_nao_exata(
    tmp_path: Path, mocker: MockerFixture
) -> None:
    baixar, _ = _api_falsa(total_por_especie=1, match_type="FUZZY")
    mocker.patch.object(gbif, "_baixar", side_effect=baixar)

    with pytest.raises(ExtracaoError, match="correspondência exata"):
        baixar_gbif(tmp_path)

    assert not (tmp_path / "gbif").exists()


def test_baixar_gbif_rejeita_pagina_sem_results(tmp_path: Path, mocker: MockerFixture) -> None:
    def baixar(url: str) -> bytes:
        if "/species/match" in url:
            return b'{"usageKey": 1, "matchType": "EXACT"}'
        return b'{"count": 0}'

    mocker.patch.object(gbif, "_baixar", side_effect=baixar)

    with pytest.raises(ExtracaoError, match="results"):
        baixar_gbif(tmp_path)


def test_baixar_le_a_resposta_http(mocker: MockerFixture) -> None:
    resposta = mocker.MagicMock()
    resposta.__enter__.return_value.read.return_value = b"{}"
    urlopen = mocker.patch.object(gbif.urllib.request, "urlopen", return_value=resposta)

    assert gbif._baixar("https://api.gbif.org/v1/x") == b"{}"
    assert urlopen.call_args.kwargs["timeout"] == gbif.TIMEOUT_SEGUNDOS


def _http_erro(codigo: int) -> urllib.error.HTTPError:
    return urllib.error.HTTPError("https://api.gbif.org", codigo, "erro", {}, None)  # type: ignore[arg-type]


@pytest.mark.parametrize("falha", [TimeoutError("lenta"), _http_erro(503), _http_erro(429)])
def test_falha_temporaria_tenta_de_novo_e_avisa(
    tmp_path: Path,
    mocker: MockerFixture,
    sem_espera: object,
    falha: Exception,
    caplog: pytest.LogCaptureFixture,
) -> None:
    baixar, _ = _api_falsa(total_por_especie=1)
    falhas = iter([falha, falha])

    def instavel(url: str) -> bytes:
        proxima = next(falhas, None)
        if proxima is not None:
            raise proxima
        return baixar(url)

    mocker.patch.object(gbif, "_baixar", side_effect=instavel)

    resumo = baixar_gbif(tmp_path)

    assert resumo.ocorrencias == 3
    assert [c.args[0] for c in sem_espera.call_args_list] == [2.0, 4.0]  # type: ignore[attr-defined]
    assert "tentativa 1 de 4" in caplog.text


def test_falha_persistente_desiste_depois_das_tentativas(
    tmp_path: Path, mocker: MockerFixture
) -> None:
    baixar = mocker.patch.object(gbif, "_baixar", side_effect=TimeoutError("lenta"))

    with pytest.raises(ExtracaoError, match="lenta"):
        baixar_gbif(tmp_path)

    assert baixar.call_count == gbif.TENTATIVAS


def test_erro_http_4xx_falha_sem_nova_tentativa(tmp_path: Path, mocker: MockerFixture) -> None:
    baixar = mocker.patch.object(gbif, "_baixar", side_effect=_http_erro(404))

    with pytest.raises(ExtracaoError):
        baixar_gbif(tmp_path)

    assert baixar.call_count == 1
