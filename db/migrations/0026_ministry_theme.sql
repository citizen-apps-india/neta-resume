-- 0026: ministry -> policy-theme reference map, for the "Policy focus" view.
-- Each parliamentary_question carries the official ministry it addressed. This auditable, versionable
-- lookup groups the ~50+ Union ministries into a handful of policy themes (economy, health, social, …)
-- so the API can compute, at read time, what an MP concentrates on vs. the House average — a DESCRIPTIVE
-- topical breakdown derived from official ministry tags, never a value judgment. Curated like the severity
-- rubric / party-canon map (a reference table the read layer JOINs; it does not classify).
--
-- ministry_key is the LOWERCASED ministry string so casing variants ("Labour And Employment" /
-- "Labour and Employment") collapse to one row. Unmapped ministries fall through to "Other" at read time.

CREATE TABLE ministry_theme (
    ministry_key text PRIMARY KEY,     -- lower(trim(ministry)) as it appears in parliamentary_question
    theme        text NOT NULL
);
