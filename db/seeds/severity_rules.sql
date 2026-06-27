-- Severity rule, expressed as data. Re-derives legal_section.base_severity from punishment/cognizability.
-- Run AFTER ipc_bns_sections.sql if you want the rule (not the hand-set values) to win.
-- Rule version: 'adr-v1' (mirror docs/severity-rubric.md). Bump the version when the rubric changes.
--
-- Tiering (ADR "serious criminal" rubric, extended to 3 tiers):
--   heinous : max_punishment_years >= 10  OR life/death (encoded as 99)
--   serious : max_punishment_years >= 5   OR non-bailable corruption/electoral (curated)
--   minor   : everything else
--
-- NOTE: heinous-by-category offences against women etc. are hand-set in ipc_bns_sections.sql and should
-- NOT be downgraded by this numeric rule — hence the GREATEST() guard via CASE below only UPGRADES.

UPDATE legal_section
SET base_severity = CASE
        WHEN base_severity = 'heinous' THEN 'heinous'              -- never downgrade curated heinous
        WHEN max_punishment_years >= 10 THEN 'heinous'
        WHEN max_punishment_years >= 5  THEN 'serious'
        WHEN base_severity = 'serious'  THEN 'serious'             -- keep curated serious (e.g. corruption)
        ELSE 'minor'
    END
WHERE max_punishment_years IS NOT NULL;
