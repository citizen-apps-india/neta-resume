-- Data SOURCE registry. trust_tier: 1 official, 2 ADR/TCPD, 3 reported/news.
INSERT INTO source (code, name, base_url, license, trust_tier) VALUES
    ('sansad',        'Digital Sansad (LS/RS)',            'https://sansad.in/',                 'public-official', 1),
    ('eci',           'Election Commission of India',       'https://affidavit.eci.gov.in/',      'public-official', 1),
    ('myneta',        'MyNeta / ADR',                       'https://www.myneta.info/',           'non-commercial',  2),
    ('tcpd_surf',     'TCPD SURF / LokDhaba (Ashoka)',      'https://tcpd.ashoka.edu.in/',        'academic',        2),
    ('bharat_courts', 'bharat-courts / eCourts',            'https://services.ecourts.gov.in/',   'public-official', 1),
    ('datagovin',     'data.gov.in (OGD)',                  'https://www.data.gov.in/',           'GODL-India',      1),
    ('prs',           'PRS Legislative Research',           'https://prsindia.org/',              'non-commercial',  2),
    ('wikidata',      'Wikidata',                           'https://www.wikidata.org/',          'CC0',             3),
    ('news',          'News / reported',                    NULL,                                  'reported',        3),
    ('govt',          'Government of India (official portals)', 'https://www.india.gov.in/',       'public-official', 1),
    ('worldbank',     'World Bank Open Data',               'https://data.worldbank.org/',        'CC-BY-4.0',       1),
    -- India Dashboard institutional counts (added 0029): official ministry / agency statistics, trust tier 1.
    ('moe_udise',     'UDISE+ (Ministry of Education)',     'https://udiseplus.gov.in/',          'public-official', 1),
    ('moe_aishe',     'AISHE (Ministry of Education)',      'https://aishe.gov.in/',              'public-official', 1),
    ('mohfw_hdi',     'Health Dynamics of India (MoHFW)',   'https://mohfw.gov.in/',              'public-official', 1),
    ('ncrb',          'National Crime Records Bureau',      'https://www.ncrb.gov.in/',           'public-official', 1),
    ('bprd',          'Bureau of Police Research & Development', 'https://bprd.nic.in/',           'public-official', 1),
    ('indiapost',     'Department of Posts (India Post)',   'https://www.indiapost.gov.in/',      'public-official', 1),
    ('rbi',           'Reserve Bank of India',              'https://www.rbi.org.in/',            'public-official', 1),
    ('indianrail',    'Indian Railways',                    'https://indianrailways.gov.in/',     'public-official', 1)
ON CONFLICT (code) DO NOTHING;
