-- Re-apply the state-assembly ls_state_code fix. 0018 corrected the rows that existed when it ran, but a
-- few state office_terms were written afterward (by a rollout job on the pre-fix checkout) and still carry
-- the DISTRICT (e.g. Odisha 'Bargarh'/'Ganjam'/'Jajpur'). 0018 is already recorded in schema_migrations so
-- `neta migrate` won't re-run it — this new version repeats the same idempotent UPDATE with writes halted,
-- catching every residual. The ingest itself is already fixed (myneta derives state from the house name).

UPDATE office_term ot
SET ls_state_code = regexp_replace(h.name, '\s+(Vidhan Sabha|Legislative Assembly)$', '')
FROM house h
WHERE h.id = ot.house_id
  AND h.jurisdiction = 'state'
  AND ot.ls_state_code IS DISTINCT FROM regexp_replace(h.name, '\s+(Vidhan Sabha|Legislative Assembly)$', '');
