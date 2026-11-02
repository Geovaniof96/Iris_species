"""Extração da GBIF: ``poetry run python -m iris_species.extracao_gbif``.

Regras (mesmo padrão de E6 a E8 da extração do Kaggle):

- Em sucesso, uma linha: pasta gravada, espécies, ocorrências e arquivos
  (``/caminho/raw/gbif  3 espécies  9.000 ocorrências  33 arquivos``).
- Em erro: o motivo em ``stderr`` e exit code 1; a ``raw/gbif`` anterior fica intocada.
- Não abre o banco.
  Por quê: assim dá para rebaixar a fonte sem mexer no banco.
"""

import logging
import sys

from iris_species.clients import db
from iris_species.extract.gbif import baixar_gbif
from iris_species.extract.kaggle import ExtracaoError
from iris_species.utils.saida import configurar_saida, formatar_numero

logger = logging.getLogger(__name__)


def main() -> None:
    """Baixa taxonomia e ocorrências da GBIF para ``raw/gbif`` e mostra o resumo."""
    configurar_saida()
    try:
        resumo = baixar_gbif(db.PASTA_RAW)
    except ExtracaoError as exc:
        logger.error("%s", exc)
        logger.error("Verifique a conexão com https://api.gbif.org e rode de novo.")
        sys.exit(1)
    logger.info(
        "%s  %s espécies  %s ocorrências  %s arquivos",
        resumo.pasta,
        resumo.especies,
        formatar_numero(resumo.ocorrencias),
        formatar_numero(resumo.arquivos),
    )


if __name__ == "__main__":
    main()
