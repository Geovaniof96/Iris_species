---
name: python-data-eng-standards
description: Use ao criar projeto Python, adicionar dependência, escrever testes, configurar lint/docs ou criar, revisar e alterar código Python do time de Engenharia de Dados.
---

# Padrões Python do time de Engenharia de Dados

Siga estas regras à risca sempre que criar, revisar ou alterar código Python do time
(pipelines, extratores em AWS Lambda, bibliotecas internas, utilitários). Se uma
regra conflitar com um pedido, avise o usuário antes de quebrá-la.
Modelos SQL/dbt seguem os padrões próprios do dbt e ficam fora deste guia.

## 1. Poetry e layout `src/`

### Regras
- Use **Poetry 2.x** para gerenciar a venv e os pacotes. Sempre.
- **Nunca** use `pip install`, `pip freeze` ou `requirements.txt` editado à mão.
- Sempre use o layout `src/` (padrão do `poetry new` no Poetry 2.x).
- Sempre versione o `poetry.lock` no git.
- Sempre deixe a venv em `.venv/` na raiz: `virtualenvs.in-project = true`.
- Separe as dependências por grupo:
  - principal: o que roda em produção (`boto3`, `pydantic-settings`, ...)
  - `dev`: `ruff`, `pytest`, `pytest-cov`, `pytest-mock`, `moto`, `mypy`, `pre-commit`
  - `docs`: `mkdocs-material`, `mkdocstrings[python]`
- Fixe `requires-python` alinhado ao runtime da Lambda (ex.: `python3.12` → `">=3.12,<3.13"`).

### Estrutura obrigatória
```
projeto/
├── pyproject.toml
├── poetry.lock
├── poetry.toml              # virtualenvs.in-project = true
├── README.md
├── Makefile
├── mkdocs.yml
├── .pre-commit-config.yaml
├── .gitignore
├── src/
│   └── nome_projeto/
│       ├── __init__.py
│       ├── handler.py       # entrypoint: só orquestra
│       ├── config/
│       ├── clients/         # I/O: S3, APIs, banco, Secrets Manager
│       ├── extract/
│       ├── transform/
│       ├── load/
│       └── utils/
├── tests/
│   ├── conftest.py
│   └── unit/                # espelha src/nome_projeto/
└── docs/
```

### Comandos
```bash
poetry new nome-projeto                       # cria o projeto (layout src/)
poetry config virtualenvs.in-project true --local
poetry install                                # cria .venv e instala tudo
poetry add requests                           # dependência de produção
poetry add --group dev pytest                 # dependência de desenvolvimento
poetry add --group docs mkdocs-material       # dependência de documentação
poetry remove requests
poetry lock                                   # regenera o lock
poetry run pytest                             # executa comando na venv
poetry env info                               # mostra a venv em uso
eval $(poetry env activate)                   # ativa a venv (no 2.x, `poetry shell` virou plugin)
```

### Empacotar para Lambda
Gere o requirements só pelo `poetry export`, nunca à mão:
```bash
poetry self add poetry-plugin-export
poetry export -f requirements.txt --only main -o build/requirements.txt
```
Não versione o arquivo gerado. Gere-o no build/CI.

## 2. Modularidade

- Cada módulo tem uma responsabilidade: `config`, `clients`, `extract`, `transform`, `load`, `utils`.
- **Nunca** coloque lógica de negócio no `handler`/`main`. O entrypoint só lê a config,
  instancia clientes e chama funções testáveis.
- Escreva funções pequenas e, sempre que possível, puras (o `transform` não faz I/O).
- Isole o I/O (S3, APIs, banco) em clientes ou adaptadores injetáveis e fáceis de mockar.
- Use imports absolutos: `from nome_projeto.extract.api import fetch_orders`.
- Proibido: imports circulares, `import *` e variáveis globais mutáveis.
- Leia a configuração de variáveis de ambiente em **um único módulo** (`config/`), com `pydantic-settings`.
- **Nunca** coloque credenciais no código ou no repositório. Busque os segredos no AWS Secrets Manager ou no SSM.

### Exemplo
```python
# src/nome_projeto/config/settings.py
"""Configuração da aplicação lida de variáveis de ambiente."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configurações do pipeline."""

    model_config = SettingsConfigDict(env_prefix="APP_")

    bucket_name: str
    api_base_url: str
    api_secret_id: str  # id no Secrets Manager, nunca o segredo em si
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    """Retorna as configurações (cacheadas)."""
    return Settings()
```

