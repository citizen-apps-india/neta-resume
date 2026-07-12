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
    ('worldbank',     'World Bank Open Data',               'https://data.worldbank.org/',        'CC-BY-4.0',       1)
ON CONFLICT (code) DO NOTHING;
