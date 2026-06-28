-- 0014: official contact channels for a legislator (Directory of Indian Politicians — contact module).
-- OFFICIAL channels only (Parliament/Assembly office, official @sansad.in email, official profile,
-- party office) — never personal mobile or residence address. Every row carries its source_ref.

CREATE TABLE IF NOT EXISTS contact (
    id            bigserial PRIMARY KEY,
    person_id     bigint NOT NULL REFERENCES person(id),
    channel_type  text NOT NULL CHECK (channel_type IN (
                    'email','phone','office_address','website','social','party_office')),
    value         text NOT NULL,
    label         text,                       -- 'Official (sansad.in)', 'Parliament office'
    source_ref_id bigint NOT NULL REFERENCES source_ref(id),
    UNIQUE (person_id, channel_type, value)
);

CREATE INDEX IF NOT EXISTS contact_person_idx ON contact (person_id);
