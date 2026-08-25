-- Focused SQL smoke for unenforced natural-key ambiguity detection.
-- Assumes 00_install.sql, 10_functions.sql, and minimal_schema.sql have already run.

TRUNCATE delta_ctl.table_config, delta_ctl.run_counts, delta_ctl.apply_counts,
  delta_ctl.touched_tables, delta_ctl.dependency_violations;
DROP TABLE IF EXISTS delta_stage.bar_corps;
DROP TABLE IF EXISTS delta_diff.bar_corps_class;
DROP TABLE IF EXISTS delta_map.bar_corps_id_map;
TRUNCATE public.bar_corps;

CREATE UNLOGGED TABLE delta_stage.bar_corps (LIKE public.bar_corps INCLUDING DEFAULTS);
ALTER TABLE delta_stage.bar_corps ADD COLUMN _delta_row_id bigint GENERATED ALWAYS AS IDENTITY;

INSERT INTO delta_ctl.table_config(table_name, load_phase)
VALUES ('bar_corps', 10);

SELECT delta_ctl.complete_table_config();

-- Duplicate staged unenforced NK rows must remain AMBIGUOUS_NK after typed-key rewrite.
INSERT INTO delta_stage.bar_corps(identifier, notes)
VALUES ('BC0000001', 'stage-a'), ('BC0000001', 'stage-b');

SELECT delta_ctl.classify_table('bar_corps');