```python
# src/nome_projeto/transform/orders.py
"""Transformações puras de pedidos."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Order:
    """Pedido normalizado."""

    order_id: str
    amount_cents: int


def normalize_orders(raw: list[dict[str, object]]) -> list[Order]:
    """Normaliza pedidos brutos da API.

    Args:
        raw: Registros brutos retornados pela API.

    Returns:
        Pedidos normalizados, sem duplicados por `order_id`.
    """
    unique = {str(r["id"]): r for r in raw}
    return [
        Order(order_id=oid, amount_cents=round(float(str(r["amount"])) * 100))
        for oid, r in unique.items()
    ]
```

```python
# src/nome_projeto/handler.py
"""Entrypoint da Lambda: apenas orquestra."""

import logging
from typing import Any

from nome_projeto.clients.api import OrdersApiClient
from nome_projeto.clients.s3 import S3Writer
from nome_projeto.config.settings import get_settings
from nome_projeto.load.orders import save_orders
from nome_projeto.transform.orders import normalize_orders

logger = logging.getLogger(__name__)


def handler(event: dict[str, Any], context: object) -> dict[str, Any]:
    """Extrai, transforma e grava os pedidos da data de referência."""
    settings = get_settings()
    ref_date = event["ref_date"]
    raw = OrdersApiClient.from_settings(settings).fetch_orders(ref_date)
    orders = normalize_orders(raw)
    key = save_orders(S3Writer(settings.bucket_name), orders, ref_date)
    logger.info("pipeline concluído", extra={"ref_date": ref_date, "rows": len(orders)})
    return {"status": "ok", "rows": len(orders), "key": key}
```

## 3. Ruff (lint + formatter + imports)

- Use o **Ruff** como ÚNICA ferramenta de lint e formatação. Nunca adicione black, isort ou flake8.
- Deixe a organização de imports com o Ruff (regra `I`).
- Justifique todo `ignore` e todo `# noqa` com um comentário.

```bash
poetry run ruff check . --fix     # lint com correção automática
poetry run ruff format .          # formata
# CI:
poetry run ruff check .
poetry run ruff format --check .
```

### pre-commit
```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v5.0.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
        args: [--unsafe]   # mkdocs.yml usa tags customizadas
      - id: check-added-large-files
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.8.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
```
```bash
poetry run pre-commit install
poetry run pre-commit autoupdate   # atualiza os revs
```

## 4. Testes com pytest (cobertura mínima de 50%)

- Escreva os testes em `tests/unit/`, espelhando `src/` (`src/nome_projeto/transform/orders.py` → `tests/unit/transform/test_orders.py`).
- Nomeie os arquivos `test_<modulo>.py` e as funções `test_<comportamento_esperado>()`.
- Coloque as fixtures compartilhadas em `conftest.py`. Use `pytest.mark.parametrize` para variações.
- Mocke AWS com `moto` e o resto com `pytest-mock`. Testes unitários **nunca** acessam rede, S3 ou banco reais.
- Toda função nova ou alterada ganha teste. Todo bug corrigido ganha teste de regressão.
- A cobertura mínima é de **50%** e quebra o build se não for atingida (`--cov-fail-under=50`).
- Comando: `poetry run pytest`.

```python
# tests/conftest.py
import boto3
import pytest
from moto import mock_aws


@pytest.fixture(autouse=True)
def aws_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")


@pytest.fixture
def s3_bucket():
    with mock_aws():
        s3 = boto3.client("s3")
        s3.create_bucket(Bucket="test-bucket")
        yield s3
```

```python
# tests/unit/transform/test_orders.py
import pytest

from nome_projeto.transform.orders import Order, normalize_orders


@pytest.mark.parametrize(
    ("amount", "expected"),
    [("10.00", 1000), ("0.01", 1), ("0", 0)],
)
def test_normalize_orders_converts_amount_to_cents(amount: str, expected: int) -> None:
    result = normalize_orders([{"id": "1", "amount": amount}])
    assert result == [Order(order_id="1", amount_cents=expected)]


def test_normalize_orders_removes_duplicates() -> None:
    raw = [{"id": "1", "amount": "1"}, {"id": "1", "amount": "1"}]
    assert len(normalize_orders(raw)) == 1
```

## 5. Documentação com mkdocs-material

