import logging

import pytest

from iris_species.utils.saida import (
    configurar_saida,
    formatar_numero,
    linha_tabela,
    linha_total,
)


@pytest.mark.parametrize(
    ("valor", "esperado"),
    [(0, "0"), (150, "150"), (5107, "5.107"), (1234567, "1.234.567")],
)
def test_formatar_numero_separa_milhar_com_ponto(valor: int, esperado: str) -> None:
    assert formatar_numero(valor) == esperado


def test_linha_tabela_raw_igual_ao_formato_da_spec() -> None:
    assert linha_tabela("raw", "flores", 1234) == f"{'raw'}.{'flores':<20} {'1.234':>10}"


def test_linha_total_alinha_com_linha_tabela() -> None:
    assert len(linha_total(153)) == len(linha_tabela("analytics", "especies", 3))
    assert linha_total(153) == f"{'total':<24} {'153':>10}"


def test_configurar_saida_info_no_stdout_e_erro_no_stderr(
    capsys: pytest.CaptureFixture[str],
) -> None:
    configurar_saida()
    logging.getLogger("teste").info("informação")
    logging.getLogger("teste").error("falhou")

    saida = capsys.readouterr()
    assert saida.out == "informação\n"
    assert saida.err == "falhou\n"
