-- Semantic selector diagnostics: unsupported kinds, class gate, and zero match.
TRUNCATE delta_ctl.table_config, delta_ctl.run_counts, delta_ctl.selection,
  delta_ctl.row_selection, delta_ctl.selection_diagnostics, delta_ctl.apply_counts,
  delta_ctl.touched_tables, delta_ctl.dependency_violations;
DROP SCHEMA delta_stage CASCADE; DROP SCHEMA delta_map CASCADE; DROP SCHEMA delta_diff CASCADE;
CREATE SCHEMA delta_stage; CREATE SCHEMA delta_map; CREATE SCHEMA delta_diff;

CREATE UNLOGGED TABLE delta_stage.bar_corps (LIKE public.bar_corps INCLUDING DEFAULTS);
ALTER TABLE delta_stage.bar_corps ADD COLUMN _delta_row_id bigint GENERATED ALWAYS AS IDENTITY;
CREATE UNLOGGED TABLE delta_stage.mig_group (LIKE public.mig_group INCLUDING DEFAULTS);
ALTER TABLE delta_stage.mig_group ADD COLUMN _delta_row_id bigint GENERATED ALWAYS AS IDENTITY;
CREATE UNLOGGED TABLE delta_stage.bad_emails (LIKE public.bad_emails INCLUDING DEFAULTS);
ALTER TABLE delta_stage.bad_emails ADD COLUMN _delta_row_id bigint GENERATED ALWAYS AS IDENTITY;
CREATE UNLOGGED TABLE delta_stage.auth_processing (LIKE public.auth_processing INCLUDING DEFAULTS);
ALTER TABLE delta_stage.auth_processing ADD COLUMN _delta_row_id bigint GENERATED ALWAYS AS IDENTITY;
CREATE UNLOGGED TABLE delta_stage.auth_component_operation (LIKE public.auth_component_operation INCLUDING DEFAULTS);
ALTER TABLE delta_stage.auth_component_operation ADD COLUMN _delta_row_id bigint GENERATED ALWAYS AS IDENTITY;
CREATE UNLOGGED TABLE delta_stage.email_domain_groups (LIKE public.email_domain_groups INCLUDING DEFAULTS);
ALTER TABLE delta_stage.email_domain_groups ADD COLUMN _delta_row_id bigint GENERATED ALWAYS AS IDENTITY;

INSERT INTO delta_ctl.table_config(table_name, load_phase)
VALUES ('bar_corps', 10), ('mig_group', 20), ('bad_emails', 30), -- NOSONAR
       ('auth_processing', 40), ('auth_component_operation', 50), -- NOSONAR
       ('email_domain_groups', 60), ('excluded_emails', 70); -- NOSONAR
SELECT delta_ctl.complete_table_config();
SELECT delta_ctl.create_class_table('bar_corps');
SELECT delta_ctl.create_class_table('mig_group');
SELECT delta_ctl.create_class_table('bad_emails');
SELECT delta_ctl.create_class_table('auth_processing');
SELECT delta_ctl.create_class_table('auth_component_operation');
SELECT delta_ctl.create_class_table('email_domain_groups');

INSERT INTO delta_stage.bar_corps(identifier, notes) VALUES ('BC1', 'x');
INSERT INTO delta_stage.mig_group(id, name, target_environment, source_db) VALUES (1, 'g', 'dev', 'C');
INSERT INTO delta_stage.bad_emails(id, email, notes) VALUES (1, 'a@example.test', 'x');
INSERT INTO delta_stage.auth_processing(id, corp_num) VALUES (50, 'BCOK');
INSERT INTO delta_stage.auth_component_operation(id, auth_processing_id, component_name)
VALUES (60, 50, 'component');
INSERT INTO delta_stage.email_domain_groups(email_domain, group_name)
VALUES ('example.test', 'test-group');
INSERT INTO delta_diff.bar_corps_class(_delta_row_id, class) VALUES (1, 'NEW');
INSERT INTO delta_diff.mig_group_class(_delta_row_id, staged_pk, class) VALUES (1, 1, 'NEW');
INSERT INTO delta_diff.bad_emails_class(_delta_row_id, staged_pk, class) VALUES (1, 1, 'NEW');
INSERT INTO delta_diff.auth_processing_class(_delta_row_id, staged_pk, class) VALUES (1, 50, 'NEW');
INSERT INTO delta_diff.auth_component_operation_class(_delta_row_id, staged_pk, class) VALUES (1, 60, 'NEW');
INSERT INTO delta_diff.email_domain_groups_class(_delta_row_id, class) VALUES (1, 'NEW');

INSERT INTO delta_ctl.selection(table_name, class)
VALUES ('bar_corps', 'NEW'), ('mig_group', 'NEW'), ('bad_emails', 'NEW'),
       ('auth_processing', 'NEW'), ('auth_component_operation', 'NEW'),
       ('email_domain_groups', 'NEW'), ('excluded_emails', 'NEW');
INSERT INTO delta_ctl.only_corps(corp_num) VALUES ('BCOK');
INSERT INTO delta_ctl.row_selection(
  table_name, class, mode, kind, value_from, value_to, corp_num, is_range, source_line)
VALUES
 ('bar_corps', 'NEW', 'include', 'id', 1, 1, NULL, false, 10), -- NOSONAR
 ('mig_group', 'NEW', 'include', 'corp', NULL, NULL, 'BC1', false, 11),
 ('bad_emails', 'CHANGED', 'include', 'id', 1, 1, NULL, false, 12),
 ('bad_emails', 'NEW', 'include', 'id', 999, 999, NULL, false, 13),
 ('bar_corps', 'NEW', 'include', 'corp', NULL, NULL, 'BC1', false, 14),
 ('auth_component_operation', 'NEW', 'include', 'corp', NULL, NULL, 'BCOK', false, 15),
 ('email_domain_groups', 'NEW', 'include', 'row', 1, 1, NULL, false, 16),
 ('excluded_emails', 'NEW', 'include', 'row', 1, 1, NULL, false, 17);
SELECT delta_ctl.verify_row_selection();
