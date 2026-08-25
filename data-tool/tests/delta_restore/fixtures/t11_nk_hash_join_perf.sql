-- Synthetic-volume SQL smoke for null-safe hash-accelerated natural-key matching.
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

-- Local: 50k non-null keys plus one NULL key. The NULL key must match the
-- staged NULL key below via the null-safe NK residual, not become LOCAL_ONLY/NEW.
INSERT INTO public.bar_corps(identifier, notes)
SELECT 'BC' || lpad(g::text, 7, '0'),
       CASE WHEN g <= 25000 THEN 'same-' || g ELSE 'local-' || g END
FROM generate_series(1, 50000) AS g;
INSERT INTO public.bar_corps(identifier, notes)
VALUES (NULL, 'local-null');

-- Staged: 25k unchanged, 15k changed, 10k new, plus one changed NULL-key match.
INSERT INTO delta_stage.bar_corps(identifier, notes)
SELECT 'BC' || lpad(g::text, 7, '0'), 'same-' || g
FROM generate_series(1, 25000) AS g;

INSERT INTO delta_stage.bar_corps(identifier, notes)
SELECT 'BC' || lpad(g::text, 7, '0'), 'stage-' || g
FROM generate_series(25001, 40000) AS g;

INSERT INTO delta_stage.bar_corps(identifier, notes)
SELECT 'BC' || lpad(g::text, 7, '0'), 'new-' || g
FROM generate_series(50001, 60000) AS g;

INSERT INTO delta_stage.bar_corps(identifier, notes)
VALUES (NULL, 'stage-null');

ANALYZE public.bar_corps;
ANALYZE delta_stage.bar_corps;

CREATE TEMP TABLE t11_nk_hash_join_perf_timing(elapsed_ms numeric NOT NULL);

DO $$
DECLARE
  c_table_name CONSTANT text := 'bar_corps';
  v_started timestamptz := clock_timestamp();
BEGIN
  PERFORM delta_ctl.classify_nk_table(c_table_name);
  PERFORM delta_ctl.record_class_counts(c_table_name);
  PERFORM delta_ctl.record_local_only_count(c_table_name);
  INSERT INTO t11_nk_hash_join_perf_timing(elapsed_ms)
  VALUES (EXTRACT(epoch FROM clock_timestamp() - v_started) * 1000.0);
END $$;
