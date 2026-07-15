DO $$
DECLARE
  v_class text;
  v_reason text;
BEGIN
  SELECT class, block_reason INTO v_class, v_reason
  FROM delta_diff.mig_batch_class
  LIMIT 1;

  IF v_class <> 'BLOCKED_FK' THEN
    RAISE EXCEPTION 'expected mig_batch BLOCKED_FK, got class=% reason=%', v_class, v_reason;
  END IF;

  IF v_reason IS NULL OR v_reason NOT LIKE '%mig_group parent%' THEN
    RAISE EXCEPTION 'expected preserved-parent block reason, got %', v_reason;
  END IF;
END $$;
