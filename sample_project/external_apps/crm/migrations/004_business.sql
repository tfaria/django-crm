-- update project model to point business fk to new contact model
BEGIN;
ALTER TABLE crm_project DROP CONSTRAINT crm_project_business_id_fkey;
UPDATE crm_project
SET business_id = crm_contact.id
FROM crm_contact
WHERE crm_contact.business_id = crm_project.business_id;
ALTER TABLE crm_project ADD CONSTRAINT crm_project_business_id_fkey FOREIGN KEY (business_id) REFERENCES "crm_contact" ("id") DEFERRABLE INITIALLY DEFERRED;
COMMIT;


-- update exchange model to point business fk to new contact model
BEGIN;
ALTER TABLE ledger_exchange DROP CONSTRAINT ledger_exchange_business_id_fkey;
UPDATE ledger_exchange
SET business_id = crm_contact.id
FROM crm_contact
WHERE crm_contact.business_id = ledger_exchange.business_id;
COMMIT;

BEGIN;
ALTER TABLE ledger_exchange ADD CONSTRAINT ledger_exchange_business_id_fkey FOREIGN KEY (business_id) REFERENCES "crm_contact" ("id") DEFERRABLE INITIALLY DEFERRED;
COMMIT;


-- drop old profile/business tables
DROP TABLE crm_phone;
DROP TABLE crm_profile_locations;
DROP TABLE crm_profile;
DROP TABLE crm_business CASCADE;


-- update project relationship to point to contact model
BEGIN;
ALTER TABLE crm_projectrelationship DROP CONSTRAINT crm_project_contacts_user_id_fkey;
ALTER TABLE crm_projectrelationship DROP CONSTRAINT crm_project_contacts_project_id_key;
UPDATE crm_projectrelationship
SET user_id = crm_contact.id
FROM crm_contact
WHERE crm_projectrelationship.user_id = crm_contact.user_id;
ALTER TABLE crm_projectrelationship RENAME user_id TO contact_id;
ALTER TABLE crm_projectrelationship ADD CONSTRAINT crm_project_contact_id_fkey FOREIGN KEY (contact_id) REFERENCES "crm_contact" ("id") DEFERRABLE INITIALLY DEFERRED;
CREATE UNIQUE INDEX crm_project_contacts_project_id_key ON crm_projectrelationship (project_id, contact_id);
COMMIT;


-- convert interaction contacts to user Contact model rather than User model
BEGIN;
ALTER TABLE crm_interaction_contacts DROP CONSTRAINT crm_interaction_contacts_user_id_fkey;
ALTER TABLE crm_interaction_contacts DROP CONSTRAINT crm_interaction_contacts_interaction_id_key;
UPDATE crm_interaction_contacts
SET user_id = crm_contact.id
FROM crm_contact
WHERE crm_interaction_contacts.user_id = crm_contact.user_id;
ALTER TABLE crm_interaction_contacts RENAME user_id TO contact_id;
ALTER TABLE crm_interaction_contacts ADD CONSTRAINT crm_project_contacts_user_id_fkey FOREIGN KEY (contact_id) REFERENCES "crm_contact" ("id") DEFERRABLE INITIALLY DEFERRED;
CREATE UNIQUE INDEX crm_interaction_contacts_interaction_id_key ON crm_interaction_contacts (interaction_id, contact_id);
COMMIT;


-- add NOT NULL constraint to interaction memo
UPDATE crm_interaction SET memo = '' WHERE memo IS NULL;
ALTER TABLE crm_interaction ALTER COLUMN memo SET NOT NULL;
