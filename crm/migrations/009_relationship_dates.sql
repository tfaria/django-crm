BEGIN;
ALTER TABLE crm_contact ADD COLUMN "start_date" date;
ALTER TABLE crm_contact ADD COLUMN "end_date" date;
COMMIT;
