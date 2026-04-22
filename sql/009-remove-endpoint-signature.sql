-- Remove deprecated endpoint signature storage
ALTER TABLE endpoints DROP COLUMN IF EXISTS signature;
