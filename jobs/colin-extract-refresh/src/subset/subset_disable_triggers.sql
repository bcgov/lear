SET search_path TO TARGET_SCHEMA;

-- ALTER TABLE TARGET_SCHEMA.notification 
--   DROP CONSTRAINT fk_notification_filing ;
-- ALTER TABLE TARGET_SCHEMA.office 
--   DROP CONSTRAINT fk_office_mailing_address ;
-- ALTER TABLE TARGET_SCHEMA.office 
-- DROP CONSTRAINT fk_office_delivery_address ;
-- ALTER TABLE TARGET_SCHEMA.corp_party 
--   DROP CONSTRAINT fk_corp_party_mailing_address ;
-- ALTER TABLE TARGET_SCHEMA.completing_party 
--   DROP CONSTRAINT fk_completing_party_address ;
-- ALTER TABLE TARGET_SCHEMA.office 
--   DROP CONSTRAINT fk_corp_party_delivery_address ;
-- ALTER TABLE TARGET_SCHEMA.notification 
--   DROP CONSTRAINT fk_notification_address ;
-- ALTER TABLE TARGET_SCHEMA.filing ALTER COLUMN arrangement_ind TYPE CHARACTER VARYING(255);
-- ALTER TABLE TARGET_SCHEMA.corporation ALTER COLUMN send_ar_ind TYPE CHARACTER VARYING(255);
-- ALTER TABLE TARGET_SCHEMA.share_series ALTER COLUMN max_share_ind TYPE CHARACTER VARYING(255);
-- ALTER TABLE TARGET_SCHEMA.share_struct_cls ALTER COLUMN max_share_ind TYPE CHARACTER VARYING(255);
-- ALTER TABLE TARGET_SCHEMA.filing ALTER COLUMN court_appr_ind TYPE CHARACTER VARYING(255);
-- ALTER TABLE TARGET_SCHEMA.share_struct_cls ALTER COLUMN spec_rights_ind TYPE CHARACTER VARYING(255);
-- ALTER TABLE TARGET_SCHEMA.share_struct_cls ALTER COLUMN par_value_ind TYPE CHARACTER VARYING(255);

SET CONSTRAINTS ALL DEFERRED;