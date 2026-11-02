"""Etapa de transformação: ``poetry run python -m iris_species.transformacao``.

Regras (extras à spec original):

T1. A saída na tela tem o mesmo formato da ingestão (I6): uma linha por tabela com a
    contagem vinda do banco e uma linha final com o total.
T2. Se faltar tabela na raw: mensagem em ``stderr`` mandando rodar a ingestão
    antes, e exit code 1. Se o contrato da refined falhar: o motivo vai para ``stderr``,
    exit code 1 e nada é gravado. A conexão é fechada num ``finally``.
T3. Não baixa nada e não lê ``raw/``: só lê o banco.
    Por quê: o mesmo princípio de E8 (cada etapa reexecutável isoladamente).
"""

import logging
import sys

import duckdb

from iris_species.clients import db
from iris_species.load.camadas import processar_camadas
from iris_species.transform.refined import ValidacaoError
from iris_species.utils.saida import configurar_saida, linha_tabela, linha_total

logger = logging.getLogger(__name__)


def main() -> None:
    """Gera as camadas refined e analytics e mostra as contagens."""
    configurar_saida()
    con = db.conectar()
    try:
        resultados = processar_camadas(con)
    except duckdb.CatalogException as exc:
        logger.error("tabela da raw não encontrada: %s", exc)
        logger.error("Rode antes: poetry run python -m iris_species.ingestao")
        sys.exit(1)
    except ValidacaoError as exc:
        logger.error("raw fora do contrato da refined: %s", exc)
        sys.exit(1)
    finally:
        con.close()

    for schema, tabela, contagem in resultados:
        logger.info("%s", linha_tabela(schema, tabela, contagem))
    logger.info("%s", linha_total(sum(contagem for _, _, contagem in resultados)))


if __name__ == "__main__":
    main()
