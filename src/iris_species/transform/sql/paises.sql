-- analytics.paises: uma linha por espécie e país onde ela foi registrada.
-- As ocorrências (GBIF) ganham o nome científico (GBIF) e a média do comprimento da
-- pétala das flores medidas (Kaggle) pelo JOIN na espécie.
SELECT
    o.especie,
    e.nome_cientifico,
    o.pais_codigo,
    o.pais,
    count(*) AS quantidade_ocorrencias,
    min(o.ano) AS primeiro_ano,
    max(o.ano) AS ultimo_ano,
    a.media_comprimento_petala_cm
FROM refined.ocorrencias AS o
JOIN refined.especies AS e ON e.especie = o.especie
JOIN analytics.especies AS a ON a.especie = o.especie
GROUP BY o.especie, e.nome_cientifico, o.pais_codigo, o.pais, a.media_comprimento_petala_cm
ORDER BY o.especie, quantidade_ocorrencias DESC, o.pais_codigo
