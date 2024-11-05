
-- disable triggers
ALTER TABLE corporation DISABLE TRIGGER ALL;
ALTER TABLE corp_name DISABLE TRIGGER ALL;
ALTER TABLE corp_state DISABLE TRIGGER ALL;
ALTER TABLE event DISABLE TRIGGER ALL;
ALTER TABLE filing DISABLE TRIGGER ALL;
ALTER TABLE filing_user DISABLE TRIGGER ALL;
ALTER TABLE office DISABLE TRIGGER ALL;
ALTER TABLE address DISABLE TRIGGER ALL;
ALTER TABLE corp_comments DISABLE TRIGGER ALL;
ALTER TABLE ledger_text DISABLE TRIGGER ALL;
ALTER TABLE corp_party DISABLE TRIGGER ALL;
ALTER TABLE corp_party_relationship DISABLE TRIGGER ALL;
ALTER TABLE offices_held DISABLE TRIGGER ALL;
ALTER TABLE completing_party DISABLE TRIGGER ALL;
ALTER TABLE submitting_party DISABLE TRIGGER ALL;
ALTER TABLE corp_flag DISABLE TRIGGER ALL;
ALTER TABLE cont_out DISABLE TRIGGER ALL;
ALTER TABLE conv_event DISABLE TRIGGER ALL;
ALTER TABLE conv_ledger DISABLE TRIGGER ALL;
ALTER TABLE corp_involved_amalgamating DISABLE TRIGGER ALL;
ALTER TABLE corp_involved_cont_in DISABLE TRIGGER ALL;
ALTER TABLE corp_restriction DISABLE TRIGGER ALL;
ALTER TABLE correction DISABLE TRIGGER ALL;
ALTER TABLE jurisdiction DISABLE TRIGGER ALL;
ALTER TABLE resolution DISABLE TRIGGER ALL;
ALTER TABLE share_series DISABLE TRIGGER ALL;
ALTER TABLE share_struct DISABLE TRIGGER ALL;
ALTER TABLE share_struct_cls DISABLE TRIGGER ALL;
ALTER TABLE notification DISABLE TRIGGER ALL;
ALTER TABLE notification_resend DISABLE TRIGGER ALL;
ALTER TABLE party_notification DISABLE TRIGGER ALL;


-- enable triggers
ALTER TABLE corporation ENABLE TRIGGER ALL;
ALTER TABLE corp_name ENABLE TRIGGER ALL;
ALTER TABLE corp_state ENABLE TRIGGER ALL;
ALTER TABLE event ENABLE TRIGGER ALL;
ALTER TABLE filing ENABLE TRIGGER ALL;
ALTER TABLE filing_user ENABLE TRIGGER ALL;
ALTER TABLE office ENABLE TRIGGER ALL;
ALTER TABLE address ENABLE TRIGGER ALL;
ALTER TABLE corp_comments ENABLE TRIGGER ALL;
ALTER TABLE ledger_text ENABLE TRIGGER ALL;
ALTER TABLE corp_party ENABLE TRIGGER ALL;
ALTER TABLE corp_party_relationship ENABLE TRIGGER ALL;
ALTER TABLE offices_held ENABLE TRIGGER ALL;
ALTER TABLE completing_party ENABLE TRIGGER ALL;
ALTER TABLE submitting_party ENABLE TRIGGER ALL;
ALTER TABLE corp_flag ENABLE TRIGGER ALL;
ALTER TABLE cont_out ENABLE TRIGGER ALL;
ALTER TABLE conv_event ENABLE TRIGGER ALL;
ALTER TABLE conv_ledger ENABLE TRIGGER ALL;
ALTER TABLE corp_involved_amalgamating ENABLE TRIGGER ALL;
ALTER TABLE corp_involved_cont_in ENABLE TRIGGER ALL;
ALTER TABLE corp_restriction ENABLE TRIGGER ALL;
ALTER TABLE correction ENABLE TRIGGER ALL;
ALTER TABLE jurisdiction ENABLE TRIGGER ALL;
ALTER TABLE resolution ENABLE TRIGGER ALL;
ALTER TABLE share_series ENABLE TRIGGER ALL;
ALTER TABLE share_struct ENABLE TRIGGER ALL;
ALTER TABLE share_struct_cls ENABLE TRIGGER ALL;
ALTER TABLE notification ENABLE TRIGGER ALL;
ALTER TABLE notification_resend ENABLE TRIGGER ALL;
ALTER TABLE party_notification ENABLE TRIGGER ALL;


-- count overview
select (select count(*) from corporation) as corps,
	(select count(*) from event)       as events,
       (select count(*) from corp_name) as corp_names,
       (select count(*) from corp_state) as corp_states,
       (select count(*) from filing)      as filings,
       (select count(*) from filing_user) as filing_users,
       (select count(*) from office) as offices,
       (select count(*) from address) as addresses,
       (select count(*) from corp_comments) as corp_comments,
       (select count(*) from ledger_text) as ledger_text,
       (select count(*) from corp_party) as corp_parties,
       (select count(*) from corp_party_relationship) as party_relationships,
       (select count(*) from offices_held) as offices_held,
       (select count(*) from completing_party) as completing_parties,
       (select count(*) from submitting_party) as submitting_parties,
       (select count(*) from corp_flag) as corp_flags,
       (select count(*) from cont_out) as cont_outs,
       (select count(*) from conv_event) as conv_events,
       (select count(*) from conv_ledger) as conv_ledgers,
       (select count(*) from corp_involved_amalgamating) as corp_involved_amalgamating,
       (select count(*) from corp_involved_cont_in) as corp_involved_cont_in,
       (select count(*) from corp_restriction) as corp_restrictions,
       (select count(*) from correction) as corrections,
       (select count(*) from jurisdiction) as jurisdiction,
       (select count(*) from resolution) as resolutions,
       (select count(*) from share_struct) as share_structs,
       (select count(*) from share_struct_cls) as share_structs_cls,
       (select count(*) from share_series) as share_series,
       (select count(*) from notification) as notifications,
       (select count(*) from notification_resend) as notification_resends,
       (select count(*) from party_notification) as party_notifications
;


-- Update all email addresses in extract to desired value when req'd
select *
from completing_party cp
where cp.email_req_address is not null or cp.email_req_address != '';

update completing_party
set email_req_address = '<some_email_address>'
where email_req_address is not null or email_req_address != '';


select *
from corp_party cp
where cp.email_address is not null or cp.email_address != '';

update corp_party
set email_address = '<some_email_address>'
where email_address is not null or email_address != '';


select *
from corporation c
where c.admin_email is not null or c.admin_email != '';

update corporation
set admin_email = '<some_email_address>'
where admin_email is not null or admin_email != '';


select *
from filing_user u
where u.email_addr is not null or u.email_addr != '';

update filing_user
set email_addr = '<some_email_address>'
where email_addr is not null or email_addr != '';


select *
from notification n
where n.email_address is not null or n.email_address != '';

update notification
set email_address = '<some_email_address>'
where email_address is not null or email_address != '';


select *
from notification_resend nr
where nr.email_address is not null or nr.email_address != '';

update notification_resend
set email_address = '<some_email_address>'
where email_address is not null or email_address != '';


select *
from party_notification pn
where pn.email_address is not null or pn.email_address != '';

update party_notification
set email_address = '<some_email_address>'
where email_address is not null or email_address != '';


select *
from submitting_party sp
where sp.email_req_address is not null or sp.email_req_address != '';

update submitting_party
set email_req_address = '<some_email_address>'
where email_req_address is not null or email_req_address != '';
