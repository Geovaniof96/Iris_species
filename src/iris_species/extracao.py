"""Etapa de extração: ``poetry run python -m iris_species.extracao``.

Spec:

E6. Em erro: mensagem em ``stderr`` dizendo o que falhou, uma linha sugerindo configurar
    ``~/.kaggle/kaggle.json`` ou ``KAGGLE_API_TOKEN`` caso seja credencial, e exit code 1.
E7. Em sucesso, uma linha: caminho absoluto gravado e tamanho em bytes
    (``/caminho/raw/Iris.csv  5.107 bytes``).
E8. A extração não abre o banco.
    Por quê: assim dá para rebaixar o arquivo sem mexer no banco.
"""

import logging
import sys

from iris_species.clients import db
from iris_species.extract.kaggle import ExtracaoError, baixar_iris
from iris_species.utils.saida import configurar_saida, formatar_numero

logger = logging.getLogger(__name__)

DICA_CREDENCIAL = (
    "Se for erro de credencial, configure ~/.kaggle/kaggle.json ou a variável KAGGLE_API_TOKEN."
)


def main() -> None:
    """Baixa o ``Iris.csv`` para ``raw/`` e mostra caminho e tamanho."""
    configurar_saida()
    # O kagglehub registra o próprio progresso no logging; a spec pede uma linha só.
    logging.getLogger("kagglehub").setLevel(logging.WARNING)
    try:
        destino = baixar_iris(db.PASTA_RAW)
    except ExtracaoError as exc:
        logger.error("%s", exc)
        logger.error(DICA_CREDENCIAL)
        sys.exit(1)
    logger.info("%s  %s bytes", destino, formatar_numero(destino.stat().st_size))


if __name__ == "__main__":
    main()
