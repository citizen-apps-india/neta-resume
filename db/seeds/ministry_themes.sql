-- Ministry -> policy-theme map for the "Policy focus" breakdown (idempotent).
-- Keys are LOWERCASED ministry names (matches lower(trim(parliamentary_question.ministry))). Themes are a
-- deliberately small, editable set of policy domains. Grouping ministries into themes is inherently
-- editorial — kept here (versionable) rather than in app code, and surfaced in the UI as "derived from the
-- official ministry each question addresses". Unmapped ministries render as "Other" at read time.
--
-- Themes: Economy & Industry | Health | Education & Skills | Social Welfare & Justice |
--         Agriculture & Environment | Infrastructure & Connectivity | Governance & External

INSERT INTO ministry_theme (ministry_key, theme) VALUES
    -- Economy & Industry
    ('finance', 'Economy & Industry'),
    ('chemicals and fertilizers', 'Economy & Industry'),
    ('corporate affairs', 'Economy & Industry'),
    ('commerce and industry', 'Economy & Industry'),
    ('micro, small and medium enterprises', 'Economy & Industry'),
    ('heavy industries', 'Economy & Industry'),
    ('heavy industries and public enterprises', 'Economy & Industry'),
    ('steel', 'Economy & Industry'),
    ('coal', 'Economy & Industry'),
    ('mines', 'Economy & Industry'),
    ('petroleum and natural gas', 'Economy & Industry'),
    ('power', 'Economy & Industry'),
    ('new and renewable energy', 'Economy & Industry'),
    ('textiles', 'Economy & Industry'),
    ('food processing industries', 'Economy & Industry'),
    ('consumer affairs, food and public distribution', 'Economy & Industry'),
    ('cooperation', 'Economy & Industry'),
    ('planning', 'Economy & Industry'),
    ('statistics and programme implementation', 'Economy & Industry'),
    -- Health
    ('health and family welfare', 'Health'),
    ('ayush', 'Health'),
    -- Education & Skills
    ('education', 'Education & Skills'),
    ('skill development and entrepreneurship', 'Education & Skills'),
    ('youth affairs and sports', 'Education & Skills'),
    ('science and technology', 'Education & Skills'),
    -- Social Welfare & Justice
    ('women and child development', 'Social Welfare & Justice'),
    ('social justice and empowerment', 'Social Welfare & Justice'),
    ('tribal affairs', 'Social Welfare & Justice'),
    ('minority affairs', 'Social Welfare & Justice'),
    ('labour and employment', 'Social Welfare & Justice'),
    ('rural development', 'Social Welfare & Justice'),
    ('panchayati raj', 'Social Welfare & Justice'),
    -- Agriculture & Environment
    ('agriculture and farmers welfare', 'Agriculture & Environment'),
    ('environment, forest and climate change', 'Agriculture & Environment'),
    ('jal shakti', 'Agriculture & Environment'),
    ('fisheries, animal husbandry and dairying', 'Agriculture & Environment'),
    ('earth sciences', 'Agriculture & Environment'),
    -- Infrastructure & Connectivity
    ('railways', 'Infrastructure & Connectivity'),
    ('civil aviation', 'Infrastructure & Connectivity'),
    ('road transport and highways', 'Infrastructure & Connectivity'),
    ('ports, shipping and waterways', 'Infrastructure & Connectivity'),
    ('housing and urban affairs', 'Infrastructure & Connectivity'),
    ('communications', 'Infrastructure & Connectivity'),
    ('communication', 'Infrastructure & Connectivity'),
    ('electronics and information technology', 'Infrastructure & Connectivity'),
    -- Governance & External
    ('home affairs', 'Governance & External'),
    ('defence', 'Governance & External'),
    ('external affairs', 'Governance & External'),
    ('law and justice', 'Governance & External'),
    ('prime minister', 'Governance & External'),
    ('development of north eastern region', 'Governance & External'),
    ('culture', 'Governance & External'),
    ('tourism', 'Governance & External'),
    ('information and broadcasting', 'Governance & External'),
    ('parliamentary affairs', 'Governance & External'),
    ('personnel, public grievances and pensions', 'Governance & External')
ON CONFLICT (ministry_key) DO UPDATE SET theme = EXCLUDED.theme;
