-- Starter party registry (major national/large-state parties). Extend from sansad/ECI roster.
INSERT INTO party (canonical_name, abbr, eci_party_id) VALUES
    ('Bharatiya Janata Party',            'BJP',  NULL),
    ('Indian National Congress',          'INC',  NULL),
    ('Aam Aadmi Party',                   'AAP',  NULL),
    ('All India Trinamool Congress',      'AITC', NULL),
    ('Dravida Munnetra Kazhagam',         'DMK',  NULL),
    ('Telugu Desam Party',                'TDP',  NULL),
    ('Janata Dal (United)',               'JDU',  NULL),
    ('Nationalist Congress Party',        'NCP',  NULL),
    ('Shiv Sena',                         'SS',   NULL),
    ('Samajwadi Party',                   'SP',   NULL),
    ('Independent',                       'IND',  NULL)
ON CONFLICT DO NOTHING;

-- Common aliases / spellings → canonical party. Critical for entity-resolution + switch detection.
INSERT INTO party_alias (party_id, alias, source)
SELECT p.id, v.alias, 'seed'
FROM (VALUES
    ('BJP',  'Bharatiya Janata Party'),
    ('BJP',  'BJP'),
    ('INC',  'Congress'),
    ('INC',  'Indian National Congress'),
    ('AITC', 'TMC'),
    ('AITC', 'Trinamool Congress'),
    ('JDU',  'JD(U)'),
    ('NCP',  'Nationalist Congress Party'),
    ('IND',  'Independent')
) AS v(abbr, alias)
JOIN party p ON p.abbr = v.abbr
ON CONFLICT (party_id, alias) DO NOTHING;
