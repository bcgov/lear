DO $$
DECLARE
  v_new text;
  v_changed text;
  v_blocked text;
  v_samples text;
  v_control text;
BEGIN
  SELECT delta_ctl.display_value(
           jsonb_build_object('value', E'line\nnext\tcell\rreturn' || chr(27) || 'escape' || chr(1) || 'control'),
           'value', 200)
    INTO v_control;
  IF position(chr(13) in v_control) > 0
     OR position(chr(27) in v_control) > 0
     OR position(chr(1) in v_control) > 0
     OR v_control NOT LIKE '%␤%'
     OR v_control NOT LIKE '%␉%'
     OR v_control NOT LIKE '%␍%'
     OR v_control NOT LIKE '%␛%'
     OR v_control NOT LIKE '%�%' THEN
    RAISE EXCEPTION 'preview display value retained controls or omitted visible markers: %', v_control;
  END IF;

  SELECT string_agg(line, E'\n') INTO v_new
  FROM delta_ctl.render_new_rows_tsv('bad_emails', 1) line; -- NOSONAR
  IF v_new NOT LIKE '%selector_id%' OR v_new NOT LIKE '%# TRUNCATED at 1 rows%'
     OR position(E'tab\\tline\\nnext\\rreturn\\\\slash' in v_new) = 0 THEN
    RAISE EXCEPTION 'NEW detail output missing header, escaping, or truncation: %', v_new;
  END IF;

  SELECT string_agg(line, E'\n') INTO v_changed
  FROM delta_ctl.render_changed_rows_tsv('bad_emails', 10) line;
  IF v_changed NOT LIKE '%local old%' OR v_changed NOT LIKE '%dump new%'
     OR v_changed NOT LIKE '%notes%' THEN
    RAISE EXCEPTION 'CHANGED detail output missing old-to-new values: %', v_changed;
  END IF;

  UPDATE delta_diff.bad_emails_class
  SET class = 'BLOCKED_FK',
      block_reason = E'missing\tparent\nrow\rreturn' || chr(27) || 'escape' || chr(1) || 'control'
  WHERE staged_pk = 3;
  SELECT string_agg(line, E'\n') INTO v_blocked
  FROM delta_ctl.render_blocked_rows_tsv('bad_emails', 10) line;
  IF v_blocked NOT LIKE '%newer@example.test%'
     OR position(E'missing\\tparent\\nrow\\rreturn' in v_blocked) = 0
     OR position(chr(27) in v_blocked) > 0
     OR position(chr(1) in v_blocked) > 0
     OR v_blocked NOT LIKE '%␛%'
     OR v_blocked NOT LIKE '%�%' THEN
    RAISE EXCEPTION 'BLOCKED detail output missing escaping/sanitization: %', v_blocked;
  END IF;

  SELECT string_agg(line, E'\n') INTO v_control
  FROM delta_ctl.render_samples('bad_emails', 'BLOCKED_FK', 10) line;
  IF position(chr(13) in v_control) > 0
     OR position(chr(27) in v_control) > 0
     OR position(chr(1) in v_control) > 0
     OR v_control NOT LIKE '%␍%'
     OR v_control NOT LIKE '%␛%'
     OR v_control NOT LIKE '%�%' THEN
    RAISE EXCEPTION 'preview block reason retained controls or omitted visible markers: %', v_control;
  END IF;

  SELECT string_agg(line, E'\n') INTO v_samples
  FROM delta_ctl.render_samples('bad_emails', 'CHANGED', 10) line; -- NOSONAR
  IF v_samples NOT LIKE '%email=changed@example.test%'
     OR v_samples NOT LIKE '%changed notes: local old → dump new%' THEN
    RAISE EXCEPTION 'enriched sample output missing values/diff: %', v_samples;
  END IF;

  UPDATE delta_stage.bad_emails SET notes = repeat('x', 300) WHERE id = 1;
  UPDATE delta_diff.bad_emails_class
  SET changed_cols = ARRAY['email', 'notes', 'extra_1', 'extra_2', 'extra_3', 'extra_4']
  WHERE staged_pk = 1;
  IF (SELECT count(*) FROM delta_ctl.render_samples('bad_emails', 'CHANGED', 10)) <> 6 THEN
    RAISE EXCEPTION 'expected one sample line plus at most five changed-column lines';
  END IF;
  IF (SELECT max(length(line)) FROM delta_ctl.render_samples('bad_emails', 'CHANGED', 10) line) > 220 THEN
    RAISE EXCEPTION 'expected preview sample lines to be capped at 220 characters';
  END IF;
END $$;
