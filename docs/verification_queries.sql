SELECT COUNT(*) AS stored_rows, COUNT(DISTINCT model_id) AS unique_model_ids
FROM models;

SELECT COUNT(*) AS invalid_required_rows
FROM models
WHERE model_id IS NULL OR name IS NULL OR provider IS NULL
   OR created_at IS NULL OR context_length <= 0;

SELECT provider, COUNT(*) AS model_count,
       ROUND(AVG(context_length), 0) AS mean_context_length
FROM models
GROUP BY provider
ORDER BY model_count DESC
LIMIT 10;

SELECT price_band, COUNT(*) AS model_count
FROM models
GROUP BY price_band
ORDER BY model_count DESC;