- Escreva a doc em `docs/` com mkdocs-material e gere a referência da API com mkdocstrings.
- Escreva docstrings no **padrão Google** em todos os módulos, classes e funções públicos.
- Mantenha o README curto: o que é, como instalar (`poetry install`), como rodar, como testar e o link para a doc.
- Comandos: `poetry run mkdocs serve` e `poetry run mkdocs build --strict`.

```yaml
# mkdocs.yml
site_name: nome-projeto
theme:
  name: material
  language: pt-BR
plugins:
  - search
  - mkdocstrings:
      handlers:
        python:
          paths: [src]
          options:
            docstring_style: google
            show_source: false
nav:
  - Início: index.md
  - Guia de uso: guia.md
  - Arquitetura: arquitetura.md
  - Referência da API: api.md
```
```markdown
<!-- docs/api.md -->
# Referência da API

::: nome_projeto
```

## 6. Boas práticas Python

- **Type hints** são obrigatórios em funções públicas. Verifique com `poetry run mypy src`.
- Use `logging`, **nunca** `print`, com um logger por módulo: `logger = logging.getLogger(__name__)`.
  Passe contexto em `extra={...}` em vez de concatenar na mensagem.
- Trate exceções de forma explícita. **Nunca** use `except:` nu nem `except Exception: pass`.
  Capture a exceção específica, registre o erro e propague ou converta para uma exceção do domínio.
- Use `pathlib` (não `os.path`), f-strings, `dataclasses`/`pydantic` para estruturas e context managers para recursos.
- Garanta **idempotência**: reprocessar a mesma partição/data gera o mesmo resultado, sem
  duplicar dados (sobrescreva a partição, use chaves determinísticas, faça upsert).
- Commits pequenos, com Conventional Commits (`feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`).

```python
# src/nome_projeto/clients/api.py
class ExtractionError(Exception):
    """Falha ao extrair dados da fonte."""


def fetch_orders(self, ref_date: str) -> list[dict[str, object]]:
    try:
        response = self._session.get(
            f"{self._base_url}/orders", params={"date": ref_date}, timeout=30
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        logger.exception("falha na API de pedidos", extra={"ref_date": ref_date})
        raise ExtractionError(f"Falha ao extrair pedidos de {ref_date}") from exc
    return response.json()["data"]
```

```gitignore
# .gitignore
.venv/
__pycache__/
*.pyc
.coverage
htmlcov/
.pytest_cache/
.mypy_cache/
.ruff_cache/
site/
build/
dist/
.env
```

## 7. Exemplo completo de `pyproject.toml`

```toml
[project]
name = "nome-projeto"
version = "0.1.0"
description = "Extrator de pedidos para o data lake."
readme = "README.md"
requires-python = ">=3.12,<3.13"
dependencies = [
    "boto3 (>=1.35,<2.0)",
    "pydantic-settings (>=2.6,<3.0)",
    "requests (>=2.32,<3.0)",
]

[build-system]
requires = ["poetry-core>=2.0.0,<3.0.0"]
build-backend = "poetry.core.masonry.api"

[tool.poetry]
packages = [{ include = "nome_projeto", from = "src" }]

[tool.poetry.group.dev.dependencies]
ruff = "^0.8"
pytest = "^8.3"
pytest-cov = "^6.0"
pytest-mock = "^3.14"
moto = { version = "^5.0", extras = ["s3", "secretsmanager"] }
mypy = "^1.13"
pre-commit = "^4.0"

[tool.poetry.group.docs.dependencies]
mkdocs-material = "^9.5"
mkdocstrings = { version = "^0.27", extras = ["python"] }

[tool.ruff]
line-length = 100
target-version = "py312"
src = ["src", "tests"]

[tool.ruff.lint]
select = ["E", "W", "F", "I", "B", "UP", "SIM", "N", "C4", "PL", "RUF", "S"]

[tool.ruff.lint.per-file-ignores]
"tests/**/*.py" = [
    "S101",    # assert é o idioma do pytest
    "PLR2004", # valores mágicos são esperados em asserts
    "S105",    # senhas fake em fixtures
    "S106",    # senhas fake em fixtures
]

[tool.ruff.lint.isort]
known-first-party = ["nome_projeto"]

[tool.ruff.format]
quote-style = "double"

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "--cov=src/nome_projeto --cov-report=term-missing --cov-fail-under=50"

[tool.coverage.run]
source = ["src/nome_projeto"]
branch = true
omit = ["*/__init__.py"]

[tool.coverage.report]
show_missing = true
skip_empty = true

[tool.mypy]
python_version = "3.12"
mypy_path = "src"
strict = true
warn_unused_ignores = true
plugins = ["pydantic.mypy"]

[[tool.mypy.overrides]]
module = ["boto3.*", "botocore.*", "moto.*"]
ignore_missing_imports = true
```

