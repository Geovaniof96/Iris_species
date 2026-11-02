"""Download do ``Iris.csv`` do Kaggle para a pasta ``raw/``.

Spec:

E1. Origem: ``kagglehub``, handle ``"uciml/iris"``, arquivo ``"Iris.csv"``. O
    ``database.sqlite`` do dataset é ignorado.
    Por quê: são os mesmos dados; duas fontes obrigam a decidir qual vale.

E2. O arquivo chega em ``raw/`` exatamente como o Kaggle entrega: sem parsear, sem
    renomear coluna, sem mudar encoding, sem compactar.
    Por quê: ``raw/`` é "o dado que chegou".

E3. Sempre baixa de novo (``force_download=True``) e substitui o existente.
    Por quê: o cache do kagglehub serviria uma versão antiga em silêncio.

E4. Baixa para uma pasta temporária ``.download_*`` criada dentro de ``raw/`` e só então
    move para ``raw/Iris.csv``. A pasta temporária some ao final, com sucesso ou erro.
    Por quê: um CSV cortado ao meio seria ingerido sem erro, com contagem errada que
    parece certa. A temporária fica dentro de ``raw/`` para que a troca seja atômica
    (``Path.replace`` usa ``os.replace``, e a troca é atômica no mesmo sistema de arquivos).

E5. Não exige nem lê credencial: o dataset é público.

E6. Qualquer falha no download, ou ``Iris.csv`` ausente no que veio, vira
    :class:`ExtracaoError`, e nada é escrito em ``raw/``.
"""

import tempfile
from pathlib import Path

import kagglehub

HANDLE = "uciml/iris"
ARQUIVO = "Iris.csv"


class ExtracaoError(Exception):
    """Falha ao baixar o arquivo do Kaggle."""


def baixar_iris(pasta_raw: Path) -> Path:
    """Baixa o ``Iris.csv`` e substitui ``pasta_raw/Iris.csv`` de forma atômica.

    Args:
        pasta_raw: Pasta de destino (criada se não existir).

    Returns:
        Caminho do arquivo gravado.

    Raises:
        ExtracaoError: Se o download falhar ou não trouxer o ``Iris.csv``.
    """
    pasta_raw.mkdir(parents=True, exist_ok=True)
    destino = pasta_raw / ARQUIVO
    with tempfile.TemporaryDirectory(prefix=".download_", dir=pasta_raw) as temporaria:
        try:
            devolvido = Path(
                kagglehub.dataset_download(
                    HANDLE, path=ARQUIVO, force_download=True, output_dir=temporaria
                )
            )
        # E6 pede tratar qualquer exceção do download (rede, HTTP, credencial...).
        except Exception as exc:
            raise ExtracaoError(f"falha ao baixar {ARQUIVO} de {HANDLE}: {exc}") from exc

        # O kagglehub pode devolver o próprio arquivo ou a pasta que o contém.
        baixado = devolvido if devolvido.is_file() else devolvido / ARQUIVO
        if not baixado.is_file():
            raise ExtracaoError(f"{ARQUIVO} ausente no que veio de {HANDLE} ({devolvido})")
        baixado.replace(destino)
    return destino
