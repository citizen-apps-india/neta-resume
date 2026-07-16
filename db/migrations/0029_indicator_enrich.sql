-- 0029: enrich the India Dashboard indicator catalog with two display hints, so the web can show a
-- good/bad-aware change indicator and a one-line caveat per metric.
--   * polarity — is a RISE in this series good, bad, or neither? Drives the colour of the YoY ▲/▼ chip:
--       +1 higher-is-better (GDP, literacy, life expectancy), -1 lower-is-better (inflation, infant
--       mortality, prison occupancy), 0 neutral/directionless (population, urban share). Default 0.
--   * note — an optional short caveat surfaced under the metric (e.g. the exact report + vintage a curated
--       institutional count was transcribed from, or "govt + aided").
-- Both columns are populated from the seeds (db/seeds/macro_indicators.sql +
-- db/seeds/institution_indicators.sql), which run after migrations — so the values live with the catalog.

ALTER TABLE macro_indicator_def ADD COLUMN polarity smallint NOT NULL DEFAULT 0;
ALTER TABLE macro_indicator_def ADD COLUMN note     text;
