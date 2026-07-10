-- Disable triggers for corp-scoped tables (subset refresh/load).
-- Intended to be executed from a master DbSchemaCLI script while connected to the target Postgres DB.

ALTER TABLE colin_extract.corporation DISABLE TRIGGER ALL;
ALTER TABLE colin_extract.corp_name DISABLE TRIGGER ALL;
ALTER TABLE colin_extract.corp_state DISABLE TRIGGER ALL;
ALTER TABLE colin_extract.event DISABLE TRIGGER ALL;
ALTER TABLE colin_extract.filing DISABLE TRIGGER ALL;
ALTER TABLE colin_extract.filing_user DISABLE TRIGGER ALL;
ALTER TABLE colin_extract.office DISABLE TRIGGER ALL;
ALTER TABLE colin_extract.corp_comments DISABLE TRIGGER ALL;
ALTER TABLE colin_extract.ledger_text DISABLE TRIGGER ALL;
ALTER TABLE colin_extract.corp_party DISABLE TRIGGER ALL;
ALTER TABLE colin_extract.corp_party_relationship DISABLE TRIGGER ALL;
ALTER TABLE colin_extract.offices_held DISABLE TRIGGER ALL;
ALTER TABLE colin_extract.completing_party DISABLE TRIGGER ALL;
ALTER TABLE colin_extract.submitting_party DISABLE TRIGGER ALL;
ALTER TABLE colin_extract.corp_flag DISABLE TRIGGER ALL;
ALTER TABLE colin_extract.cont_out DISABLE TRIGGER ALL;
ALTER TABLE colin_extract.conv_event DISABLE TRIGGER ALL;
ALTER TABLE colin_extract.conv_ledger DISABLE TRIGGER ALL;
ALTER TABLE colin_extract.corp_involved_amalgamating DISABLE TRIGGER ALL;
ALTER TABLE colin_extract.corp_involved_cont_in DISABLE TRIGGER ALL;
ALTER TABLE colin_extract.corp_restriction DISABLE TRIGGER ALL;
ALTER TABLE colin_extract.correction DISABLE TRIGGER ALL;
ALTER TABLE colin_extract.jurisdiction DISABLE TRIGGER ALL;
ALTER TABLE colin_extract.resolution DISABLE TRIGGER ALL;
ALTER TABLE colin_extract.share_series DISABLE TRIGGER ALL;
ALTER TABLE colin_extract.share_struct DISABLE TRIGGER ALL;
ALTER TABLE colin_extract.share_struct_cls DISABLE TRIGGER ALL;
ALTER TABLE colin_extract.notification DISABLE TRIGGER ALL;
ALTER TABLE colin_extract.notification_resend DISABLE TRIGGER ALL;
ALTER TABLE colin_extract.party_notification DISABLE TRIGGER ALL;
ALTER TABLE colin_extract.payment DISABLE TRIGGER ALL;
ALTER TABLE colin_extract.carsfile DISABLE TRIGGER ALL;
ALTER TABLE colin_extract.carsbox DISABLE TRIGGER ALL;
ALTER TABLE colin_extract.carsrept DISABLE TRIGGER ALL;
ALTER TABLE colin_extract.carindiv DISABLE TRIGGER ALL;
