-- 0007: IPC/BNS section catalog + criminal cases + charges (with derived severity)

-- Catalog of legal sections + IPC↔BNS crosswalk. base_severity is the rule input (see docs/severity-rubric.md).
CREATE TABLE legal_section (
    id                    bigserial PRIMARY KEY,
    code_system           text NOT NULL CHECK (code_system IN ('IPC','BNS')),
    section_number        text NOT NULL,             -- '302'
    title                 text,                      -- 'Murder'
    ipc_equivalent        text,                      -- BNS→IPC crosswalk
    bns_equivalent        text,                      -- IPC→BNS crosswalk
    base_severity         text CHECK (base_severity IN ('heinous','serious','minor')),
    is_cognizable         boolean,
    max_punishment_years  int,
    UNIQUE (code_system, section_number)
);

-- A criminal case declared in an affidavit and/or tracked via courts.
CREATE TABLE criminal_case (
    id                     bigserial PRIMARY KEY,
    person_id              bigint NOT NULL REFERENCES person(id),
    affidavit_id           bigint REFERENCES affidavit(id),    -- declared at this filing
    source_ref_id          bigint NOT NULL REFERENCES source_ref(id),
    case_number            text,
    court                  text,
    filed_year             int,
    status                 text NOT NULL DEFAULT 'pending'
                             CHECK (status IN ('pending','convicted','acquitted','framed_charges')),
    is_convicted           boolean NOT NULL DEFAULT false,
    severity               text CHECK (severity IN ('heinous','serious','minor')),  -- DERIVED (max over charges)
    severity_rule_version  text,                       -- which rubric produced it (auditability)
    description            text,
    cnr_number             text,                       -- eCourts CNR for court enrichment linkage
    court_source_ref_id    bigint REFERENCES source_ref(id)  -- live status from bharat-courts/ecourts
);

CREATE INDEX criminal_case_person_idx ON criminal_case (person_id);

-- The IPC/BNS sections charged on a case (many per case).
CREATE TABLE case_charge (
    id                bigserial PRIMARY KEY,
    criminal_case_id  bigint NOT NULL REFERENCES criminal_case(id) ON DELETE CASCADE,
    section_id        bigint REFERENCES legal_section(id),
    raw_section_text  text NOT NULL                  -- as scraped ('IPC 302','BNS 103')
);

CREATE INDEX case_charge_case_idx ON case_charge (criminal_case_id);
