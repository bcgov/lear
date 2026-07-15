DO $$
DECLARE
  v_ambiguous bigint;
BEGIN
  SELECT count(*) INTO v_ambiguous
  FROM delta_diff.bar_corps_class
  WHERE class = 'AMBIGUOUS_NK';

  IF v_ambiguous <> 2 THEN
    RAISE EXCEPTION 'expected 2 bar_corps AMBIGUOUS_NK rows, got %', v_ambiguous;
  END IF;
END $$;
