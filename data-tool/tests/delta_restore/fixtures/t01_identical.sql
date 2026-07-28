-- Seed used on both source and local DB for the optional T01 identical scenario.
\set corp_num1 '''BC0000001'''
\set corp_num2 '''BC0000002'''
\set mig_flow '''migrate-corps-flow'''
\set env '''dev'''
\set completed '''COMPLETED'''
\set ts '''2026-07-01T00:00:00+00'''

INSERT INTO corporation(corp_num) VALUES (:corp_num1), (:corp_num2);
INSERT INTO event(event_id) VALUES (1001), (1002);

INSERT INTO email_domain_groups(email_domain, group_name)
VALUES ('example.com', 'Example');

INSERT INTO bad_emails(id, email, notes)
VALUES (1, 'bad@example.com', 'seed');

INSERT INTO excluded_emails(email, notes)
VALUES ('skip@example.com', 'seed');

INSERT INTO excluded_email_domains(email_domain, notes)
VALUES ('blocked.example', 'seed');

INSERT INTO excluded_email_domain_patterns(id, email_domain, local_part_pattern, notes)
VALUES (1, 'pattern.example', 'test%', 'seed');

INSERT INTO exclude_corps(corp_num, notes)
VALUES (:corp_num2, 'seed');

INSERT INTO corps_with_third_party(corp_num, vendor, vendor_count, notes)
VALUES (:corp_num1, 'VendorA', 1, 'seed');

INSERT INTO bar_corps(identifier, notes)
VALUES (:corp_num1, 'seed');

INSERT INTO mig_group(id, name, target_environment, source_db)
VALUES (1, :mig_flow, :env, 'COLIN');

INSERT INTO mig_batch(id, mig_group_id, name, target_environment)
VALUES (10, 1, 'batch-1', :env);

INSERT INTO mig_corp_batch(id, mig_batch_id, corp_num)
VALUES (20, 10, :corp_num1);

INSERT INTO mig_corp_account(id, corp_num, target_environment, account_id, mig_batch_id)
VALUES (30, :corp_num1, :env, 'account-1', 10);

INSERT INTO corp_processing(id, corp_num, flow_name, environment, mig_batch_id, last_processed_event_id, failed_event_id, processed_status, last_error, last_modified)
VALUES (40, :corp_num1, :mig_flow, :env, 10, 1001, NULL, :completed, NULL, :ts);

INSERT INTO colin_tracking(id, corp_num, flow_name, environment, mig_batch_id, processed_status, last_modified)
VALUES (50, :corp_num1, :mig_flow, :env, 10, :completed, :ts);

INSERT INTO auth_processing(id, corp_num, flow_name, environment, operation, operation_scope, attempt_key, mig_batch_id, processed_status, last_modified)
VALUES (60, :corp_num1, 'auth-flow', :env, 'CREATE', 'BUSINESS', 'attempt-1', 10, :completed, :ts);

INSERT INTO auth_component_operation(id, auth_processing_id, component_name, operation, status, payload)
VALUES (70, 60, 'accounts', 'CREATE', :completed, '{"ok":true}');

INSERT INTO demigrated_filings(id, filing_id, notes)
VALUES (1, 90001, 'seed');
