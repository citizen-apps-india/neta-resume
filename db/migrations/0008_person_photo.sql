-- 0008: official photo URL on person (sansad.in provides these for Rajya Sabha members).
ALTER TABLE person ADD COLUMN IF NOT EXISTS photo_url text;
