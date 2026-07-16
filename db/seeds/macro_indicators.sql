-- India Dashboard indicator catalog (idempotent). Which macro series we show, grouped + ordered.
-- Codes are World Bank Open Data series codes (v1 source; keyless API, CC-BY 4.0) — every code here was
-- smoke-tested to return India data. Names are the source's official series names (descriptive, not ours).
-- Notes: CO2 uses the current EN.GHG.* code (legacy EN.ATM.CO2E.PC was retired by the World Bank);
-- central-govt debt (GC.DOD.TOTL.GD.ZS) was considered and dropped — its latest India value is 2018.
-- Sparse series (Gini, poverty — survey years only) are fine: the UI charts actual points and always
-- labels the year a value is "as of".
-- polarity (added 0029): +1 higher-is-better, -1 lower-is-better, 0 neutral — drives the colour of the
-- YoY change chip so a fall in inflation reads green, not red.

INSERT INTO macro_indicator_def (code, name, unit, format, category, category_order, ind_order, polarity) VALUES
    -- Economy & Growth
    ('NY.GDP.MKTP.CD',       'GDP (current US$)',                                          'US$',                    'usd_compact',   'Economy & Growth',       1, 1,  1),
    ('NY.GDP.MKTP.KD.ZG',    'GDP growth (annual %)',                                      '%',                      'pct',           'Economy & Growth',       1, 2,  1),
    ('NY.GDP.PCAP.CD',       'GDP per capita (current US$)',                               'US$',                    'usd_compact',   'Economy & Growth',       1, 3,  1),
    ('FI.RES.TOTL.CD',       'Total reserves (includes gold, current US$)',                'US$',                    'usd_compact',   'Economy & Growth',       1, 4,  1),
    ('GC.TAX.TOTL.GD.ZS',    'Tax revenue (% of GDP)',                                     '% of GDP',               'pct',           'Economy & Growth',       1, 5,  0),
    -- Prices
    ('FP.CPI.TOTL.ZG',       'Inflation, consumer prices (annual %)',                      '%',                      'pct',           'Prices',                 2, 1, -1),
    -- Work
    ('SL.UEM.TOTL.ZS',       'Unemployment (% of labor force, modeled ILO estimate)',      '% of labour force',      'pct',           'Work',                   3, 1, -1),
    ('SL.TLF.CACT.ZS',       'Labor force participation rate (% of population 15+)',       '% of population 15+',    'pct',           'Work',                   3, 2,  1),
    -- Poverty & Inequality
    ('SI.POV.DDAY',          'Poverty headcount at $3.00 a day, 2021 PPP (% of population)', '% of population',      'pct',           'Poverty & Inequality',   4, 1, -1),
    ('SI.POV.GINI',          'Gini index',                                                 'index (0–100)',          'number',        'Poverty & Inequality',   4, 2, -1),
    -- Health
    ('SP.DYN.LE00.IN',       'Life expectancy at birth (years)',                           'years',                  'number',        'Health',                 5, 1,  1),
    ('SP.DYN.IMRT.IN',       'Infant mortality (per 1,000 live births)',                   'per 1,000 live births',  'number',        'Health',                 5, 2, -1),
    ('SH.STA.MMRT',          'Maternal mortality ratio (per 100,000 live births)',         'per 100,000 live births','number',        'Health',                 5, 3, -1),
    ('SH.XPD.CHEX.GD.ZS',    'Current health expenditure (% of GDP)',                      '% of GDP',               'pct',           'Health',                 5, 4,  1),
    -- Education
    ('SE.ADT.LITR.ZS',       'Adult literacy rate (% of people ages 15+)',                 '% of ages 15+',          'pct',           'Education',              6, 1,  1),
    ('SE.PRM.ENRR',          'School enrollment, primary (% gross)',                       '% gross',                'pct',           'Education',              6, 2,  1),
    ('SE.XPD.TOTL.GD.ZS',    'Government expenditure on education (% of GDP)',             '% of GDP',               'pct',           'Education',              6, 3,  1),
    -- Infrastructure & Access
    ('EG.ELC.ACCS.ZS',       'Access to electricity (% of population)',                    '% of population',        'pct',           'Infrastructure & Access',7, 1,  1),
    ('IT.NET.USER.ZS',       'Individuals using the Internet (% of population)',           '% of population',        'pct',           'Infrastructure & Access',7, 2,  1),
    -- People
    ('SP.POP.TOTL',          'Population, total',                                          'people',                 'count_compact', 'People',                 8, 1,  0),
    ('SP.URB.TOTL.IN.ZS',    'Urban population (% of total)',                              '% of population',        'pct',           'People',                 8, 2,  0),
    ('SP.DYN.TFRT.IN',       'Fertility rate (births per woman)',                          'births per woman',       'number',        'People',                 8, 3,  0),
    -- Environment
    ('EN.GHG.CO2.PC.CE.AR5', 'CO2 emissions per capita, excluding LULUCF (tonnes)',        't CO2 / person',         'number',        'Environment',            9, 1, -1),
    ('AG.LND.FRST.ZS',       'Forest area (% of land area)',                               '% of land area',         'pct',           'Environment',            9, 2,  1)
ON CONFLICT (code) DO UPDATE SET
    name = EXCLUDED.name, unit = EXCLUDED.unit, format = EXCLUDED.format,
    category = EXCLUDED.category, category_order = EXCLUDED.category_order, ind_order = EXCLUDED.ind_order,
    polarity = EXCLUDED.polarity;
