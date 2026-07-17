-- End-to-end row selection apply: 1 parent plus 16/16/16 selected children.
TRUNCATE delta_ctl.table_config, delta_ctl.run_counts, delta_ctl.selection,
  delta_ctl.row_selection, delta_ctl.selection_diagnostics, delta_ctl.apply_counts,
  delta_ctl.touched_tables, delta_ctl.dependency_violations;
DROP SCHEMA delta_stage CASCADE;
DROP SCHEMA delta_map CASCADE;
DROP SCHEMA delta_diff CASCADE;
CREATE SCHEMA delta_stage;
CREATE SCHEMA delta_map;
CREATE SCHEMA delta_diff;
TRUNCATE public.mig_group, public.mig_batch, public.mig_corp_account,
  public.mig_corp_batch, public.corp_processing, public.corporation RESTART IDENTITY;

CREATE UNLOGGED TABLE delta_stage.mig_group (LIKE public.mig_group INCLUDING DEFAULTS);
ALTER TABLE delta_stage.mig_group ADD COLUMN _delta_row_id bigint GENERATED ALWAYS AS IDENTITY;
CREATE UNLOGGED TABLE delta_stage.mig_batch (LIKE public.mig_batch INCLUDING DEFAULTS);
ALTER TABLE delta_stage.mig_batch ADD COLUMN _delta_row_id bigint GENERATED ALWAYS AS IDENTITY;
CREATE UNLOGGED TABLE delta_stage.mig_corp_account (LIKE public.mig_corp_account INCLUDING DEFAULTS);
ALTER TABLE delta_stage.mig_corp_account ADD COLUMN _delta_row_id bigint GENERATED ALWAYS AS IDENTITY;
CREATE UNLOGGED TABLE delta_stage.mig_corp_batch (LIKE public.mig_corp_batch INCLUDING DEFAULTS);
ALTER TABLE delta_stage.mig_corp_batch ADD COLUMN _delta_row_id bigint GENERATED ALWAYS AS IDENTITY;
CREATE UNLOGGED TABLE delta_stage.corp_processing (LIKE public.corp_processing INCLUDING DEFAULTS);
ALTER TABLE delta_stage.corp_processing ADD COLUMN _delta_row_id bigint GENERATED ALWAYS AS IDENTITY;

INSERT INTO delta_ctl.table_config(table_name, load_phase)
VALUES ('mig_group', 20), ('mig_batch', 30), ('mig_corp_batch', 40), -- NOSONAR
       ('mig_corp_account', 50), ('corp_processing', 60); -- NOSONAR
SELECT delta_ctl.complete_table_config();

INSERT INTO public.mig_group(id, name, target_environment, source_db)
VALUES (1, 'existing-group', 'dev', 'COLIN');
INSERT INTO delta_stage.mig_group(id, name, target_environment, source_db)
VALUES (1, 'existing-group', 'dev', 'COLIN');
INSERT INTO delta_stage.mig_batch(id, mig_group_id, name, target_environment)
VALUES (152, 1, 'selected-parent', 'dev');

INSERT INTO delta_stage.mig_corp_account(id, corp_num, target_environment, account_id, mig_batch_id)
SELECT id, 'BC' || lpad(id::text, 7, '0'), 'dev', 'acct-' || id, 152
FROM (SELECT 23 AS id UNION ALL SELECT generate_series(23643, 23658)) q;

INSERT INTO delta_stage.mig_corp_batch(id, mig_batch_id, corp_num)
SELECT id, 152, 'MB' || lpad(id::text, 7, '0') FROM generate_series(3001, 3020) id;

INSERT INTO public.corporation(corp_num)
SELECT 'CP' || lpad(id::text, 7, '0') FROM generate_series(4001, 4032) id;
INSERT INTO delta_stage.corp_processing(
  id, corp_num, flow_name, environment, mig_batch_id, processed_status, last_modified)
SELECT id, 'CP' || lpad(id::text, 7, '0'), 'flow-' || id, 'dev', 152, 'READY', now()
FROM generate_series(4001, 4032) id;

SELECT delta_ctl.run_preview_classification();
INSERT INTO delta_ctl.selection(table_name, class)
SELECT table_name, 'NEW' FROM delta_ctl.table_config; -- NOSONAR
INSERT INTO delta_ctl.selection(table_name, class)
SELECT table_name, 'CHANGED' FROM delta_ctl.table_config;

DO $$
DECLARE
  c_include_mode constant text := 'include';
BEGIN
  INSERT INTO delta_ctl.row_selection(
    table_name, class, mode, kind, value_from, value_to, corp_num, is_range, source_line)
  VALUES
    ('mig_corp_account', 'NEW', 'exclude', 'id', 23, 23, NULL, false, 1),
    ('mig_corp_batch', 'NEW', c_include_mode, 'id', 3001, 3017, NULL, true, 2),
    ('mig_corp_batch', 'NEW', 'exclude', 'id', 3017, 3017, NULL, false, 3),
    ('corp_processing', 'NEW', c_include_mode, 'id', 4001, 4015, NULL, true, 4),
    ('corp_processing', 'NEW', c_include_mode, 'corp', NULL, NULL, 'CP0004016', false, 5);
END $$;

SELECT delta_ctl.run_apply();
