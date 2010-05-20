BEGIN;
CREATE TABLE "crm_profile_locations" (
    "id" serial NOT NULL PRIMARY KEY,
    "profile_id" integer NOT NULL REFERENCES "crm_profile" ("id") DEFERRABLE INITIALLY DEFERRED,
    "location_id" integer NOT NULL REFERENCES "contactinfo_location" ("id") DEFERRABLE INITIALLY DEFERRED,
    UNIQUE ("profile_id", "location_id")
);
CREATE TABLE "crm_business_locations" (
    "id" serial NOT NULL PRIMARY KEY,
    "business_id" integer NOT NULL REFERENCES "crm_business" ("id") DEFERRABLE INITIALLY DEFERRED,
    "location_id" integer NOT NULL REFERENCES "contactinfo_location" ("id") DEFERRABLE INITIALLY DEFERRED,
    UNIQUE ("business_id", "location_id")
);
COMMIT;
