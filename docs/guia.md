# Guia de uso

Rode todos os comandos a partir da raiz do projeto.

## Instalar

```bash
poetry install
```

## Rodar o pipeline

```bash
poetry run python -m iris_species.extracao       # raw/Iris.csv
poetry run python -m iris_species.ingestao       # raw.flores
poetry run python -m iris_species.transformacao  # refined.flores e analytics.especies
```

Ou, de uma vez: `make pipeline`.

Saída esperada:

```
/caminho/do/projeto/raw/Iris.csv  5.107 bytes
raw.flores                      150
total                           150
refined.flores                  150
analytics.especies                3
total                           153
```

## Consultar no navegador

```bash
poetry run python -m iris_species.ui
```

Abre http://localhost:4213. Encerre com Ctrl+C **antes** de rodar a ingestão ou a
transformação de novo: o `iris.duckdb` aceita um único processo escrevendo.

Na primeira execução, a extensão `ui` do DuckDB é baixada da internet.

## Erros comuns

| Mensagem | O que fazer |
|---|---|
| `falha ao baixar Iris.csv` | Verifique a rede. Se o erro for de credencial, configure `~/.kaggle/kaggle.json` ou `KAGGLE_API_TOKEN`. |
| `arquivo ausente: Iris.csv` | Rode a extração antes da ingestão. |
| `raw.flores não encontrada` | Rode a ingestão antes da transformação. |
| `Could not set lock on file` | Feche a UI (Ctrl+C) e rode de novo. |
