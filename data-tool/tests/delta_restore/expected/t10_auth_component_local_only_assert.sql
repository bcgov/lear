DO $$
DECLARE
  v_local_only bigint;
BEGIN
  SELECT row_count INTO v_local_only
  FROM delta_ctl.run_counts
  WHERE table_name = 'auth_component_operation'
    AND count_name = 'LOCAL_ONLY';

  IF COALESCE(v_local_only, -1) <> 1 THEN
    RAISE EXCEPTION 'expected auth_component_operation LOCAL_ONLY=1, got %', v_local_only;
  END IF;
END $$;
