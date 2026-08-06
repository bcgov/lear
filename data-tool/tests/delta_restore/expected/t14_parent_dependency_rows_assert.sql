DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM delta_ctl.dependency_violations
    WHERE child_table = 'mig_batch' AND parent_table = 'mig_group'
      AND row_count = 1 AND sample_ids = '200'
  ) THEN
    RAISE EXCEPTION 'expected dependency violation with child sample id 200';
  END IF;
  UPDATE delta_diff.mig_group_class
  SET selected = true
  WHERE staged_pk = 100;
  PERFORM delta_ctl.validate_dependencies();
  IF EXISTS (SELECT 1 FROM delta_ctl.dependency_violations) THEN
    RAISE EXCEPTION 'expected dependency validation to pass after selecting parent';
  END IF;
END $$;
