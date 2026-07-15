-- Focused SQL smoke for preserved-parent FK blocking.
-- Assumes 00_install.sql, 10_functions.sql, and minimal_schema.sql have already run.

CREATE UNLOGGED TABLE delta_stage.mig_group (LIKE public.mig_group INCLUDING DEFAULTS);
ALTER TABLE delta_stage.mig_group ADD COLUMN _delta_row_id bigint GENERATED ALWAYS AS IDENTITY;

CREATE UNLOGGED TABLE delta_stage.mig_batch (LIKE public.mig_batch INCLUDING DEFAULTS);
ALTER TABLE delta_stage.mig_batch ADD COLUMN _delta_row_id bigint GENERATED ALWAYS AS IDENTITY;

INSERT INTO delta_ctl.table_config(table_name, load_phase)
VALUES ('mig_group', 20), ('mig_batch', 30);

SELECT delta_ctl.complete_table_config();

-- The child references a staged/local parent ID that does not exist and is not pending NEW.
INSERT INTO delta_stage.mig_batch(id, mig_group_id, name, target_environment)
VALUES (10, 999, 'batch-with-missing-parent', 'dev');

SELECT delta_ctl.classify_table('mig_group');
SELECT delta_ctl.classify_table('mig_batch');
