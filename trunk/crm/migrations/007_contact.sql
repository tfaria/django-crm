-- add NOT NULL constraint to contact notes and description
UPDATE crm_contact SET notes = '' WHERE notes IS NULL;
ALTER TABLE crm_contact ALTER COLUMN notes SET NOT NULL;
UPDATE crm_contact SET description = '' WHERE description IS NULL;
ALTER TABLE crm_contact ALTER COLUMN description SET NOT NULL;
