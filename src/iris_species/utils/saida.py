"""Saída na tela comum a todos os scripts do pipeline.

Regras:

- ``stdout`` e ``stderr`` são reconfigurados para utf-8 no início de cada ``main()``.
  Por quê: no Prompt de Comando do Windows o acento sai embaralhado por padrão.
- A saída passa pelo ``logging`` (regra da SKILL), sem prefixos: ``INFO`` vai para
  ``stdout`` e ``WARNING`` ou acima vai para ``stderr``.
  Por quê: a spec define o texto exato de cada linha, e quem lê a tela não deve ver
  nível ou timestamp.
- Números com milhar separado por ponto (``1.234``).
"""

import logging
import sys
from io import TextIOWrapper

_FORMATO = "%(message)s"


class _SomenteAbaixoDeWarning(logging.Filter):
    """Deixa passar só os registros que vão para ``stdout``."""

    def filter(self, record: logging.LogRecord) -> bool:
        return record.levelno < logging.WARNING


def configurar_saida() -> None:
    """Reconfigura ``stdout``/``stderr`` para utf-8 e direciona o ``logging`` para eles."""
    for fluxo in (sys.stdout, sys.stderr):
        if isinstance(fluxo, TextIOWrapper):
            fluxo.reconfigure(encoding="utf-8")

    para_stdout = logging.StreamHandler(sys.stdout)
    para_stdout.setLevel(logging.INFO)
    para_stdout.addFilter(_SomenteAbaixoDeWarning())
    para_stderr = logging.StreamHandler(sys.stderr)
    para_stderr.setLevel(logging.WARNING)
    for handler in (para_stdout, para_stderr):
        handler.setFormatter(logging.Formatter(_FORMATO))

    # force=True: reexecutar main() no mesmo processo (testes) não duplica handlers.
    logging.basicConfig(level=logging.INFO, handlers=[para_stdout, para_stderr], force=True)


def formatar_numero(valor: int) -> str:
    """Formata um inteiro com milhar separado por ponto.

    Args:
        valor: Número a formatar.

    Returns:
        Texto como ``"1.234"``.
    """
    return f"{valor:,}".replace(",", ".")


def linha_tabela(schema: str, tabela: str, contagem: int) -> str:
    """Monta a linha de contagem de uma tabela, alinhada como na spec da ingestão.

    Args:
        schema: Schema da tabela.
        tabela: Nome da tabela.
        contagem: Linhas gravadas, lidas do banco.

    Returns:
        Linha alinhada: nome qualificado à esquerda, contagem à direita.
    """
    # Para o schema "raw" (3 letras) é idêntico ao f"{schema}.{tabela:<20}" da spec;
    # alinhar o nome qualificado inteiro mantém "refined" e "analytics" alinhados ao total.
    return f"{f'{schema}.{tabela}':<24} {formatar_numero(contagem):>10}"


def linha_total(total: int) -> str:
    """Monta a linha final de total, alinhada com :func:`linha_tabela`.

    Args:
        total: Soma das contagens.

    Returns:
        Linha alinhada com o total.
    """
    return f"{'total':<24} {formatar_numero(total):>10}"
