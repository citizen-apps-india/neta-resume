-- 0015: allow municipal (local-body) houses — corporators/mayors of a municipal corporation.
-- The Directory now spans union (LS/RS), state (assemblies) and municipal levels with the same model.

ALTER TABLE house DROP CONSTRAINT house_jurisdiction_check;
ALTER TABLE house ADD CONSTRAINT house_jurisdiction_check
    CHECK (jurisdiction IN ('union', 'state', 'municipal'));
