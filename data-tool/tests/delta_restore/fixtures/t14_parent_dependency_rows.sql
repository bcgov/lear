-- Selected child with excluded NEW parent produces persisted sample_ids.
TRUNCATE delta_ctl.table_config, delta_ctl.run_counts, delta_ctl.selection,
  delta_ctl.row_selection, delta_ctl.selection_diagnostics, delta_ctl.apply_counts,
  delta_ctl.touched_tables, delta_ctl.dependency_violations;
DROP SCHEMA delta_stage CASCADE; DROP SCHEMA delta_map CASCADE; DROP SCHEMA delta_diff CASCADE;
CREATE SCHEMA delta_stage; CREATE SCHEMA delta_map; CREATE SCHEMA delta_diff;

CREATE UNLOGGED TABLE delta_stage.mig_group (LIKE public.mig_group INCLUDING DEFAULTS);
ALTER TABLE delta_stage.mig_group ADD COLUMN _delta_row_id bigint GENERATED ALWAYS AS IDENTITY;
CREATE UNLOGGED TABLE delta_stage.mig_batch (LIKE public.mig_batch INCLUDING DEFAULTS);
ALTER TABLE delta_stage.mig_batch ADD COLUMN _delta_row_id bigint GENERATED ALWAYS AS IDENTITY;
INSERT INTO delta_ctl.table_config(table_name, load_phase) VALUES ('mig_group', 20), ('mig_batch', 30);
SELECT delta_ctl.complete_table_config();
SELECT delta_ctl.create_class_table('mig_group');
SELECT delta_ctl.create_class_table('mig_batch');
INSERT INTO delta_stage.mig_group(id, name) VALUES (100, 'parent');
INSERT INTO delta_stage.mig_batch(id, mig_group_id, name) VALUES (200, 100, 'child');
INSERT INTO delta_diff.mig_group_class(_delta_row_id, staged_pk, class, selected)
VALUES (1, 100, 'NEW', false);
INSERT INTO delta_diff.mig_batch_class(_delta_row_id, staged_pk, class, selected)
VALUES (1, 200, 'NEW', true);
SELECT delta_ctl.validate_dependencies();
