DO $$
DECLARE
  v_bad bigint;
BEGIN
  IF (SELECT count(*) FROM public.mig_batch WHERE id = 152) <> 1 THEN
    RAISE EXCEPTION 'expected selected mig_batch parent id 152';
  END IF;
  IF (SELECT count(*) FROM public.mig_corp_account) <> 16
     OR EXISTS (SELECT 1 FROM public.mig_corp_account WHERE id = 23) THEN
    RAISE EXCEPTION 'mig_corp_account row exclusion failed';
  END IF;
  IF (SELECT count(*) FROM public.mig_corp_batch) <> 16
     OR EXISTS (SELECT 1 FROM public.mig_corp_batch WHERE id > 3016) THEN
    RAISE EXCEPTION 'mig_corp_batch range inclusion failed';
  END IF;
  IF (SELECT count(*) FROM public.corp_processing) <> 16
     OR EXISTS (SELECT 1 FROM public.corp_processing WHERE id > 4016) THEN
    RAISE EXCEPTION 'corp_processing range inclusion failed';
  END IF;

  SELECT count(*) INTO v_bad
  FROM delta_ctl.apply_counts
  WHERE expected_count <> affected_count;
  IF v_bad <> 0 THEN
    RAISE EXCEPTION 'expected apply expected_count = affected_count';
  END IF;
  IF NOT EXISTS (
    SELECT 1 FROM delta_ctl.apply_counts
    WHERE table_name = 'mig_batch' AND class = 'NEW'
      AND expected_count = 1 AND affected_count = 1
  ) OR NOT EXISTS (
    SELECT 1 FROM delta_ctl.apply_counts
    WHERE table_name = 'mig_corp_account' AND class = 'NEW'
      AND expected_count = 16 AND affected_count = 16
  ) OR NOT EXISTS (
    SELECT 1 FROM delta_ctl.apply_counts
    WHERE table_name = 'mig_corp_batch' AND class = 'NEW'
      AND expected_count = 16 AND affected_count = 16
  ) OR NOT EXISTS (
    SELECT 1 FROM delta_ctl.apply_counts
    WHERE table_name = 'corp_processing' AND class = 'NEW'
      AND expected_count = 16 AND affected_count = 16
  ) THEN
    RAISE EXCEPTION 'missing expected 1/16/16/16 apply counts';
  END IF;
END $$;
