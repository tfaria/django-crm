ALTER TABLE crm_contact ADD COLUMN "middle_name" varchar(50);
UPDATE crm_contact SET middle_name = '';
ALTER TABLE crm_contact ALTER COLUMN "middle_name" SET NOT NULL;
