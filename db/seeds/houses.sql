-- Houses for v1 (Parliament). State assemblies are added later with no schema change.
INSERT INTO house (code, name, jurisdiction, state_code) VALUES
    ('LS', 'Lok Sabha',   'union', NULL),
    ('RS', 'Rajya Sabha', 'union', NULL)
ON CONFLICT (code) DO NOTHING;

-- Current cycles (extend as needed). The Rajya Sabha is a continuous house with staggered terms,
-- so we model the current sitting cohort as a single cycle; actual term dates live on office_term.
INSERT INTO term_cycle (house_id, number, start_date, end_date, eci_election_id)
SELECT h.id, v.number, v.start_date, v.end_date, v.eci_election_id
FROM (VALUES
    ('LS', 18, DATE '2024-06-24', NULL,              'LS2024'),
    ('LS', 17, DATE '2019-06-17', DATE '2024-06-23', 'LS2019'),
    ('RS',  1, NULL,             NULL,                'RS-CURRENT')
) AS v(house_code, number, start_date, end_date, eci_election_id)
JOIN house h ON h.code = v.house_code
ON CONFLICT (house_id, number) DO NOTHING;
