BEGIN;
ALTER TABLE crm_projectrelationshiptype RENAME TO crm_relationshiptype;
ALTER SEQUENCE crm_projectrelationshiptype_id_seq RENAME TO crm_relationshiptype_id_seq;
ALTER TABLE crm_projectrelationship_types RENAME column projectrelationshiptype_id TO relationshiptype_id;

ALTER TABLE crm_business_contacts RENAME TO crm_businessrelationship;
ALTER SEQUENCE crm_business_contacts_id_seq RENAME TO crm_businessrelationship_id_seq;

CREATE TABLE "crm_businessrelationship_types" (
    "id" serial NOT NULL PRIMARY KEY,
    "businessrelationship_id" integer NOT NULL REFERENCES "crm_businessrelationship" ("id") DEFERRABLE INITIALLY DEFERRED,
    "relationshiptype_id" integer NOT NULL REFERENCES "crm_relationshiptype" ("id") DEFERRABLE INITIALLY DEFERRED,
    UNIQUE ("businessrelationship_id", "relationshiptype_id")
);
COMMIT;
