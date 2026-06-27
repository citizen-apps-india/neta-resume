-- Starter IPC/BNS section catalog with severity + IPC↔BNS crosswalk.
-- base_severity follows docs/severity-rubric.md (ADR "serious crime" = max punishment >= 5y, plus
-- a curated heinous list). This is a SEED, not exhaustive — extend as cases surface new sections.
-- See db/seeds/severity_rules.sql for the rule that can re-derive base_severity in bulk.

INSERT INTO legal_section
    (code_system, section_number, title, ipc_equivalent, bns_equivalent, base_severity, is_cognizable, max_punishment_years)
VALUES
    -- Heinous (life/death eligible or grave offences against the person)
    ('IPC', '302',  'Murder',                              NULL,  '103', 'heinous', true, 99),
    ('BNS', '103',  'Murder',                              '302', NULL,  'heinous', true, 99),
    ('IPC', '376',  'Rape',                                NULL,  '64',  'heinous', true, 99),
    ('BNS', '64',   'Rape',                                '376', NULL,  'heinous', true, 99),
    ('IPC', '364A', 'Kidnapping for ransom',               NULL,  '140', 'heinous', true, 99),
    ('BNS', '140',  'Kidnapping for ransom',               '364A',NULL,  'heinous', true, 99),
    ('IPC', '307',  'Attempt to murder',                   NULL,  '109', 'heinous', true, 10),
    ('BNS', '109',  'Attempt to murder',                   '307', NULL,  'heinous', true, 10),
    ('IPC', '395',  'Dacoity',                             NULL,  '310', 'heinous', true, 10),

    -- Serious (max punishment >= 5 years / non-bailable / corruption / electoral)
    ('IPC', '304',  'Culpable homicide not amounting to murder', NULL, '105', 'serious', true, 10),
    ('IPC', '308',  'Attempt to commit culpable homicide', NULL,  '110', 'serious', true, 7),
    ('IPC', '326',  'Grievous hurt by dangerous weapons',  NULL,  '118', 'serious', true, 7),
    ('IPC', '420',  'Cheating',                            NULL,  '318', 'serious', true, 7),
    ('IPC', '467',  'Forgery of valuable security',        NULL,  '337', 'serious', true, 99),
    ('IPC', '120B', 'Criminal conspiracy',                 NULL,  '61',  'serious', true, 7),
    ('PCA', '13',   'Criminal misconduct (Prevention of Corruption Act)', NULL, NULL, 'serious', true, 7),

    -- Minor (bailable / < 5 years)
    ('IPC', '147',  'Rioting',                             NULL,  '191', 'minor', true, 2),
    ('IPC', '341',  'Wrongful restraint',                  NULL,  '126', 'minor', false, 1),
    ('IPC', '353',  'Assault to deter public servant',     NULL,  '132', 'minor', true, 2),
    ('IPC', '499',  'Defamation',                          NULL,  '356', 'minor', false, 2),
    ('IPC', '506',  'Criminal intimidation',               NULL,  '351', 'minor', true, 2)
ON CONFLICT (code_system, section_number) DO NOTHING;

-- Common low-grade IPC sections that show up constantly in affidavits + electoral (RPA) offences.
INSERT INTO legal_section
    (code_system, section_number, title, ipc_equivalent, bns_equivalent, base_severity, is_cognizable, max_punishment_years)
VALUES
    ('IPC', '143',  'Member of unlawful assembly',          NULL, '189', 'minor', true, 1),
    ('IPC', '149',  'Unlawful assembly common object',      NULL, '190', 'minor', true, 2),
    ('IPC', '186',  'Obstructing public servant',           NULL, '221', 'minor', false, 1),
    ('IPC', '188',  'Disobedience to order of public servant', NULL, '223', 'minor', true, 1),
    ('IPC', '283',  'Danger/obstruction in public way',     NULL, '285', 'minor', false, 1),
    ('IPC', '294',  'Obscene acts in public',               NULL, '296', 'minor', true, 1),
    ('IPC', '323',  'Voluntarily causing hurt',             NULL, '115', 'minor', false, 1),
    ('IPC', '324',  'Hurt by dangerous weapon',             NULL, '118', 'serious', true, 3),
    ('IPC', '427',  'Mischief causing damage',              NULL, '324', 'minor', true, 2),
    ('IPC', '447',  'Criminal trespass',                    NULL, '329', 'minor', false, 1),
    ('IPC', '448',  'House trespass',                       NULL, '329', 'minor', false, 1),
    ('IPC', '504',  'Intentional insult/breach of peace',   NULL, '352', 'minor', false, 2),
    ('RPA', '125',  'Promoting enmity in connection with election', NULL, NULL, 'serious', true, 3),
    ('RPA', '126',  'Canvassing/disturbance near polling',  NULL, NULL, 'minor', false, 1),
    ('RPA', '127',  'Disturbances at election meetings',    NULL, NULL, 'minor', false, 1),
    ('RPA', '171',  'Corrupt practice (bribery/undue influence)', NULL, NULL, 'serious', true, 1)
ON CONFLICT (code_system, section_number) DO NOTHING;
