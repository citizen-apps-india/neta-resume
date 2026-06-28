-- Houses for v1 (Parliament). State assemblies are added incrementally with no schema change —
-- jurisdiction='state' + a state_code (ISO 3166-2:IN). Maharashtra Vidhan Sabha is the first.
INSERT INTO house (code, name, jurisdiction, state_code) VALUES
    ('LS',     'Lok Sabha',                'union',     NULL),
    ('RS',     'Rajya Sabha',              'union',     NULL),
    ('MH_VS',  'Maharashtra Vidhan Sabha', 'state',     'MH'),
    ('DL_MCD', 'Delhi MCD',                'municipal', 'DL')
ON CONFLICT (code) DO NOTHING;

-- Current cycles (extend as needed). The Rajya Sabha is a continuous house with staggered terms,
-- so we model the current sitting cohort as a single cycle; actual term dates live on office_term.
INSERT INTO term_cycle (house_id, number, start_date, end_date, eci_election_id)
SELECT h.id, v.number, v.start_date, v.end_date, v.eci_election_id
FROM (VALUES
    ('LS', 18, DATE '2024-06-24', NULL,              'LS2024'),
    ('LS', 17, DATE '2019-06-17', DATE '2024-06-23', 'LS2019'),
    ('LS', 16, DATE '2014-05-26', DATE '2019-06-16', 'LS2014'),
    ('LS', 15, DATE '2009-05-22', DATE '2014-05-25', 'LS2009'),
    ('RS',  1, NULL,             NULL,                'RS-CURRENT'),
    -- 15th Maharashtra Vidhan Sabha — elected Nov 2024.
    ('MH_VS', 15, DATE '2024-11-23', NULL,            'MH_VS2024'),
    -- Municipal Corporation of Delhi — elected Dec 2022.
    ('DL_MCD', 1, DATE '2022-12-07', NULL,            'DL_MCD2022')
) AS v(house_code, number, start_date, end_date, eci_election_id)
JOIN house h ON h.code = v.house_code
ON CONFLICT (house_id, number) DO NOTHING;
