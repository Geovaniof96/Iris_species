# Guia de uso

Rode todos os comandos a partir da raiz do projeto.

## Instalar

```bash
poetry install
```

## Rodar o pipeline

```bash
poetry run python -m iris_species.extracao       # raw/Iris.csv (Kaggle)
poetry run python -m iris_species.extracao_gbif  # raw/gbif/ (GBIF, cerca de 1 a 2 minutos)
poetry run python -m iris_species.ingestao       # schema raw
poetry run python -m iris_species.transformacao  # schemas refined e analytics
```

Ou, de uma vez: `make pipeline`.

Saída esperada (as contagens da GBIF podem variar com o tempo):

```
/caminho/do/projeto/raw/Iris.csv  5.107 bytes
/caminho/do/projeto/raw/gbif  3 espécies  9.000 ocorrências  33 arquivos
raw.flores                      150
raw.gbif_especies                 3
raw.gbif_ocorrencias          9.000
total                         9.153
refined.flores                  150
refined.especies                  3
refined.ocorrencias           9.000
analytics.especies                3
analytics.panorama                3
analytics.paises                 25
total                         9.184
```

## Exemplos de JOIN

```sql
-- O panorama pronto: uma linha por espécie, com as duas fontes.
SELECT * FROM analytics.panorama;

-- Cada flor medida, com o nome científico e onde a espécie mais aparece.
SELECT f.id, f.especie, e.nome_cientifico, f.comprimento_petala_cm, p.pais_mais_frequente
FROM refined.flores AS f
JOIN refined.especies AS e USING (especie)
JOIN analytics.panorama AS p USING (especie)
ORDER BY f.id;

-- Ocorrências no Brasil? (JOIN com filtro na outra fonte)
SELECT e.nome_cientifico, count(o.gbif_id) AS ocorrencias
FROM refined.especies AS e
LEFT JOIN refined.ocorrencias AS o ON o.especie = e.especie AND o.pais_codigo = 'BR'
GROUP BY e.nome_cientifico;
```

## Consultar no navegador

```bash
poetry run python -m iris_species.ui
```

Abre http://localhost:4213. Encerre com Ctrl+C **antes** de rodar a ingestão ou a
transformação de novo: o `iris.duckdb` aceita um único processo escrevendo.

## Erros comuns

| Mensagem | O que fazer |
|---|---|
| `falha ao baixar Iris.csv` | Verifique a rede. Se o erro for de credencial, configure `~/.kaggle/kaggle.json` ou `KAGGLE_API_TOKEN`. |
| `falha ao acessar https://api.gbif.org/...` | Verifique a rede e rode `extracao_gbif` de novo. A `raw/gbif` anterior continua intacta. |
| `arquivo ausente: ...` | Rode a extração correspondente antes da ingestão. |
| `tabela da raw não encontrada` | Rode a ingestão antes da transformação. |
| `Could not set lock on file` | Feche a UI (Ctrl+C) e rode de novo. |
