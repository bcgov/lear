-- Enable triggers for corp-scoped tables (subset refresh/load).
-- Intended to be executed from a master DbSchemaCLI script while connected to the target Postgres DB.

ALTER TABLE colin_extract.corporation ENABLE TRIGGER ALL;
ALTER TABLE colin_extract.corp_name ENABLE TRIGGER ALL;
ALTER TABLE colin_extract.corp_state ENABLE TRIGGER ALL;
ALTER TABLE colin_extract.event ENABLE TRIGGER ALL;
ALTER TABLE colin_extract.filing ENABLE TRIGGER ALL;
ALTER TABLE colin_extract.filing_user ENABLE TRIGGER ALL;
ALTER TABLE colin_extract.office ENABLE TRIGGER ALL;
ALTER TABLE colin_extract.corp_comments ENABLE TRIGGER ALL;
ALTER TABLE colin_extract.ledger_text ENABLE TRIGGER ALL;
ALTER TABLE colin_extract.corp_party ENABLE TRIGGER ALL;
ALTER TABLE colin_extract.corp_party_relationship ENABLE TRIGGER ALL;
ALTER TABLE colin_extract.offices_held ENABLE TRIGGER ALL;
ALTER TABLE colin_extract.completing_party ENABLE TRIGGER ALL;
ALTER TABLE colin_extract.submitting_party ENABLE TRIGGER ALL;
ALTER TABLE colin_extract.corp_flag ENABLE TRIGGER ALL;
ALTER TABLE colin_extract.cont_out ENABLE TRIGGER ALL;
ALTER TABLE colin_extract.conv_event ENABLE TRIGGER ALL;
ALTER TABLE colin_extract.conv_ledger ENABLE TRIGGER ALL;
ALTER TABLE colin_extract.corp_involved_amalgamating ENABLE TRIGGER ALL;
ALTER TABLE colin_extract.corp_involved_cont_in ENABLE TRIGGER ALL;
ALTER TABLE colin_extract.corp_restriction ENABLE TRIGGER ALL;
ALTER TABLE colin_extract.correction ENABLE TRIGGER ALL;
ALTER TABLE colin_extract.jurisdiction ENABLE TRIGGER ALL;
ALTER TABLE colin_extract.resolution ENABLE TRIGGER ALL;
ALTER TABLE colin_extract.share_series ENABLE TRIGGER ALL;
ALTER TABLE colin_extract.share_struct ENABLE TRIGGER ALL;
ALTER TABLE colin_extract.share_struct_cls ENABLE TRIGGER ALL;
ALTER TABLE colin_extract.notification ENABLE TRIGGER ALL;
ALTER TABLE colin_extract.notification_resend ENABLE TRIGGER ALL;
ALTER TABLE colin_extract.party_notification ENABLE TRIGGER ALL;
ALTER TABLE colin_extract.payment ENABLE TRIGGER ALL;
ALTER TABLE colin_extract.carsfile ENABLE TRIGGER ALL;
ALTER TABLE colin_extract.carsbox ENABLE TRIGGER ALL;
ALTER TABLE colin_extract.carsrept ENABLE TRIGGER ALL;
ALTER TABLE colin_extract.carindiv ENABLE TRIGGER ALL;
