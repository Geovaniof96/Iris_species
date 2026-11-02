-- analytics.panorama: uma linha por espécie, juntando as duas fontes.
--   refined.especies    taxonomia (GBIF)
--   analytics.especies  medidas das 150 flores (Kaggle)
--   refined.ocorrencias registros no mundo (GBIF), agregados por espécie
-- LEFT JOIN nas ocorrências: espécie sem ocorrência aparece com contagens nulas.
WITH ocorrencias AS (
    SELECT
        especie,
        count(*) AS quantidade_ocorrencias,
        count(DISTINCT pais_codigo) AS quantidade_paises,
        min(ano) AS primeiro_ano,
        max(ano) AS ultimo_ano,
        avg(latitude) AS latitude_media
    FROM refined.ocorrencias
    GROUP BY especie
),
pais_principal AS (
    SELECT especie, pais AS pais_mais_frequente
    FROM refined.ocorrencias
    WHERE pais IS NOT NULL
    GROUP BY especie, pais
    QUALIFY row_number() OVER (PARTITION BY especie ORDER BY count(*) DESC, pais) = 1
)
SELECT
    e.especie,
    e.nome_cientifico,
    e.familia,
    e.gbif_codigo,
    a.quantidade AS quantidade_flores,
    a.media_comprimento_sepala_cm,
    a.media_largura_sepala_cm,
    a.media_comprimento_petala_cm,
    a.media_largura_petala_cm,
    o.quantidade_ocorrencias,
    o.quantidade_paises,
    p.pais_mais_frequente,
    o.primeiro_ano,
    o.ultimo_ano,
    o.latitude_media
FROM refined.especies AS e
JOIN analytics.especies AS a USING (especie)
LEFT JOIN ocorrencias AS o USING (especie)
LEFT JOIN pais_principal AS p USING (especie)
ORDER BY e.especie
