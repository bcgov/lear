-- Focused SQL smoke for auth_component_operation LOCAL_ONLY scoping.
-- Assumes 00_install.sql, 10_functions.sql, and minimal_schema.sql have already run.
\set corp_num '''BC0000001'''
\set auth_flow '''auth-flow'''
\set env '''dev'''
\set op '''CREATE'''
\set scope '''BUSINESS'''
\set completed '''COMPLETED'''
\set ts '''2026-07-01T00:00:00+00'''
\set ok_payload '''{\"ok\":true}'''
\set accounts '''accounts'''

TRUNCATE delta_ctl.table_config, delta_ctl.run_counts, delta_ctl.apply_counts,
  delta_ctl.touched_tables, delta_ctl.dependency_violations;
DROP TABLE IF EXISTS delta_stage.auth_component_operation;
DROP TABLE IF EXISTS delta_stage.auth_processing;
DROP TABLE IF EXISTS delta_diff.auth_component_operation_class;
DROP TABLE IF EXISTS delta_diff.auth_processing_class;
DROP TABLE IF EXISTS delta_map.auth_processing_id_map;
TRUNCATE public.auth_component_operation, public.auth_processing, public.corporation;

CREATE UNLOGGED TABLE delta_stage.auth_processing (LIKE public.auth_processing INCLUDING DEFAULTS);
ALTER TABLE delta_stage.auth_processing ADD COLUMN _delta_row_id bigint GENERATED ALWAYS AS IDENTITY;

CREATE UNLOGGED TABLE delta_stage.auth_component_operation (LIKE public.auth_component_operation INCLUDING DEFAULTS);
ALTER TABLE delta_stage.auth_component_operation ADD COLUMN _delta_row_id bigint GENERATED ALWAYS AS IDENTITY;

INSERT INTO delta_ctl.table_config(table_name, load_phase)
VALUES ('auth_processing', 50), ('auth_component_operation', 60);

SELECT delta_ctl.complete_table_config();

INSERT INTO public.corporation(corp_num) VALUES (:corp_num);

-- One staged auth_processing row matches local id=100; local id=999 is unrelated scope.
INSERT INTO public.auth_processing(id, corp_num, flow_name, environment, operation, operation_scope, attempt_key, mig_batch_id, processed_status, last_modified)
VALUES
  (100, :corp_num, :auth_flow, :env, :op, :scope, 'attempt-1', NULL, :completed, :ts),
  (999, :corp_num, :auth_flow, :env, :op, :scope, 'unrelated', NULL, :completed, :ts);

INSERT INTO delta_stage.auth_processing(id, corp_num, flow_name, environment, operation, operation_scope, attempt_key, mig_batch_id, processed_status, last_modified)
VALUES
  (10, :corp_num, :auth_flow, :env, :op, :scope, 'attempt-1', NULL, :completed, :ts);

-- Local row 200 matches staged row 20. Row 201 is local-only under the matched parent.
-- Row 299 is under an unrelated local parent and should not be counted by scoped LOCAL_ONLY.
INSERT INTO public.auth_component_operation(id, auth_processing_id, component_name, operation, status, payload)
VALUES
  (200, 100, :accounts, :op, :completed, :ok_payload),
  (201, 100, 'contacts', :op, :completed, :ok_payload),
  (299, 999, :accounts, :op, :completed, '{"unrelated":true}');

INSERT INTO delta_stage.auth_component_operation(id, auth_processing_id, component_name, operation, status, payload)
VALUES
  (20, 10, :accounts, :op, :completed, :ok_payload);

SELECT delta_ctl.classify_table('auth_processing');
SELECT delta_ctl.classify_table('auth_component_operation');
