BEGIN;
ALTER TABLE crm_contactrelationship ADD COLUMN "start_date" date;
ALTER TABLE crm_contactrelationship ADD COLUMN "end_date" date;
COMMIT;
