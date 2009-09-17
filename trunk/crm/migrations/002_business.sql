BEGIN;
ALTER TABLE crm_business DROP COLUMN address_id;
ALTER TABLE crm_business ADD COLUMN description text;

CREATE TABLE "crm_business_related_businesses" (
    "id" serial NOT NULL PRIMARY KEY,
    "from_business_id" integer NOT NULL REFERENCES "crm_business" ("id") DEFERRABLE INITIALLY DEFERRED,
    "to_business_id" integer NOT NULL REFERENCES "crm_business" ("id") DEFERRABLE INITIALLY DEFERRED,
    UNIQUE ("from_business_id", "to_business_id")
);
COMMIT;
