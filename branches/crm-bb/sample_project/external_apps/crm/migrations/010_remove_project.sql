--- migrate crm project to timepiece

--- pendulum entry
BEGIN;
ALTER TABLE pendulum_entry DROP CONSTRAINT pendulum_entry_project_id_fkey;

UPDATE pendulum_entry
SET project_id = p2.id
FROM pendulum_project p1, crm_project p2
WHERE p1.id = pendulum_entry.project_id AND p2.name = p1.name;

ALTER TABLE pendulum_entry RENAME TO timepiece_entry;
ALTER TABLE pendulum_entry_pkey RENAME TO timepiece_entry_pkey;
ALTER INDEX pendulum_entry_activity_id RENAME TO timepiece_entry_activity_id;
ALTER INDEX pendulum_entry_project_id RENAME TO timepiece_entry_project_id;
ALTER INDEX pendulum_entry_site_id RENAME TO timepiece_entry_site_id;
ALTER INDEX pendulum_entry_user_id RENAME TO timepiece_entry_user_id;
COMMIT;

BEGIN;
-- remove unused tables
DROP TABLE pendulum_project_sites;
DROP TABLE pendulum_project;
DROP TABLE pendulum_pendulumconfiguration;

--- crm project
ALTER TABLE crm_project RENAME TO timepiece_project;
ALTER SEQUENCE crm_project_id_seq RENAME TO timepiece_project_id_seq;
ALTER INDEX crm_project_business_id RENAME TO timepiece_project_business_id;
ALTER INDEX crm_project_point_person_id RENAME TO timepiece_project_point_person_id;
ALTER INDEX crm_project_pkey RENAME TO timepiece_project_pkey;
ALTER INDEX crm_project_contacts_pkey RENAME TO timepiece_project_contacts_pkey;
ALTER INDEX crm_project_contacts_project_id_key RENAME TO timepiece_project_contacts_project_id_key;
ALTER TABLE timepiece_project DROP CONSTRAINT crm_project_business_id_fkey;
ALTER TABLE timepiece_project DROP CONSTRAINT crm_project_point_person_id_fkey;
ALTER TABLE timepiece_project ADD CONSTRAINT timepiece_project_business_id_fkey FOREIGN KEY (business_id) REFERENCES crm_contact(id) DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE timepiece_project ADD CONSTRAINT timepiece_project_point_person_id_fkey FOREIGN KEY (point_person_id) REFERENCES auth_user(id) DEFERRABLE INITIALLY DEFERRED;

--- crm project relationship
ALTER TABLE crm_projectrelationship RENAME TO timepiece_projectrelationship;
ALTER INDEX crm_projectrelationship_project_id RENAME TO timepiece_projectrelationship_project_id;
ALTER INDEX crm_projectrelationship_user_id RENAME TO timepiece_projectrelationship_user_id;
ALTER TABLE timepiece_projectrelationship DROP CONSTRAINT crm_project_contact_id_fkey;
ALTER TABLE timepiece_projectrelationship DROP CONSTRAINT crm_project_contacts_project_id_fkey;
ALTER TABLE timepiece_projectrelationship ADD CONSTRAINT timepiece_project_contact_id_fkey FOREIGN KEY (contact_id) REFERENCES crm_contact(id) DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE timepiece_projectrelationship ADD CONSTRAINT timepiece_project_contacts_project_id_fkey FOREIGN KEY (project_id) REFERENCES timepiece_project(id) DEFERRABLE INITIALLY DEFERRED;

--- pendulum activity
ALTER TABLE pendulum_activity RENAME TO timepiece_activity;
ALTER INDEX pendulum_activity_pkey RENAME TO timepiece_activity_pkey;
ALTER INDEX pendulum_activity_code_key RENAME TO timepiece_activity_code_key;
ALTER SEQUENCE pendulum_activity_id_seq RENAME TO timepiece_activity_id_seq;

--- pendulum activity sites
ALTER TABLE pendulum_activity_sites RENAME TO timepiece_activity_sites;
ALTER INDEX pendulum_activity_sites_activity_id_key RENAME TO timepiece_activity_sites_activity_id_key;
ALTER INDEX pendulum_activity_sites_pkey RENAME TO timepiece_activity_sites_pkey;
ALTER SEQUENCE pendulum_activity_sites_id_seq RENAME TO timepiece_activity_sites_id_seq;
COMMIT;

--- entry constraints
BEGIN;
ALTER SEQUENCE pendulum_entry_id_seq RENAME TO timepiece_entry_id_seq;
ALTER TABLE timepiece_entry DROP CONSTRAINT pendulum_entry_activity_id_fkey;
ALTER TABLE timepiece_entry DROP CONSTRAINT pendulum_entry_site_id_fkey;
ALTER TABLE timepiece_entry DROP CONSTRAINT pendulum_entry_user_id_fkey;
ALTER TABLE timepiece_entry ADD CONSTRAINT timepiece_entry_activity_id_fkey FOREIGN KEY (activity_id) REFERENCES timepiece_activity(id) DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE timepiece_entry ADD CONSTRAINT timepiece_entry_site_id_fkey FOREIGN KEY (site_id) REFERENCES django_site(id) DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE timepiece_entry ADD CONSTRAINT timepiece_entry_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth_user(id) DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE timepiece_entry ADD CONSTRAINT pendulum_entry_project_id_fkey FOREIGN KEY (project_id) REFERENCES timepiece_project(id) DEFERRABLE INITIALLY DEFERRED;
COMMIT;

DROP TABLE timepiece_activity_sites;
ALTER TABLE timepiece_entry DROP COLUMN site_id;

BEGIN;
CREATE TABLE "timepiece_project_interactions" (
    "id" serial NOT NULL PRIMARY KEY,
    "project_id" integer NOT NULL REFERENCES "timepiece_project" ("id") DEFERRABLE INITIALLY DEFERRED,
    "interaction_id" integer NOT NULL REFERENCES "crm_interaction" ("id") DEFERRABLE INITIALLY DEFERRED,
    UNIQUE ("project_id", "interaction_id")
);
CREATE TABLE "timepiece_projectrelationship_types" (
    "id" serial NOT NULL PRIMARY KEY,
    "projectrelationship_id" integer NOT NULL REFERENCES "timepiece_projectrelationship" ("id") DEFERRABLE INITIALLY DEFERRED,
    "relationshiptype_id" integer NOT NULL REFERENCES "crm_relationshiptype" ("id") DEFERRABLE INITIALLY DEFERRED,
    UNIQUE ("projectrelationship_id", "relationshiptype_id")
);
COMMIT;

BEGIN;
ALTER TABLE timepiece_project ADD COLUMN "billing_period_id" integer;
INSERT INTO timepiece_project_interactions (project_id, interaction_id) SELECT project_id, id FROM crm_interaction WHERE project_id IS NOT NULL;
ALTER TABLE crm_interaction DROP COLUMN project_id;
ALTER TABLE timepiece_entry ADD COLUMN "location" varchar(255);
UPDATE timepiece_entry SET location = '';
COMMIT;

BEGIN;
ALTER TABLE timepiece_entry ALTER location SET NOT NULL;
ALTER TABLE timepiece_entry ALTER comments SET NOT NULL;
COMMIT;

