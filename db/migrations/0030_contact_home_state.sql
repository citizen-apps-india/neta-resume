-- 0030: allow a 'home_state' contact channel — the legislator's DECLARED home state from the public
-- ECI affidavit (via MyNeta). This is the coarse locality only; residential addresses / personal
-- mobile numbers remain deliberately excluded (see pipelines/enrich/contacts.py). Enriches the Contact
-- tab with a sourced "declared home state" fact.

ALTER TABLE contact DROP CONSTRAINT IF EXISTS contact_channel_type_check;
ALTER TABLE contact ADD CONSTRAINT contact_channel_type_check
    CHECK (channel_type IN ('email','phone','office_address','website','social','party_office','home_state'));
