"""Interface do DuckDB sobre o ``iris.duckdb``: ``poetry run python -m iris_species.ui``.

Spec (o ``ui.py`` da raiz, movido para o pacote por causa do layout ``src/`` da SKILL):

U1. Abre o ``iris.duckdb`` da raiz do projeto (caminho a partir de ``__file__``) e executa
    ``INSTALL ui; LOAD ui; CALL start_ui()``, que sobe o servidor em
    http://localhost:4213 e abre o navegador.

U2. Imprime a URL e ``Ctrl+C para encerrar``, fica num laço de ``time.sleep(1)`` e, no
    ``KeyboardInterrupt``, fecha a conexão e sai limpo, sem traceback.
    Por quê: o ``.duckdb`` aceita um único processo escrevendo; com a UI de pé, a ingestão
    falha com ``Could not set lock on file``.

U3. Não cria banco: se o ``iris.duckdb`` não existir, mensagem em ``stderr`` mandando rodar
    a ingestão antes, e exit code 1. Por isso não usa ``conectar()``, que cria o arquivo.

U4. Se ``INSTALL``/``LOAD``/``start_ui`` falharem (ex.: sem internet), mensagem em ``stderr``
    com o erro do DuckDB numa linha, fecha a conexão e exit code 1, sem traceback.

U5. Não importa nada do restante do pacote (nem ``clients.db``, nem ``utils.saida``).
    Por quê: a extensão vem da internet, e a ingestão não pode depender dela.
"""

import logging
import sys
import time
from io import TextIOWrapper
from pathlib import Path

import duckdb

_CAMINHO_BANCO = Path(__file__).resolve().parents[2] / "iris.duckdb"
URL = "http://localhost:4213"

logger = logging.getLogger(__name__)


def _configurar_saida() -> None:
    # Cópia mínima de utils.saida.configurar_saida (U5 proíbe importar do pacote).
    for fluxo in (sys.stdout, sys.stderr):
        if isinstance(fluxo, TextIOWrapper):
            fluxo.reconfigure(encoding="utf-8")
    para_stdout = logging.StreamHandler(sys.stdout)
    para_stdout.addFilter(lambda registro: registro.levelno < logging.WARNING)
    para_stderr = logging.StreamHandler(sys.stderr)
    para_stderr.setLevel(logging.WARNING)
    logging.basicConfig(
        level=logging.INFO, format="%(message)s", handlers=[para_stdout, para_stderr], force=True
    )


def _em_uma_linha(exc: BaseException) -> str:
    return " ".join(str(exc).split())


def main() -> None:
    """Sobe a interface do DuckDB e espera o Ctrl+C."""
    _configurar_saida()
    if not _CAMINHO_BANCO.is_file():
        logger.error("Banco não encontrado: %s", _CAMINHO_BANCO)
        logger.error("Rode antes: poetry run python -m iris_species.ingestao")
        sys.exit(1)

    con = duckdb.connect(str(_CAMINHO_BANCO))
    try:
        try:
            con.execute("INSTALL ui")
            con.execute("LOAD ui")
            con.execute("CALL start_ui()").fetchall()
        except duckdb.Error as exc:
            logger.error("A extensão ui do DuckDB não pôde ser instalada/carregada.")
            logger.error("%s", _em_uma_linha(exc))
            sys.exit(1)

        logger.info(URL)
        logger.info("Ctrl+C para encerrar")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
    finally:
        con.close()


if __name__ == "__main__":
    main()
