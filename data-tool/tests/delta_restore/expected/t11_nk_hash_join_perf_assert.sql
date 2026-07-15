\if :{?t11_nk_hash_join_perf_max_ms}
\else
\set t11_nk_hash_join_perf_max_ms 60000
\endif

CREATE TEMP TABLE t11_nk_hash_join_perf_settings(max_ms numeric NOT NULL);
INSERT INTO t11_nk_hash_join_perf_settings(max_ms)
VALUES (:t11_nk_hash_join_perf_max_ms);

DO $$
DECLARE
  v_elapsed_ms numeric;
  v_max_ms numeric;
  v_unchanged bigint;
  v_changed bigint;
  v_new bigint;
  v_local_only bigint;
  v_null_class text;
  v_null_local_ctid tid;
  v_null_changed_cols text[];
  v_cross_type_hash_match boolean;
BEGIN
  SELECT max_ms INTO v_max_ms
  FROM t11_nk_hash_join_perf_settings
  LIMIT 1;

  IF v_max_ms IS NULL OR v_max_ms <= 0 THEN
    RAISE EXCEPTION 'expected positive t11 max runtime threshold, got %', v_max_ms;
  END IF;

  SELECT elapsed_ms INTO v_elapsed_ms
  FROM t11_nk_hash_join_perf_timing
  LIMIT 1;

  IF v_elapsed_ms IS NULL THEN
    RAISE EXCEPTION 'expected t11 elapsed timing row';
  END IF;

  -- Generous, configurable ceiling: hash-accelerated NK classification should be
  -- comfortably below this for ~50k local + ~50k staged rows; nested-loop regressions
  -- should fail without making slower CI hosts flaky. Override with psql variable
  -- t11_nk_hash_join_perf_max_ms when needed.
  IF v_elapsed_ms > v_max_ms THEN
    RAISE EXCEPTION 'expected t11 NK hash smoke under % ms, got % ms', v_max_ms, v_elapsed_ms;
  END IF;

  EXECUTE format('SELECT (%s) = (%s)',
    delta_ctl.nk_hash_expr(ARRAY['5::integer']),
    delta_ctl.nk_hash_expr(ARRAY['5::bigint']))
  INTO v_cross_type_hash_match;

  IF v_cross_type_hash_match IS DISTINCT FROM true THEN
    RAISE EXCEPTION 'expected NK hash equality for integer and bigint jsonb rendering';
  END IF;

  SELECT count(*) INTO v_unchanged
  FROM delta_diff.bar_corps_class
  WHERE class = 'UNCHANGED';

  SELECT count(*) INTO v_changed
  FROM delta_diff.bar_corps_class
  WHERE class = 'CHANGED';

  SELECT count(*) INTO v_new
  FROM delta_diff.bar_corps_class
  WHERE class = 'NEW';

  SELECT row_count INTO v_local_only
  FROM delta_ctl.run_counts
  WHERE table_name = 'bar_corps'
    AND count_name = 'LOCAL_ONLY';

  IF v_unchanged <> 25000 THEN
    RAISE EXCEPTION 'expected bar_corps UNCHANGED=25000, got %', v_unchanged;
  END IF;

  IF v_changed <> 15001 THEN
    RAISE EXCEPTION 'expected bar_corps CHANGED=15001 including NULL-key match, got %', v_changed;
  END IF;

  IF v_new <> 10000 THEN
    RAISE EXCEPTION 'expected bar_corps NEW=10000, got %', v_new;
  END IF;

  IF COALESCE(v_local_only, -1) <> 10000 THEN
    RAISE EXCEPTION 'expected bar_corps LOCAL_ONLY=10000, got %', v_local_only;
  END IF;

  SELECT d.class, d.local_ctid, d.changed_cols
  INTO v_null_class, v_null_local_ctid, v_null_changed_cols
  FROM delta_diff.bar_corps_class d
  JOIN delta_stage.bar_corps s ON s._delta_row_id = d._delta_row_id
  WHERE s.identifier IS NULL;

  IF v_null_class <> 'CHANGED' OR v_null_local_ctid IS NULL THEN
    RAISE EXCEPTION 'expected staged NULL identifier to match local NULL as CHANGED, got class=% local_ctid=%',
      v_null_class, v_null_local_ctid;
  END IF;

  IF v_null_changed_cols IS DISTINCT FROM ARRAY['notes']::text[] THEN
    RAISE EXCEPTION 'expected NULL-key match changed_cols={notes}, got %', v_null_changed_cols;
  END IF;
END $$;
