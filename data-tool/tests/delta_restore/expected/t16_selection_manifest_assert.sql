DO $$
DECLARE
  v_lines text[];
  v_none_lines text[];
  v_variant_lines text[];
  v_manifest text;
  v_error text;
  v_invalid_value text;
  v_binding_headers integer;
  v_active_count integer;
  v_include_min integer;
  v_include_max integer;
  v_active integer;
  v_wildcard integer;
  v_small_new integer;
  v_small_changed integer;
  v_large_new integer;
  v_large_changed integer;
  v_pointer integer;
  v_pos integer;
  v_generic_count integer;
  v_range_line_count integer;
  v_singleton_line_count integer;
  v_last_range integer;
  v_first_singleton integer;
  v_singleton_ordinals bigint[];
  v_singleton_ordinal_index integer;
  v_exact_count bigint;
  v_exact_distinct bigint;
  v_missing_count bigint;
  v_extra_count bigint;
  c_range_counts_pattern constant text := '#   Range counts:%';
  c_boundary_selector_pattern constant text :=
    '# [selector_limit_boundary] new.rows include=id:%';
BEGIN
  IF EXISTS (
    SELECT 1 FROM delta_ctl.run_metadata WHERE key = 'selector_suggestion_limit' -- NOSONAR
  ) THEN
    RAISE EXCEPTION 'selector limit fixture must begin without metadata to test fallback';
  END IF;

  SELECT array_agg(line ORDER BY ord), string_agg(line, E'\n' ORDER BY ord)
    INTO v_lines, v_manifest
  FROM delta_ctl.render_selection_manifest() WITH ORDINALITY AS manifest(line, ord);

  IF v_lines[1] <> '# delta-selection v2'
     OR v_lines[2] <> '# dump_sha256=manifest-test-sha'
     OR v_lines[3] <> '# staged bad_emails=5 selector_limit_boundary=51 mig_batch=5 mig_group=51 bar_corps=52 corp_processing=106 auth_component_operation=54' THEN
    RAISE EXCEPTION 'v2 binding headers were not emitted first or exactly: %', v_manifest;
  END IF;

  SELECT count(*) INTO v_binding_headers
  FROM unnest(v_lines) line
  WHERE line ~ '^# (dump_sha256=|staged )';
  IF v_binding_headers <> 2 THEN
    RAISE EXCEPTION 'documentation was mistaken for a binding header: %', v_manifest;
  END IF;

  v_active := array_position(v_lines, '# ACTIVE SELECTION');
  v_small_new := array_position(
    v_lines, '# Small NEW sets receive ready-to-uncomment suggestions:'); -- NOSONAR
  v_small_changed := array_position(
    v_lines, '# Small CHANGED sets receive ready-to-uncomment suggestions:'); -- NOSONAR
  v_large_new := array_position(
    v_lines, '# Large NEW sets receive a useful pointer rather than no guidance:');
  v_large_changed := array_position(
    v_lines, '# Large CHANGED sets receive a useful pointer rather than no guidance:');
  v_pointer := array_position(
    v_lines,
    '# Full selector grammar and 13 worked examples: selection_cookbook.txt (this run dir)');
  IF v_active IS NULL OR v_small_new IS NULL OR v_small_changed IS NULL
     OR v_large_new IS NULL OR v_large_changed IS NULL OR v_pointer IS NULL
     OR NOT (v_active < v_small_new
             AND v_small_new < v_small_changed
             AND v_small_changed < v_large_new
             AND v_large_new < v_large_changed
             AND v_large_changed < v_pointer) THEN
    RAISE EXCEPTION 'manifest section order is wrong: %', v_manifest;
  END IF;
  IF v_lines[v_pointer - 1] <> '# ---------------------------------------------------------------------------'
     OR v_lines[v_pointer + 1] <> '# ---------------------------------------------------------------------------' THEN
    RAISE EXCEPTION 'cookbook pointer block does not match the approved shape: %', v_manifest;
  END IF;
  IF array_position(v_lines, '# OPERATOR COOKBOOK') IS NOT NULL
     OR array_position(v_lines, '# 1. Apply all NEW and CHANGED rows for a table:') IS NOT NULL
     OR array_position(
          v_lines,
          '# Classes: new | changed | changed_local_newer (other classes are never applyable).')
        IS NOT NULL THEN
    RAISE EXCEPTION 'manifest still embeds cookbook or grammar reference text: %', v_manifest;
  END IF;

  SELECT count(*), min(strpos(line, 'include=')), max(strpos(line, 'include='))
    INTO v_active_count, v_include_min, v_include_max
  FROM unnest(v_lines) line
  WHERE line ~ '^\[[^]]+\][[:space:]]+include=';
  IF v_active_count <> 8 OR v_include_min <> v_include_max THEN
    RAISE EXCEPTION
      'wildcard/per-table active lines are missing or misaligned: count=% min=% max=% manifest=%',
      v_active_count, v_include_min, v_include_max, v_manifest;
  END IF;

  SELECT ord INTO v_wildcard
  FROM unnest(v_lines) WITH ORDINALITY AS u(line, ord)
  WHERE line LIKE '[*]%' LIMIT 1;
  IF v_lines[v_wildcard] !~ '^\[\*\][[:space:]]+include=new,changed$'
     OR v_lines[v_wildcard + 1] <>
       '# Default selection ([*] new,changed) currently matches 323 rows across 7 tables (new=266 changed=57).' THEN
    RAISE EXCEPTION 'default wildcard or blast-radius total changed: %', v_manifest;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM unnest(v_lines) line
    WHERE line ~ '^\[mig_batch\][[:space:]]+include=new,changed # new=3 changed=2 changed_local_newer=0 parents=mig_group$'
  ) THEN
    RAISE EXCEPTION 'mig_batch active line lacks its preserved parent annotation: %', v_manifest;
  END IF;
  IF NOT EXISTS (
    SELECT 1 FROM unnest(v_lines) line
    WHERE line ~ '^\[corp_processing\][[:space:]]+include=new,changed # new=53 changed=53 changed_local_newer=0 parents=mig_batch$'
  ) THEN
    RAISE EXCEPTION 'corp_processing active line lacks its preserved parent annotation: %', v_manifest;
  END IF;
  IF EXISTS (
    SELECT 1 FROM unnest(v_lines) line
    WHERE line LIKE '[mig_batch]%' AND line LIKE '%external:%'
  ) THEN
    RAISE EXCEPTION 'external FK leaked into parent annotations: %', v_manifest;
  END IF;

  -- Every exact table block begins after an actual blank line. Mixed PK and
  -- PK-less sets also keep range/count pairs adjacent and place one actual blank
  -- line before their separate singleton selectors.
  IF EXISTS (
    SELECT 1
    FROM unnest(v_lines) WITH ORDINALITY AS rendered(line, ord)
    WHERE line ~ '^# \[[^]]+\] Exact (NEW|CHANGED) set:'
      AND (ord < 3
           OR v_lines[(ord - 1)::integer] <> ''
           OR v_lines[(ord - 2)::integer] = '')
  ) THEN
    RAISE EXCEPTION 'an exact table block lacks its leading blank line: %', v_manifest;
  END IF;

  v_pos := array_position(
    v_lines, '# [bad_emails] Exact NEW set: rows=3 singletons=1 ranges=1');
  IF v_pos IS NULL
     OR v_lines[v_pos + 1] <> '# [bad_emails] new.rows include=id:2-3'
     OR v_lines[v_pos + 2] <> '#   Range counts: 2-3 (2 rows)'
     OR v_lines[v_pos + 3] <> ''
     OR v_lines[v_pos + 4] <> '# [bad_emails] new.rows include=id:5' THEN
    RAISE EXCEPTION 'mixed PK NEW exact guidance has the wrong layout: %', v_manifest;
  END IF;
  v_pos := array_position(
    v_lines, '# [mig_batch] Exact NEW set: rows=3 singletons=1 ranges=1');
  IF v_pos IS NULL
     OR v_lines[v_pos + 1] <> '# [mig_batch] new.rows include=row:4-5'
     OR v_lines[v_pos + 2] <> '#   Range counts: 4-5 (2 rows)'
     OR v_lines[v_pos + 3] <> ''
     OR v_lines[v_pos + 4] <> '# [mig_batch] new.rows include=row:8' THEN
    RAISE EXCEPTION 'mixed PK-less NEW exact guidance has the wrong layout: %', v_manifest;
  END IF;
  v_pos := array_position(
    v_lines, '# [bad_emails] Exact CHANGED set: rows=2 singletons=2 ranges=0');
  IF v_pos IS NULL
     OR v_lines[v_pos + 1] <> '# [bad_emails] changed.rows include=id:7,9'
     OR v_lines[v_pos + 2] LIKE c_range_counts_pattern THEN
    RAISE EXCEPTION 'singleton-only CHANGED exact guidance has the wrong layout: %', v_manifest;
  END IF;
  v_pos := array_position(
    v_lines, '# [mig_batch] Exact CHANGED set: rows=2 singletons=0 ranges=1');
  IF v_pos IS NULL
     OR v_lines[v_pos + 1] <> '# [mig_batch] changed.rows include=row:10-11'
     OR v_lines[v_pos + 2] <> '#   Range counts: 10-11 (2 rows)' THEN
    RAISE EXCEPTION 'range-only PK-less CHANGED guidance has the wrong layout: %', v_manifest;
  END IF;

  -- The inclusive default boundary remains exact and forces both categories to wrap.
  IF array_position(
       v_lines,
       '# [selector_limit_boundary] Exact NEW set: rows=50 singletons=40 ranges=5')
       IS NULL THEN
    RAISE EXCEPTION '50-row exact summary is missing: %', v_manifest;
  END IF;
  SELECT
    count(*) FILTER (WHERE line LIKE '%-%'),
    count(*) FILTER (WHERE line NOT LIKE '%-%'),
    max(ord) FILTER (WHERE line LIKE '%-%'),
    min(ord) FILTER (WHERE line NOT LIKE '%-%')
    INTO v_range_line_count, v_singleton_line_count, v_last_range, v_first_singleton
  FROM unnest(v_lines) WITH ORDINALITY AS rendered(line, ord)
  WHERE line LIKE c_boundary_selector_pattern;
  IF v_range_line_count <= 1 OR v_singleton_line_count <= 8
     OR v_last_range >= v_first_singleton
     OR v_lines[v_first_singleton - 1] <> ''
     OR v_lines[v_first_singleton - 2] NOT LIKE c_range_counts_pattern THEN
    RAISE EXCEPTION
      'boundary selectors did not wrap with all ranges before singletons: ranges=% singletons=% manifest=%',
      v_range_line_count, v_singleton_line_count, v_manifest;
  END IF;

  -- Long singleton lists form visual paragraphs of four selector lines. There
  -- is exactly one actual blank line before selector lines 5, 9, 13, and so on.
  SELECT array_agg(ord ORDER BY ord)
    INTO v_singleton_ordinals
  FROM unnest(v_lines) WITH ORDINALITY AS rendered(line, ord)
  WHERE line LIKE c_boundary_selector_pattern
    AND line NOT LIKE '%-%';
  FOR v_singleton_ordinal_index IN 2..cardinality(v_singleton_ordinals) LOOP
    IF v_singleton_ordinals[v_singleton_ordinal_index]
         - v_singleton_ordinals[v_singleton_ordinal_index - 1]
       <> (CASE WHEN mod(v_singleton_ordinal_index - 1, 4) = 0 THEN 2 ELSE 1 END) THEN
      RAISE EXCEPTION
        'long singleton selector paragraphs do not break every four lines: ordinals=% manifest=%',
        v_singleton_ordinals, v_manifest;
    END IF;
  END LOOP;

  -- Every wrapped line is a complete selector. Categories never mix, and the soft
  -- 120-character cap is exceeded only for one indivisible selector token.
  IF EXISTS (
    SELECT 1
    FROM unnest(v_lines) line
    WHERE line ~ '^# \[[^]]+\] (new|changed)\.rows include=(id|row):'
      AND length(line) > 120
      AND cardinality(string_to_array(
            regexp_replace(line, '^.*include=(id|row):', ''), ',')) <> 1
  ) OR EXISTS (
    SELECT 1 FROM unnest(v_lines) line
    WHERE line LIKE c_range_counts_pattern AND length(line) > 120
  ) OR EXISTS (
    SELECT 1
    FROM unnest(v_lines) line
    CROSS JOIN LATERAL unnest(string_to_array(
      split_part(line, 'include=id:', 2), ',')) AS token -- NOSONAR
    WHERE line LIKE c_boundary_selector_pattern
    GROUP BY line
    HAVING bool_or(position('-' in token) > 0)
       AND bool_or(position('-' in token) = 0)
  ) OR EXISTS (
    SELECT 1 FROM unnest(v_lines) line
    WHERE right(line, 1) = E'\\'
       OR line ~ '^#[[:space:]]+include=(id|row):'
  ) THEN
    RAISE EXCEPTION 'wrapped selector grammar, category separation, or line cap failed: %',
      v_manifest;
  END IF;

  -- Each wrapped range line is followed immediately by the annotation derived
  -- from exactly that line's tokens, in the same order.
  IF EXISTS (
    SELECT 1
    FROM unnest(v_lines) WITH ORDINALITY AS rendered(line, ord)
    CROSS JOIN LATERAL (
      SELECT '#   Range counts: ' ||
             string_agg(
               token || ' (' ||
               (split_part(token, '-', 2)::bigint
                - split_part(token, '-', 1)::bigint + 1)::text ||
               ' rows)',
               ', ' ORDER BY token_ord) AS expected
      FROM unnest(string_to_array(
        split_part(rendered.line, 'include=id:', 2), ','))
        WITH ORDINALITY AS range_token(token, token_ord)
    ) annotation
    WHERE rendered.line LIKE '# [selector_limit_boundary] new.rows include=id:%-%'
      AND v_lines[(rendered.ord + 1)::integer] <> annotation.expected
  ) THEN
    RAISE EXCEPTION 'a wrapped range annotation is absent or mismatched: %', v_manifest;
  END IF;

  -- Expanding every repeated line must reconstruct the classified exact set once:
  -- no omissions, extras, or duplicated tokens across chunks.
  WITH selector_lines AS (
    SELECT split_part(line, 'include=id:', 2) AS payload
    FROM unnest(v_lines) line
    WHERE line LIKE c_boundary_selector_pattern
  ), tokens AS (
    SELECT token
    FROM selector_lines
    CROSS JOIN LATERAL unnest(string_to_array(payload, ',')) AS parsed(token)
  ), expanded AS (
    SELECT expanded_id AS id
    FROM tokens
    CROSS JOIN LATERAL generate_series(
      split_part(token, '-', 1)::bigint,
      CASE WHEN position('-' in token) > 0
           THEN split_part(token, '-', 2)::bigint
           ELSE token::bigint
      END
    ) AS ids(expanded_id)
  ), source AS (
    SELECT s.id
    FROM delta_stage.selector_limit_boundary s
    JOIN delta_diff.selector_limit_boundary_class d
      ON d._delta_row_id = s._delta_row_id
    WHERE d.class = 'NEW'
  )
  SELECT
    (SELECT count(*) FROM expanded),
    (SELECT count(DISTINCT id) FROM expanded),
    (SELECT count(*) FROM (SELECT id FROM source EXCEPT SELECT id FROM expanded) q),
    (SELECT count(*) FROM (SELECT id FROM expanded EXCEPT SELECT id FROM source) q)
    INTO v_exact_count, v_exact_distinct, v_missing_count, v_extra_count;
  IF v_exact_count <> 50 OR v_exact_distinct <> 50
     OR v_missing_count <> 0 OR v_extra_count <> 0 THEN
    RAISE EXCEPTION
      'repeated selector lines do not union to the original exact set: count=% distinct=% missing=% extra=% manifest=%',
      v_exact_count, v_exact_distinct, v_missing_count, v_extra_count, v_manifest;
  END IF;

  -- The paragraph threshold is strict: exactly eight singleton lines remain
  -- contiguous, while nine lines break immediately before lines 5 and 9.
  UPDATE delta_stage.selector_limit_boundary
  SET id = 4000000000000000000::bigint + _delta_row_id * 2;
  UPDATE delta_diff.selector_limit_boundary_class
  SET class = CASE WHEN _delta_row_id <= 24 THEN 'NEW' ELSE 'UNCHANGED' END; -- NOSONAR
  UPDATE delta_ctl.run_counts
  SET row_count = 24
  WHERE table_name = 'selector_limit_boundary' AND count_name = 'NEW'; -- NOSONAR
  SELECT array_agg(line ORDER BY ord)
    INTO v_variant_lines
  FROM delta_ctl.render_selection_manifest() WITH ORDINALITY AS manifest(line, ord);
  SELECT array_agg(ord ORDER BY ord)
    INTO v_singleton_ordinals
  FROM unnest(v_variant_lines) WITH ORDINALITY AS rendered(line, ord)
  WHERE line LIKE c_boundary_selector_pattern;
  IF cardinality(v_singleton_ordinals) <> 8 OR EXISTS (
    SELECT 1
    FROM generate_subscripts(v_singleton_ordinals, 1) AS indexes(i)
    WHERE i > 1
      AND v_singleton_ordinals[i] - v_singleton_ordinals[i - 1] <> 1
  ) THEN
    RAISE EXCEPTION 'exactly eight singleton lines received paragraph spacing: ordinals=% manifest=%',
      v_singleton_ordinals, array_to_string(v_variant_lines, E'\n');
  END IF;

  UPDATE delta_diff.selector_limit_boundary_class
  SET class = CASE WHEN _delta_row_id <= 27 THEN 'NEW' ELSE 'UNCHANGED' END;
  UPDATE delta_ctl.run_counts
  SET row_count = 27
  WHERE table_name = 'selector_limit_boundary' AND count_name = 'NEW'; -- NOSONAR
  SELECT array_agg(line ORDER BY ord)
    INTO v_variant_lines
  FROM delta_ctl.render_selection_manifest() WITH ORDINALITY AS manifest(line, ord);
  SELECT array_agg(ord ORDER BY ord)
    INTO v_singleton_ordinals
  FROM unnest(v_variant_lines) WITH ORDINALITY AS rendered(line, ord)
  WHERE line LIKE c_boundary_selector_pattern;
  IF cardinality(v_singleton_ordinals) <> 9 OR EXISTS (
    SELECT 1
    FROM generate_subscripts(v_singleton_ordinals, 1) AS indexes(i)
    WHERE i > 1
      AND v_singleton_ordinals[i] - v_singleton_ordinals[i - 1]
          <> (CASE WHEN mod(i - 1, 4) = 0 THEN 2 ELSE 1 END)
  ) THEN
    RAISE EXCEPTION 'nine singleton lines lack paragraph spacing before lines 5 and 9: ordinals=% manifest=%',
      v_singleton_ordinals, array_to_string(v_variant_lines, E'\n');
  END IF;

  -- Restore the inclusive 50-row fixture for all subsequent limit variants.
  UPDATE delta_stage.selector_limit_boundary
  SET id = CASE
             WHEN _delta_row_id <= 10 THEN
               100000000000000::bigint
               + ((_delta_row_id - 1) / 2) * 3
               + ((_delta_row_id - 1) % 2)
             WHEN _delta_row_id <= 50 THEN
               2000000000000000000::bigint + (_delta_row_id - 11) * 2
             ELSE 3000000000000000000::bigint
           END;
  UPDATE delta_diff.selector_limit_boundary_class
  SET class = CASE WHEN _delta_row_id <= 50 THEN 'NEW' ELSE 'UNCHANGED' END;
  UPDATE delta_ctl.run_counts
  SET row_count = 50
  WHERE table_name = 'selector_limit_boundary' AND count_name = 'NEW'; -- NOSONAR

  IF EXISTS (
    SELECT 1 FROM unnest(v_lines) line
    WHERE line LIKE '# [%] changed_local_newer.rows include=%'
  ) THEN
    RAISE EXCEPTION 'CHANGED_LOCAL_NEWER received unsafe ready-to-uncomment guidance: %', v_manifest;
  END IF;

  v_pos := array_position(
    v_lines, '# corp_processing has 53 CHANGED rows; choose selector_id or corp values from:');
  IF v_pos IS NULL
     OR v_lines[v_pos + 1] <> '# details/corp_processing.changed.tsv'
     OR v_lines[v_pos + 2] <> '# Example syntax:'
     OR v_lines[v_pos + 3] <> '# [corp_processing] changed.rows include=id:100,200-210'
     OR v_lines[v_pos + 4] <> '# [corp_processing] changed.rows include=corp:BC0000001,BC0000002'
     OR v_lines[v_pos + 5] <> '#' THEN
    RAISE EXCEPTION 'large CHANGED guidance does not match the approved shape: %', v_manifest;
  END IF;
  IF NOT (v_large_changed < v_pos AND v_pos < v_pointer) THEN
    RAISE EXCEPTION 'large CHANGED guidance is not in its grouped section: %', v_manifest;
  END IF;

  v_pos := array_position(
    v_lines, '# auth_component_operation has 54 NEW rows; choose selector_id from:');
  IF v_pos IS NULL
     OR v_lines[v_pos + 1] <> '# details/auth_component_operation.new.tsv'
     OR v_lines[v_pos + 3] <> '# [auth_component_operation] new.rows include=id:100,200-210'
     OR v_lines[v_pos + 4] <>
       '# corp: selectors are also supported via the staged auth_processing parent:'
     OR v_lines[v_pos + 5] <>
       '# [auth_component_operation] new.rows include=corp:BC0000001,BC0000002' THEN
    RAISE EXCEPTION 'large NEW auth guidance lost its parent-derived corp caveat: %', v_manifest;
  END IF;

  IF EXISTS (
    SELECT 1 FROM unnest(v_lines) line
    WHERE line NOT LIKE '#%' AND line LIKE '%.rows %'
  ) THEN
    RAISE EXCEPTION 'rendered manifest contains an uncommented row selector: %', v_manifest;
  END IF;

  -- Negative values still receive a summary but suppress every exact selector.
  UPDATE delta_stage.bad_emails SET id = -2 WHERE _delta_row_id = 1;
  SELECT array_agg(line ORDER BY ord)
    INTO v_variant_lines
  FROM delta_ctl.render_selection_manifest() WITH ORDINALITY AS manifest(line, ord);
  IF array_position(
       v_variant_lines,
       '# [bad_emails] Exact NEW set: rows=3 singletons=3 ranges=0') IS NULL
     OR array_position(
       v_variant_lines,
       '# [bad_emails] Exact NEW selector unavailable for this small set.') IS NULL
     OR array_position(
       v_variant_lines,
       '#   Review details/bad_emails.new.tsv; negative id: values are outside the selector grammar.')
       IS NULL
     OR EXISTS (
       SELECT 1 FROM unnest(v_variant_lines) line
       WHERE line LIKE '# [bad_emails] new.rows include=id:%'
     ) THEN
    RAISE EXCEPTION 'negative selector fallback is incomplete or unsafe: %',
      array_to_string(v_variant_lines, E'\n');
  END IF;
  UPDATE delta_stage.bad_emails SET id = 2 WHERE _delta_row_id = 1;

  -- A singleton suggestion has no redundant range-count comment.
  UPDATE delta_diff.bad_emails_class
  SET class = 'UNCHANGED'
  WHERE _delta_row_id = 5;
  UPDATE delta_ctl.run_counts
  SET row_count = 1
  WHERE table_name = 'bad_emails' AND count_name = 'CHANGED'; -- NOSONAR
  SELECT array_agg(line ORDER BY ord)
    INTO v_variant_lines
  FROM delta_ctl.render_selection_manifest() WITH ORDINALITY AS manifest(line, ord);
  v_pos := array_position(
    v_variant_lines,
    '# [bad_emails] Exact CHANGED set: rows=1 singletons=1 ranges=0');
  IF v_pos IS NULL
     OR v_variant_lines[v_pos + 1] <> '# [bad_emails] changed.rows include=id:7'
     OR v_variant_lines[v_pos + 2] LIKE c_range_counts_pattern THEN
    RAISE EXCEPTION 'singleton suggestion received range-count guidance: %',
      array_to_string(v_variant_lines, E'\n');
  END IF;
  UPDATE delta_diff.bad_emails_class
  SET class = 'CHANGED'
  WHERE _delta_row_id = 5;
  UPDATE delta_ctl.run_counts
  SET row_count = 2
  WHERE table_name = 'bad_emails' AND count_name = 'CHANGED'; -- NOSONAR

  -- Missing selector-limit metadata falls back to 50: 50 is exact, 51 is generic.
  UPDATE delta_diff.selector_limit_boundary_class
  SET class = 'NEW'
  WHERE _delta_row_id = 51;
  UPDATE delta_ctl.run_counts
  SET row_count = 51
  WHERE table_name = 'selector_limit_boundary' AND count_name = 'NEW'; -- NOSONAR
  SELECT array_agg(line ORDER BY ord)
    INTO v_variant_lines
  FROM delta_ctl.render_selection_manifest() WITH ORDINALITY AS manifest(line, ord);
  v_small_new := array_position(
    v_variant_lines, '# Small NEW sets receive ready-to-uncomment suggestions:');
  v_small_changed := array_position(
    v_variant_lines, '# Small CHANGED sets receive ready-to-uncomment suggestions:');
  IF EXISTS (
       SELECT 1
       FROM unnest(v_variant_lines) WITH ORDINALITY AS rendered(line, ord)
       WHERE ord > v_small_new AND ord < v_small_changed
         AND (line LIKE '# [selector_limit_boundary] Exact NEW set:%'
              OR line LIKE c_boundary_selector_pattern)
     )
     OR array_position(
       v_variant_lines,
       '# selector_limit_boundary has 51 NEW rows; choose selector_id from:') IS NULL THEN
    RAISE EXCEPTION 'missing selector-limit metadata did not use the 50/51 boundary: %',
      array_to_string(v_variant_lines, E'\n');
  END IF;

  -- A custom limit applies to both complementary renderer branches.
  INSERT INTO delta_ctl.run_metadata(key, value)
  VALUES ('selector_suggestion_limit', '2')
  ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value;
  SELECT array_agg(line ORDER BY ord)
    INTO v_variant_lines
  FROM delta_ctl.render_selection_manifest() WITH ORDINALITY AS manifest(line, ord);
  v_small_new := array_position(
    v_variant_lines, '# Small NEW sets receive ready-to-uncomment suggestions:');
  v_small_changed := array_position(
    v_variant_lines, '# Small CHANGED sets receive ready-to-uncomment suggestions:');
  IF array_position(
       v_variant_lines,
       '# [bad_emails] Exact CHANGED set: rows=2 singletons=2 ranges=0') IS NULL
     OR array_position(v_variant_lines, '# [bad_emails] changed.rows include=id:7,9') IS NULL
     OR EXISTS (
       SELECT 1
       FROM unnest(v_variant_lines) WITH ORDINALITY AS rendered(line, ord)
       WHERE ord > v_small_new AND ord < v_small_changed
         AND (line LIKE '# [bad_emails] Exact NEW set:%'
              OR line LIKE '# [bad_emails] new.rows include=id:%')
     )
     OR array_position(
       v_variant_lines, '# bad_emails has 3 NEW rows; choose selector_id from:') IS NULL THEN
    RAISE EXCEPTION 'custom selector limit did not preserve exact N and generic N+1: %',
      array_to_string(v_variant_lines, E'\n');
  END IF;

  -- Zero disables every exact suggestion while retaining generic guidance.
  UPDATE delta_ctl.run_metadata
  SET value = '0'
  WHERE key = 'selector_suggestion_limit';
  SELECT array_agg(line ORDER BY ord)
    INTO v_variant_lines
  FROM delta_ctl.render_selection_manifest() WITH ORDINALITY AS manifest(line, ord);
  v_small_new := array_position(
    v_variant_lines, '# Small NEW sets receive ready-to-uncomment suggestions:');
  v_large_new := array_position(
    v_variant_lines, '# Large NEW sets receive a useful pointer rather than no guidance:');
  IF v_small_new IS NULL OR v_large_new IS NULL OR EXISTS (
    SELECT 1
    FROM unnest(v_variant_lines) WITH ORDINALITY AS rendered(line, ord)
    WHERE ord > v_small_new AND ord < v_large_new
      AND (line ~ '^# \[[^]]+\] (new|changed)\.rows include=(id|row):'
           OR line ~ '^# \[[^]]+\] Exact (NEW|CHANGED) set:'
           OR line ~ '^# \[[^]]+\] Exact (NEW|CHANGED) selector unavailable')
  ) THEN
    RAISE EXCEPTION 'zero selector limit still emitted exact selector assistance: %',
      array_to_string(v_variant_lines, E'\n');
  END IF;
  SELECT count(*) INTO v_generic_count
  FROM unnest(v_variant_lines) line
  WHERE line ~ '^# [a-z0-9_]+ has [0-9]+ (NEW|CHANGED) rows; choose selector_id';
  IF v_generic_count <> 10 THEN
    RAISE EXCEPTION 'zero selector limit did not make every positive set generic: count=% manifest=%',
      v_generic_count, array_to_string(v_variant_lines, E'\n');
  END IF;

  -- Present malformed metadata fails clearly; only absence receives the fallback.
  FOREACH v_invalid_value IN ARRAY ARRAY['bogus', '-1', '100001', NULL]::text[] LOOP
    UPDATE delta_ctl.run_metadata
    SET value = v_invalid_value
    WHERE key = 'selector_suggestion_limit';
    v_error := NULL;
    BEGIN
      PERFORM delta_ctl.render_selection_manifest();
    EXCEPTION WHEN OTHERS THEN
      v_error := SQLERRM;
    END;
    IF v_error IS NULL
       OR position('invalid selector_suggestion_limit metadata value:' in v_error) = 0
       OR position('allowed range: 0..100000' in v_error) = 0 THEN
      RAISE EXCEPTION 'invalid selector metadata % did not fail clearly: %',
        COALESCE(v_invalid_value, '<NULL>'), COALESCE(v_error, '<no error>');
    END IF;
  END LOOP;
  DELETE FROM delta_ctl.run_metadata WHERE key = 'selector_suggestion_limit';

  UPDATE delta_ctl.run_metadata SET value = 'none' WHERE key = 'manifest_default';
  SELECT array_agg(line ORDER BY ord)
    INTO v_none_lines
  FROM delta_ctl.render_selection_manifest() WITH ORDINALITY AS manifest(line, ord);

  SELECT ord INTO v_wildcard
  FROM unnest(v_none_lines) WITH ORDINALITY AS u(line, ord)
  WHERE line LIKE '[*]%' LIMIT 1;
  IF v_none_lines[v_wildcard] !~ '^\[\*\][[:space:]]+include=$'
     OR v_none_lines[v_wildcard + 1] <>
       '# Default selection ([*] none) currently matches 0 rows across 0 tables (new=0 changed=0).'
     OR EXISTS (
       SELECT 1 FROM unnest(v_none_lines) line
       WHERE line NOT LIKE '#%' AND line ~ 'include=(new|changed)'
     ) THEN
    RAISE EXCEPTION '--manifest-default none did not produce an empty active selection: %',
      array_to_string(v_none_lines, E'\n');
  END IF;

  DELETE FROM delta_ctl.run_metadata WHERE key = 'manifest_default';
  SELECT array_agg(line ORDER BY ord)
    INTO v_none_lines
  FROM delta_ctl.render_selection_manifest() WITH ORDINALITY AS manifest(line, ord);
  IF NOT EXISTS (
    SELECT 1 FROM unnest(v_none_lines) line
    WHERE line ~ '^\[\*\][[:space:]]+include=new,changed$'
  ) THEN
    RAISE EXCEPTION 'missing manifest_default metadata did not preserve the historical default';
  END IF;
END $$;
