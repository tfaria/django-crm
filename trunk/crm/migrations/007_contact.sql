-- add NOT NULL constraint to contact notes and description
BEGIN;
UPDATE crm_contact SET notes = '' WHERE notes IS NULL;
UPDATE crm_contact SET description = '' WHERE description IS NULL;
COMMIT;

BEGIN;
ALTER TABLE crm_contact ALTER COLUMN notes SET NOT NULL;
ALTER TABLE crm_contact ALTER COLUMN description SET NOT NULL;
COMMIT;
