-- Value rendering, old-to-new diffs, escaping, and detail truncation.
TRUNCATE delta_ctl.table_config, delta_ctl.run_counts, delta_ctl.selection,
  delta_ctl.row_selection, delta_ctl.selection_diagnostics, delta_ctl.apply_counts,
  delta_ctl.touched_tables, delta_ctl.dependency_violations;
DROP SCHEMA delta_stage CASCADE; DROP SCHEMA delta_map CASCADE; DROP SCHEMA delta_diff CASCADE;
CREATE SCHEMA delta_stage; CREATE SCHEMA delta_map; CREATE SCHEMA delta_diff;
TRUNCATE public.bad_emails RESTART IDENTITY;

CREATE UNLOGGED TABLE delta_stage.bad_emails (LIKE public.bad_emails INCLUDING DEFAULTS);
ALTER TABLE delta_stage.bad_emails ADD COLUMN _delta_row_id bigint GENERATED ALWAYS AS IDENTITY;
INSERT INTO delta_ctl.table_config(table_name, load_phase) VALUES ('bad_emails', 10);
SELECT delta_ctl.complete_table_config();
INSERT INTO public.bad_emails(id, email, notes) VALUES (1, 'changed@example.test', 'local old');
INSERT INTO delta_stage.bad_emails(id, email, notes) VALUES
  (1, 'changed@example.test', 'dump new'),
  (2, 'new@example.test', E'tab\tline\nnext\rreturn\\slash'),
  (3, 'newer@example.test', 'third');
SELECT delta_ctl.run_preview_classification();
