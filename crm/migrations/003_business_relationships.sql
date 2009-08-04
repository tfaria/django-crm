alter table crm_projectrelationshiptype RENAME to crm_relationshiptype;
alter SEQUENCE crm_projectrelationshiptype_id_seq RENAME TO crm_relationshiptype_id_seq;

alter table crm_business_contacts RENAME TO crm_businessrelationship;
alter SEQUENCE crm_business_contacts_id_seq RENAME TO crm_businessrelationship_id_seq;

CREATE TABLE "crm_businessrelationship_types" (
    "id" serial NOT NULL PRIMARY KEY,
    "businessrelationship_id" integer NOT NULL REFERENCES "crm_businessrelationship" ("id") DEFERRABLE INITIALLY DEFERRED,
    "relationshiptype_id" integer NOT NULL REFERENCES "crm_relationshiptype" ("id") DEFERRABLE INITIALLY DEFERRED,
    UNIQUE ("businessrelationship_id", "relationshiptype_id")
);


alter table crm_projectrelationship_types RENAME column projectrelationshiptype_id to relationshiptype_id

.75 hrs
