-- Fix state-assembly office_terms whose ls_state_code got the DISTRICT instead of the state.
-- Cause: the ingest mapped house.state_code -> state name via a code dict that silently fell back to the
-- parsed district when a code wasn't listed (Odisha 'OD' vs ISO 'OR', Chhattisgarh 'CG', Uttarakhand 'UK').
-- The ingest now derives the state from the house NAME; this backfills existing rows the same way.
-- Idempotent: only rewrites rows that don't already match the house-derived state name.

UPDATE office_term ot
SET ls_state_code = regexp_replace(h.name, '\s+(Vidhan Sabha|Legislative Assembly)$', '')
FROM house h
WHERE h.id = ot.house_id
  AND h.jurisdiction = 'state'
  AND ot.ls_state_code IS DISTINCT FROM regexp_replace(h.name, '\s+(Vidhan Sabha|Legislative Assembly)$', '');
