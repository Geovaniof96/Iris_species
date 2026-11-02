"""Download da taxonomia e das ocorrências das três espécies de íris na API da GBIF.

Regras (segunda fonte do pipeline, no mesmo padrão da extração do Kaggle):

G1. Origem: API pública da GBIF (https://api.gbif.org/v1), sem chave. Para cada espécie,
    ``species/match`` dá a taxonomia e o ``usageKey``; ``occurrence/search`` dá as
    ocorrências com coordenada, paginadas de 300 em 300, até ``LIMITE_POR_ESPECIE``.
    Por quê: a Iris tem uma tabela só; a GBIF traz entidades diferentes (taxonomia e
    registros no mundo) que se ligam às flores pela espécie, o que dá sentido ao JOIN.

G2. Cada resposta é gravada em ``raw/gbif/`` exatamente como chegou (bytes da API):
    ``especies/<especie>.json`` e ``ocorrencias/<especie>/pagina_NNN.json``.
    Por quê: ``raw/`` é "o dado que chegou" (E2).

G3. Tudo é baixado numa pasta temporária ``.download_gbif_*`` dentro de ``raw/``, e a
    ``raw/gbif`` só é trocada no fim. Se algo falhar antes, a ``raw/gbif`` anterior fica
    intocada.
    Por quê: um conjunto de páginas pela metade seria ingerido sem erro (E4).

G4. Falha de rede, resposta HTTP de erro, JSON inválido ou espécie sem correspondência
    exata viram :class:`ExtracaoError`.
"""

import json
import tempfile
import urllib.error
import urllib.request
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any
from urllib.parse import urlencode

from iris_species.extract.kaggle import ExtracaoError

URL_BASE = "https://api.gbif.org/v1"
PASTA = "gbif"
ESPECIES: Mapping[str, str] = MappingProxyType(
    {"setosa": "Iris setosa", "versicolor": "Iris versicolor", "virginica": "Iris virginica"}
)
LIMITE_POR_ESPECIE = 3000
TAMANHO_PAGINA = 300
TIMEOUT_SEGUNDOS = 30


@dataclass(frozen=True)
class ResumoGbif:
    """O que a extração da GBIF gravou."""

    pasta: Path
    especies: int
    ocorrencias: int
    arquivos: int


def _baixar(url: str) -> bytes:
    # S310: a URL é sempre montada a partir de URL_BASE (https), nunca de entrada externa.
    requisicao = urllib.request.Request(url, headers={"User-Agent": "iris-species"})  # noqa: S310
    with urllib.request.urlopen(requisicao, timeout=TIMEOUT_SEGUNDOS) as resposta:  # noqa: S310
        corpo: bytes = resposta.read()
    return corpo


def _obter_json(url: str) -> tuple[bytes, dict[str, Any]]:
    try:
        corpo = _baixar(url)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise ExtracaoError(f"falha ao acessar {url}: {exc}") from exc
    try:
        dados = json.loads(corpo)
    except json.JSONDecodeError as exc:
        raise ExtracaoError(f"resposta não é JSON válido: {url}") from exc
    if not isinstance(dados, dict):
        raise ExtracaoError(f"resposta inesperada (não é um objeto JSON): {url}")
    return corpo, dados


def url_especie(nome: str) -> str:
    """Monta a URL de ``species/match`` para um nome científico."""
    return f"{URL_BASE}/species/match?{urlencode({'name': nome})}"


def url_ocorrencias(codigo: int, offset: int, limite: int) -> str:
    """Monta a URL de uma página de ``occurrence/search`` com coordenada válida."""
    parametros = {
        "taxonKey": codigo,
        "hasCoordinate": "true",
        "hasGeospatialIssue": "false",
        "occurrenceStatus": "PRESENT",
        "limit": limite,
        "offset": offset,
    }
    return f"{URL_BASE}/occurrence/search?{urlencode(parametros)}"


def _codigo_gbif(dados: dict[str, Any], nome: str) -> int:
    codigo = dados.get("usageKey")
    if dados.get("matchType") != "EXACT" or not isinstance(codigo, int):
        raise ExtracaoError(
            f"GBIF sem correspondência exata para {nome!r} (matchType={dados.get('matchType')})"
        )
    return codigo


def _gravar(caminho: Path, corpo: bytes) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_bytes(corpo)


def _trocar_pasta(nova: Path, destino: Path, temporaria: Path) -> None:
    # Path.replace não substitui pasta com conteúdo: a antiga vai para a temporária
    # (apagada ao sair) e volta se a troca falhar.
    antiga = temporaria / "antiga"
    if destino.exists():
        destino.replace(antiga)
    try:
        nova.replace(destino)
    except OSError:
        if antiga.exists():
            antiga.replace(destino)
        raise


def baixar_gbif(pasta_raw: Path, limite: int = LIMITE_POR_ESPECIE) -> ResumoGbif:
    """Baixa taxonomia e ocorrências das três espécies e substitui ``pasta_raw/gbif``.

    Args:
        pasta_raw: Pasta ``raw/`` (criada se não existir).
        limite: Máximo de ocorrências por espécie.

    Returns:
        Resumo com a pasta gravada e as contagens.

    Raises:
        ExtracaoError: Se qualquer requisição falhar ou vier fora do esperado.
    """
    pasta_raw.mkdir(parents=True, exist_ok=True)
    destino = pasta_raw / PASTA
    ocorrencias = arquivos = 0
    with tempfile.TemporaryDirectory(prefix=".download_gbif_", dir=pasta_raw) as tmp:
        temporaria = Path(tmp)
        nova = temporaria / PASTA
        for especie, nome in ESPECIES.items():
            corpo, dados = _obter_json(url_especie(nome))
            codigo = _codigo_gbif(dados, nome)
            _gravar(nova / "especies" / f"{especie}.json", corpo)
            arquivos += 1

            offset = pagina = 0
            while offset < limite:
                url = url_ocorrencias(codigo, offset, min(TAMANHO_PAGINA, limite - offset))
                corpo, dados = _obter_json(url)
                resultados = dados.get("results")
                if not isinstance(resultados, list):
                    raise ExtracaoError(f"resposta sem 'results': {url}")
                _gravar(nova / "ocorrencias" / especie / f"pagina_{pagina:03d}.json", corpo)
                arquivos += 1
                ocorrencias += len(resultados)
                offset += len(resultados)
                pagina += 1
                if dados.get("endOfRecords") or not resultados:
                    break
        _trocar_pasta(nova, destino, temporaria)
    return ResumoGbif(destino, len(ESPECIES), ocorrencias, arquivos)
