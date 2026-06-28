-- Election registry. PAST entries link to a term_cycle (eci_election_id) whose winners we hold in full;
-- UPCOMING entries are EXPECTED dates derived from fixed 5-year terms (not yet notified by ECI).
INSERT INTO election (eci_election_id, name, level, house_code, election_date, status, seats, note) VALUES
    -- Past — full winner results available.
    ('LS2024',     'General Election 2024 (18th Lok Sabha)', 'national',  'LS',     DATE '2024-06-04', 'past', 543, NULL),
    ('MH_VS2024',  'Maharashtra Assembly Election 2024',     'state',     'MH_VS',  DATE '2024-11-23', 'past', 288, NULL),
    ('DL_MCD2022', 'Delhi Municipal Election 2022',          'municipal', 'DL_MCD', DATE '2022-12-07', 'past', 250, NULL),
    -- Upcoming — EXPECTED (term-based; not yet notified by ECI).
    ('DL_MCD2027', 'Delhi Municipal Election',               'municipal', NULL,     DATE '2027-12-01', 'upcoming', 250, 'Expected — not yet notified by ECI'),
    ('UP_VS2027',  'Uttar Pradesh Assembly Election',        'state',     NULL,     DATE '2027-03-01', 'upcoming', 403, 'Expected — not yet notified by ECI'),
    ('GJ_VS2027',  'Gujarat Assembly Election',              'state',     NULL,     DATE '2027-12-01', 'upcoming', 182, 'Expected — not yet notified by ECI'),
    ('MH_VS2029',  'Maharashtra Assembly Election',          'state',     NULL,     DATE '2029-11-01', 'upcoming', 288, 'Expected — not yet notified by ECI'),
    ('LS2029',     'General Election (19th Lok Sabha)',      'national',  NULL,     DATE '2029-05-01', 'upcoming', 543, 'Expected — not yet notified by ECI')
ON CONFLICT (eci_election_id) DO NOTHING;