## 8. Comandos de qualidade e Makefile

Rode nesta ordem antes de entregar:
```bash
poetry install
poetry run ruff check . --fix
poetry run ruff format .
poetry run mypy src
poetry run pytest
poetry run mkdocs build --strict
```

```makefile
# Makefile — só chama `poetry run ...`
.PHONY: install lint format typecheck test docs check

install:
	poetry install

lint:
	poetry run ruff check .
	poetry run ruff format --check .

format:
	poetry run ruff check . --fix
	poetry run ruff format .

typecheck:
	poetry run mypy src

test:
	poetry run pytest

docs:
	poetry run mkdocs build --strict

check: lint typecheck test docs
```

## 9. Faça / Não faça

| Não faça | Faça |
|---|---|
| `pip install requests` | `poetry add requests` |
| `pip install pytest` | `poetry add --group dev pytest` |
| `requirements.txt` à mão | `poetry export -f requirements.txt --only main` |
| Código na raiz ou em `nome_projeto/` | Código em `src/nome_projeto/` |
| Lógica de negócio no `handler` | Lógica em módulo testável, chamada pelo handler |
| `print(...)` | `logger.info(...)` |
| `except: pass` / `except Exception: pass` | `except ErroEspecifico as exc: ... raise DominioError(...) from exc` |
| `os.path.join(a, b)` | `Path(a) / b` |
| `os.environ["X"]` espalhado pelo código | `get_settings().x` em `config/` |
| Senha/token no código ou no `.env` versionado | Secrets Manager / SSM |
| `from modulo import *` | Import absoluto e explícito |
| black + isort + flake8 | Ruff |
| Teste que chama S3/API real | `moto` / `pytest-mock` |
| `INSERT` cego no reprocessamento | Sobrescrever partição / upsert idempotente |

## 10. Fluxo para criar um projeto novo do zero

```bash
# 1. Criar o projeto (layout src/) e a venv local
poetry new nome-projeto && cd nome-projeto
poetry config virtualenvs.in-project true --local

# 2. Fixar o Python do runtime da Lambda
#    -> editar requires-python = ">=3.12,<3.13" no pyproject.toml
poetry env use python3.12

# 3. Dependências por grupo
poetry add boto3 pydantic-settings
poetry add --group dev ruff pytest pytest-cov pytest-mock "moto[s3,secretsmanager]" mypy pre-commit
poetry add --group docs mkdocs-material "mkdocstrings[python]"

# 4. Estrutura
mkdir -p src/nome_projeto/{config,clients,extract,transform,load,utils} tests/unit docs
touch src/nome_projeto/{config,clients,extract,transform,load,utils}/__init__.py tests/conftest.py

# 5. Configurar ruff/pytest/coverage/mypy no pyproject.toml (seção 7),
#    mkdocs.yml (seção 5), .pre-commit-config.yaml (seção 3), .gitignore e Makefile

# 6. Hooks e validação
poetry run pre-commit install
make format check

# 7. Versionar (incluindo poetry.lock)
git add . && git commit -m "chore: estrutura inicial do projeto"
```

## Checklist antes de entregar

Confira cada item antes de concluir **qualquer** tarefa. Se algum item falhar, corrija
ou informe explicitamente ao usuário o que ficou pendente e por quê.

- [ ] Nenhum uso de pip; dependência adicionada via `poetry add` no grupo certo e `poetry.lock` atualizado
- [ ] Código dentro de `src/<pacote>/`, modular e sem lógica no entrypoint
- [ ] I/O isolado em clientes mockáveis; config lida só em `config/`
- [ ] `ruff check` e `ruff format --check` passando (imports organizados)
- [ ] Type hints + `mypy src` sem erros
- [ ] Testes unitários escritos (e de regressão para bug); sem acesso a rede/AWS reais; cobertura ≥ 50%
- [ ] `logging` em vez de `print`; nenhum `except` nu ou silencioso
- [ ] Pipeline idempotente (reprocessamento seguro)
- [ ] Docstrings Google e doc atualizada; `mkdocs build --strict` passando
- [ ] Sem segredos ou credenciais no código
