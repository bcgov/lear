-- SET search_path TO TARGET_SCHEMA;

-- ALTER TABLE TARGET_SCHEMA.notification ADD CONSTRAINT fk_notification_filing FOREIGN KEY (event_id) REFERENCES TARGET_SCHEMA.filing (event_id);
-- ALTER TABLE TARGET_SCHEMA.office ADD CONSTRAINT fk_office_mailing_address FOREIGN KEY (mailing_addr_id) REFERENCES TARGET_SCHEMA.address (addr_id);
-- ALTER TABLE TARGET_SCHEMA.office ADD CONSTRAINT fk_office_delivery_address FOREIGN KEY (delivery_addr_id) REFERENCES TARGET_SCHEMA.address (addr_id);
-- ALTER TABLE TARGET_SCHEMA.office ADD CONSTRAINT fk_corp_party_delivery_address FOREIGN KEY (delivery_addr_id) REFERENCES TARGET_SCHEMA.address (addr_id);
-- ALTER TABLE TARGET_SCHEMA.corp_party ADD CONSTRAINT fk_corp_party_mailing_address FOREIGN KEY (mailing_addr_id) REFERENCES TARGET_SCHEMA.address (addr_id);
-- ALTER TABLE TARGET_SCHEMA.completing_party ADD CONSTRAINT fk_completing_party_address FOREIGN KEY (mailing_addr_id) REFERENCES TARGET_SCHEMA.address (addr_id);
-- ALTER TABLE TARGET_SCHEMA.notification ADD CONSTRAINT fk_notification_address FOREIGN KEY (mailing_addr_id) REFERENCES TARGET_SCHEMA.address (addr_id);


-- ALTER TABLE TARGET_SCHEMA.corporation ALTER COLUMN send_ar_ind TYPE boolean USING (CASE send_ar_ind WHEN 'true' THEN true WHEN 'false' THEN false ELSE true END);
-- ALTER TABLE TARGET_SCHEMA.filing ALTER COLUMN arrangement_ind TYPE boolean USING (CASE arrangement_ind WHEN 'true' THEN true WHEN 'false' THEN false ELSE true END);
-- ALTER TABLE TARGET_SCHEMA.filing ALTER COLUMN court_appr_ind TYPE boolean USING (CASE court_appr_ind WHEN 'true' THEN true WHEN 'false' THEN false ELSE true END);
-- ALTER TABLE TARGET_SCHEMA.share_series ALTER COLUMN max_share_ind TYPE boolean USING (CASE max_share_ind WHEN 'true' THEN true WHEN 'false' THEN false ELSE true END);
-- ALTER TABLE TARGET_SCHEMA.share_struct_cls ALTER COLUMN max_share_ind TYPE boolean USING (CASE max_share_ind WHEN 'true' THEN true WHEN 'false' THEN false ELSE true END);
-- ALTER TABLE TARGET_SCHEMA.share_struct_cls ALTER COLUMN spec_rights_ind TYPE boolean USING (CASE spec_rights_ind WHEN 'true' THEN true WHEN 'false' THEN false ELSE true END);
-- ALTER TABLE TARGET_SCHEMA.share_struct_cls ALTER COLUMN par_value_ind TYPE boolean USING (CASE  par_value_ind WHEN 'true' THEN true WHEN 'false' THEN false ELSE true END);
