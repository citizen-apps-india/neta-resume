-- 0006: ECI affidavit wealth (assets/liabilities/income), year-over-year via filed_year

-- All amounts are integer RUPEES (parse ₹ lakh/crore upstream in transform/money.py).
CREATE TABLE affidavit (
    id                 bigserial PRIMARY KEY,
    person_id          bigint NOT NULL REFERENCES person(id),
    source_ref_id      bigint NOT NULL REFERENCES source_ref(id),  -- the MyNeta candidate-page partition
    election_cycle     text NOT NULL,               -- 'LS2024','RS2022-Karnataka' (drives YoY)
    house_id           smallint NOT NULL REFERENCES house(id),
    filed_year         int NOT NULL,
    age                int,
    education          text,
    total_assets       bigint NOT NULL DEFAULT 0,
    total_liabilities  bigint NOT NULL DEFAULT 0,
    movable_assets     bigint,
    immovable_assets   bigint,
    self_income        bigint,                       -- declared income (ITR fields where present)
    income_year        int,
    pan_given          boolean,
    raw_url            text,                          -- direct affidavit page link (shown in UI)
    UNIQUE (person_id, election_cycle, source_ref_id)
);

CREATE INDEX affidavit_person_idx ON affidavit (person_id);

-- Optional granular breakdown (cash, jewellery, land, liability, income).
CREATE TABLE affidavit_line_item (
    id            bigserial PRIMARY KEY,
    affidavit_id  bigint NOT NULL REFERENCES affidavit(id) ON DELETE CASCADE,
    category      text NOT NULL,                     -- 'asset_movable','asset_immovable','liability','income'
    label         text,
    amount        bigint NOT NULL DEFAULT 0,
    owner         text                               -- 'self','spouse','dependent'
);

CREATE INDEX affidavit_line_item_aff_idx ON affidavit_line_item (affidavit_id);
