-- -- Enable triggers for corp-scoped tables (subset refresh/load).
-- -- Intended to be executed from a master DbSchemaCLI script while connected to the target Postgres DB.

-- ALTER TABLE corporation ENABLE TRIGGER ALL;
-- ALTER TABLE corp_name ENABLE TRIGGER ALL;
-- ALTER TABLE corp_state ENABLE TRIGGER ALL;
-- ALTER TABLE event ENABLE TRIGGER ALL;
-- ALTER TABLE filing ENABLE TRIGGER ALL;
-- ALTER TABLE filing_user ENABLE TRIGGER ALL;
-- ALTER TABLE office ENABLE TRIGGER ALL;
-- ALTER TABLE corp_comments ENABLE TRIGGER ALL;
-- ALTER TABLE ledger_text ENABLE TRIGGER ALL;
-- ALTER TABLE corp_party ENABLE TRIGGER ALL;
-- ALTER TABLE corp_party_relationship ENABLE TRIGGER ALL;
-- ALTER TABLE offices_held ENABLE TRIGGER ALL;
-- ALTER TABLE completing_party ENABLE TRIGGER ALL;
-- ALTER TABLE submitting_party ENABLE TRIGGER ALL;
-- ALTER TABLE corp_flag ENABLE TRIGGER ALL;
-- ALTER TABLE cont_out ENABLE TRIGGER ALL;
-- ALTER TABLE conv_event ENABLE TRIGGER ALL;
-- ALTER TABLE conv_ledger ENABLE TRIGGER ALL;
-- ALTER TABLE corp_involved_amalgamating ENABLE TRIGGER ALL;
-- ALTER TABLE corp_involved_cont_in ENABLE TRIGGER ALL;
-- ALTER TABLE corp_restriction ENABLE TRIGGER ALL;
-- ALTER TABLE correction ENABLE TRIGGER ALL;
-- ALTER TABLE jurisdiction ENABLE TRIGGER ALL;
-- ALTER TABLE resolution ENABLE TRIGGER ALL;
-- ALTER TABLE share_series ENABLE TRIGGER ALL;
-- ALTER TABLE share_struct ENABLE TRIGGER ALL;
-- ALTER TABLE share_struct_cls ENABLE TRIGGER ALL;
-- ALTER TABLE notification ENABLE TRIGGER ALL;
-- ALTER TABLE notification_resend ENABLE TRIGGER ALL;
-- ALTER TABLE party_notification ENABLE TRIGGER ALL;
-- ALTER TABLE payment ENABLE TRIGGER ALL;
-- ALTER TABLE carsfile ENABLE TRIGGER ALL;
-- ALTER TABLE carsbox ENABLE TRIGGER ALL;
-- ALTER TABLE carsrept ENABLE TRIGGER ALL;
-- ALTER TABLE carindiv ENABLE TRIGGER ALL;

SET search_path TO TARGET_SCHEMA;

ALTER TABLE TARGET_SCHEMA.notification ADD CONSTRAINT fk_notification_filing FOREIGN KEY (event_id) REFERENCES TARGET_SCHEMA.filing (event_id);
ALTER TABLE TARGET_SCHEMA.office ADD CONSTRAINT fk_office_mailing_address FOREIGN KEY (mailing_addr_id) REFERENCES TARGET_SCHEMA.address (addr_id);
ALTER TABLE TARGET_SCHEMA.office ADD CONSTRAINT fk_office_delivery_address FOREIGN KEY (delivery_addr_id) REFERENCES TARGET_SCHEMA.address (addr_id);
ALTER TABLE TARGET_SCHEMA.office ADD CONSTRAINT fk_corp_party_delivery_address FOREIGN KEY (delivery_addr_id) REFERENCES TARGET_SCHEMA.address (addr_id);
ALTER TABLE TARGET_SCHEMA.corp_party ADD CONSTRAINT fk_corp_party_mailing_address FOREIGN KEY (mailing_addr_id) REFERENCES TARGET_SCHEMA.address (addr_id);
ALTER TABLE TARGET_SCHEMA.completing_party ADD CONSTRAINT fk_completing_party_address FOREIGN KEY (mailing_addr_id) REFERENCES TARGET_SCHEMA.address (addr_id);
ALTER TABLE TARGET_SCHEMA.notification ADD CONSTRAINT fk_notification_address FOREIGN KEY (mailing_addr_id) REFERENCES TARGET_SCHEMA.address (addr_id);
ALTER TABLE TARGET_SCHEMA.corp_processing ADD CONSTRAINT fk_corp_processing_corporation FOREIGN KEY (corp_num) REFERENCES TARGET_SCHEMA.corporation (corp_num);
ALTER TABLE TARGET_SCHEMA.colin_tracking ADD CONSTRAINT fk_colin_tracking_corporation FOREIGN KEY (corp_num) REFERENCES TARGET_SCHEMA.corporation (corp_num);


ALTER TABLE TARGET_SCHEMA.corporation ALTER COLUMN send_ar_ind TYPE boolean USING (CASE send_ar_ind WHEN 'true' THEN true WHEN 'false' THEN false ELSE true END);
ALTER TABLE TARGET_SCHEMA.filing ALTER COLUMN arrangement_ind TYPE boolean USING (CASE arrangement_ind WHEN 'true' THEN true WHEN 'false' THEN false ELSE true END);
ALTER TABLE TARGET_SCHEMA.filing ALTER COLUMN court_appr_ind TYPE boolean USING (CASE court_appr_ind WHEN 'true' THEN true WHEN 'false' THEN false ELSE true END);
ALTER TABLE TARGET_SCHEMA.share_series ALTER COLUMN max_share_ind TYPE boolean USING (CASE max_share_ind WHEN 'true' THEN true WHEN 'false' THEN false ELSE true END);
ALTER TABLE TARGET_SCHEMA.share_struct_cls ALTER COLUMN max_share_ind TYPE boolean USING (CASE max_share_ind WHEN 'true' THEN true WHEN 'false' THEN false ELSE true END);
ALTER TABLE TARGET_SCHEMA.share_struct_cls ALTER COLUMN spec_rights_ind TYPE boolean USING (CASE spec_rights_ind WHEN 'true' THEN true WHEN 'false' THEN false ELSE true END);
ALTER TABLE TARGET_SCHEMA.share_struct_cls ALTER COLUMN par_value_ind TYPE boolean USING (CASE  par_value_ind WHEN 'true' THEN true WHEN 'false' THEN false ELSE true END);
