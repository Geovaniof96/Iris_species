"""Etapa de ingestão: ``poetry run python -m iris_species.ingestao``.

Spec:

I6. Uma linha por tabela com nome qualificado e contagem vinda do banco, e uma linha
    final com o total, alinhadas.
I7. Antes de abrir o banco, verifica se todos os arquivos do mapa (e os da GBIF) existem. Se faltar
    algum: lista os ausentes em ``stderr``, diz em que pasta procurou e sai com exit code
    1, sem criar o ``iris.duckdb``. A conexão é fechada num ``finally``.
    Por quê: um banco vazio criado sem dados parece ingestão quebrada.
E8. A ingestão não baixa nada.
    Por quê: assim dá para reingerir sem rede.
"""

import logging
import sys

from iris_species.clients import db
from iris_species.load.raw import arquivos_faltando, ingerir
from iris_species.load.raw_gbif import gbif_faltando, ingerir_gbif
from iris_species.utils.saida import configurar_saida, linha_tabela, linha_total

logger = logging.getLogger(__name__)


def main() -> None:
    """Grava os arquivos de ``raw/`` no schema ``raw`` e mostra as contagens."""
    configurar_saida()
    faltando = arquivos_faltando(db.PASTA_RAW) + gbif_faltando(db.PASTA_RAW)
    if faltando:
        for arquivo in faltando:
            logger.error("arquivo ausente: %s", arquivo)
        logger.error("procurado em: %s", db.PASTA_RAW)
        sys.exit(1)

    con = db.conectar()
    try:
        resultados = ingerir(con, db.PASTA_RAW) + ingerir_gbif(con, db.PASTA_RAW)
    finally:
        con.close()

    for schema, tabela, contagem in resultados:
        logger.info("%s", linha_tabela(schema, tabela, contagem))
    logger.info("%s", linha_total(sum(contagem for _, _, contagem in resultados)))


if __name__ == "__main__":
    main()
