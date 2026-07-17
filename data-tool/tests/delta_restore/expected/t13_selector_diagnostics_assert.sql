DO $$
BEGIN
  IF (SELECT count(*) FROM delta_ctl.selection_diagnostics WHERE problem = 'KIND_UNSUPPORTED') <> 2 THEN
    RAISE EXCEPTION 'expected two KIND_UNSUPPORTED diagnostics';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM delta_ctl.selection_diagnostics
                 WHERE source_line = 12 AND problem = 'CLASS_NOT_INCLUDED') THEN
    RAISE EXCEPTION 'expected CLASS_NOT_INCLUDED diagnostic';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM delta_ctl.selection_diagnostics
                 WHERE source_line = 13 AND problem = 'NO_MATCH' AND matched = 0) THEN -- NOSONAR
    RAISE EXCEPTION 'expected NO_MATCH diagnostic';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM delta_ctl.selection_diagnostics
                 WHERE source_line = 14 AND problem = 'NO_MATCH' AND matched = 0) THEN
    RAISE EXCEPTION 'expected --only-corps to reduce selector to NO_MATCH';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM delta_ctl.selection_diagnostics
                 WHERE source_line = 15 AND problem IS NULL AND matched = 1) THEN
    RAISE EXCEPTION 'expected parent-derived auth component corp selector match';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM delta_ctl.selection_diagnostics
                 WHERE source_line = 16 AND problem IS NULL AND matched = 1) THEN
    RAISE EXCEPTION 'expected PK-less row selector match';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM delta_ctl.selection_diagnostics
                 WHERE source_line = 17 AND problem = 'NO_MATCH' AND matched = 0) THEN
    RAISE EXCEPTION 'expected absent staged table to produce NO_MATCH';
  END IF;

  DELETE FROM delta_ctl.row_selection WHERE source_line NOT IN (15, 16);
  PERFORM delta_ctl.stamp_selection();
  IF NOT EXISTS (SELECT 1 FROM delta_diff.auth_component_operation_class WHERE selected) THEN
    RAISE EXCEPTION 'expected parent-derived auth component corp selector to stamp row';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM delta_diff.email_domain_groups_class WHERE selected) THEN
    RAISE EXCEPTION 'expected PK-less row selector to stamp row';
  END IF;
END $$;
