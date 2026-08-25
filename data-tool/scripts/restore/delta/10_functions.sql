-- Delta restore classification, selection, and apply functions.

CREATE OR REPLACE FUNCTION delta_ctl.assert_identifier(p_value text, p_kind text DEFAULT 'identifier')
RETURNS text
LANGUAGE plpgsql
AS $$
BEGIN
  IF p_value IS NULL OR p_value !~ '^[a-z_][a-z0-9_]*$' THEN
    RAISE EXCEPTION 'invalid %: %', p_kind, p_value;
  END IF;
  RETURN p_value;
END;
$$;

CREATE OR REPLACE FUNCTION delta_ctl.public_rel(p_name text)
RETURNS text
LANGUAGE sql
IMMUTABLE PARALLEL SAFE
AS $$ SELECT format('public.%I', p_name) $$;

CREATE OR REPLACE FUNCTION delta_ctl.map_table_name(p_table text)
RETURNS text
LANGUAGE sql
IMMUTABLE STRICT PARALLEL SAFE
AS $$ SELECT p_table || '_id_map' $$;

CREATE OR REPLACE FUNCTION delta_ctl.map_rel(p_table text)
RETURNS text
LANGUAGE sql
IMMUTABLE STRICT PARALLEL SAFE
AS $$ SELECT format('delta_map.%I', delta_ctl.map_table_name(p_table)) $$;

CREATE OR REPLACE FUNCTION delta_ctl.temp_rel(p_name text)
RETURNS text
LANGUAGE sql
IMMUTABLE STRICT PARALLEL SAFE
AS $$ SELECT format('pg_temp.%I', p_name) $$;

CREATE OR REPLACE FUNCTION delta_ctl.drop_table_sql(p_rel text)
RETURNS text
LANGUAGE sql
IMMUTABLE STRICT PARALLEL SAFE
AS $$ SELECT format('DROP TABLE IF EXISTS %s', p_rel) $$;

CREATE OR REPLACE FUNCTION delta_ctl.analyze_sql(p_rel text)
RETURNS text
LANGUAGE sql
IMMUTABLE STRICT PARALLEL SAFE
AS $$ SELECT format('ANALYZE %s', p_rel) $$;

CREATE OR REPLACE FUNCTION delta_ctl.stage_fk_join(p_fk_temp text)
RETURNS text
LANGUAGE sql
IMMUTABLE STRICT PARALLEL SAFE
AS $$ SELECT format('LEFT JOIN %s fk ON fk._delta_row_id = s._delta_row_id', p_fk_temp) $$;

CREATE OR REPLACE FUNCTION delta_ctl.aliased_expr(p_expr text, p_alias text)
RETURNS text
LANGUAGE sql
IMMUTABLE STRICT PARALLEL SAFE
AS $$ SELECT format('%s AS %I', p_expr, p_alias) $$;

CREATE OR REPLACE FUNCTION delta_ctl.nk_hash_index_sql(p_rel text)
RETURNS text
LANGUAGE sql
IMMUTABLE STRICT PARALLEL SAFE
AS $$ SELECT format('CREATE INDEX ON %s (nk_hash)', p_rel) $$;

CREATE OR REPLACE FUNCTION delta_ctl.null_bigint_expr()
RETURNS text
LANGUAGE sql
IMMUTABLE PARALLEL SAFE
AS $$ SELECT 'NULL::bigint' $$;

CREATE OR REPLACE FUNCTION delta_ctl.class_table_name(p_base_table text)
RETURNS text
LANGUAGE sql
IMMUTABLE STRICT PARALLEL SAFE
AS $$ SELECT p_base_table || '_class' $$;

CREATE OR REPLACE FUNCTION delta_ctl.duplicate_table_name(p_table text, p_scope text)
RETURNS text
LANGUAGE sql
IMMUTABLE STRICT PARALLEL SAFE
AS $$ SELECT 'delta_dup_' || p_table || '_' || p_scope $$;

CREATE OR REPLACE FUNCTION delta_ctl.false_expr()
RETURNS text
LANGUAGE sql
IMMUTABLE PARALLEL SAFE
AS $$ SELECT 'false' $$;

CREATE OR REPLACE FUNCTION delta_ctl.hash_parent_mode()
RETURNS text
LANGUAGE sql
IMMUTABLE PARALLEL SAFE
AS $$ SELECT 'hash_parent' $$;

CREATE OR REPLACE FUNCTION delta_ctl.auth_processing_table()
RETURNS text
LANGUAGE sql
IMMUTABLE PARALLEL SAFE
AS $$ SELECT 'auth_processing' $$;

CREATE OR REPLACE FUNCTION delta_ctl.table_kind()
RETURNS text
LANGUAGE sql
IMMUTABLE PARALLEL SAFE
AS $$ SELECT 'table' $$;

CREATE OR REPLACE FUNCTION delta_ctl.class_header()
RETURNS text
LANGUAGE sql
IMMUTABLE PARALLEL SAFE
AS $$ SELECT 'class' $$;

CREATE OR REPLACE FUNCTION delta_ctl.truncated_rows_marker(p_limit integer)
RETURNS text
LANGUAGE sql
IMMUTABLE STRICT PARALLEL SAFE
AS $$ SELECT format('# TRUNCATED at %s rows', p_limit) $$;

CREATE OR REPLACE FUNCTION delta_ctl.parent_table_kind()
RETURNS text
LANGUAGE sql
IMMUTABLE PARALLEL SAFE
AS $$ SELECT 'parent table' $$;

CREATE OR REPLACE FUNCTION delta_ctl.and_separator()
RETURNS text
LANGUAGE sql
IMMUTABLE PARALLEL SAFE
AS $$ SELECT ' AND ' $$;

CREATE OR REPLACE FUNCTION delta_ctl.external_fk_pattern()
RETURNS text
LANGUAGE sql
IMMUTABLE PARALLEL SAFE
AS $$ SELECT 'external:%' $$;

CREATE OR REPLACE FUNCTION delta_ctl.fk_alias_kind()
RETURNS text
LANGUAGE sql
IMMUTABLE PARALLEL SAFE
AS $$ SELECT 'FK alias' $$;

CREATE OR REPLACE FUNCTION delta_ctl.local_id_col(p_fk_col text)
RETURNS text
LANGUAGE sql
IMMUTABLE STRICT PARALLEL SAFE
AS $$ SELECT p_fk_col || '_local_id' $$;

CREATE OR REPLACE FUNCTION delta_ctl.map_fk_expr(p_parent_table text, p_fk_col text)
RETURNS text
LANGUAGE sql
IMMUTABLE STRICT PARALLEL SAFE
AS $$ SELECT format('delta_ctl.map_fk(%L, s.%I::bigint)', p_parent_table, p_fk_col) $$;

CREATE OR REPLACE FUNCTION delta_ctl.assert_table_name(p_table text)
RETURNS text
LANGUAGE sql
AS $$ SELECT delta_ctl.assert_identifier(p_table, delta_ctl.table_kind()) $$;

CREATE OR REPLACE FUNCTION delta_ctl.parent_pending_col(p_fk_col text)
RETURNS text
LANGUAGE sql
IMMUTABLE STRICT PARALLEL SAFE
AS $$ SELECT p_fk_col || '_parent_pending' $$;

CREATE OR REPLACE FUNCTION delta_ctl.auth_component_op_table()
RETURNS text
LANGUAGE sql
IMMUTABLE PARALLEL SAFE
AS $$ SELECT 'auth_component_operation' $$;

CREATE OR REPLACE FUNCTION delta_ctl.stage_table_exists(p_table text)
RETURNS boolean
LANGUAGE sql
AS $$
SELECT to_regclass(format('delta_stage.%I', p_table)) IS NOT NULL;
$$;

CREATE OR REPLACE FUNCTION delta_ctl.map_table_exists(p_table text)
RETURNS boolean
LANGUAGE sql
AS $$
SELECT to_regclass(delta_ctl.map_rel(p_table)) IS NOT NULL;
$$;

CREATE OR REPLACE FUNCTION delta_ctl.phase_notice(p_table text, p_phase text, p_started_at timestamptz DEFAULT NULL)
RETURNS timestamptz
LANGUAGE plpgsql
AS $$
DECLARE
  v_now timestamptz := clock_timestamp();
BEGIN
  IF p_started_at IS NULL THEN
    RAISE NOTICE 'delta_restore table=% phase=% start', COALESCE(p_table, '<all>'), p_phase;
  ELSE
    RAISE NOTICE 'delta_restore table=% phase=% done elapsed_ms=%',
      COALESCE(p_table, '<all>'), p_phase,
      round((EXTRACT(epoch FROM (v_now - p_started_at)) * 1000)::numeric, 3);
  END IF;
  RETURN v_now;
END;
$$;

CREATE OR REPLACE FUNCTION delta_ctl.map_fk(p_parent_table text, p_staged_id bigint)
RETURNS bigint
LANGUAGE plpgsql
AS $$
DECLARE
  v_map regclass;
  v_local_id bigint;
  v_row_count bigint;
BEGIN
  PERFORM delta_ctl.assert_identifier(p_parent_table, delta_ctl.parent_table_kind());
  IF p_staged_id IS NULL THEN
    RETURN NULL;
  END IF;

  v_map := to_regclass(delta_ctl.map_rel(p_parent_table));
  IF v_map IS NOT NULL THEN
    EXECUTE format('SELECT local_id FROM %s WHERE staged_id = $1', v_map)
      INTO v_local_id
      USING p_staged_id;
    GET DIAGNOSTICS v_row_count = ROW_COUNT;
    IF v_row_count > 0 THEN
      RETURN v_local_id;
    END IF;

    -- A map table exists, so a miss means the staged parent was not safely mapped
    -- (for example AMBIGUOUS_NK/BLOCKED_FK). Do not fall back to same-number
    -- public IDs because those may belong to unrelated local rows.
    RETURN NULL;
  END IF;

  IF to_regclass(delta_ctl.public_rel(p_parent_table)) IS NOT NULL THEN
    EXECUTE format('SELECT id::bigint FROM public.%I WHERE id = $1', p_parent_table)
      INTO v_local_id
      USING p_staged_id;
    GET DIAGNOSTICS v_row_count = ROW_COUNT;
    IF v_row_count > 0 THEN
      RETURN v_local_id;
    END IF;
  END IF;

  RETURN NULL;
END;
$$;

CREATE OR REPLACE FUNCTION delta_ctl.parent_pending(p_parent_table text, p_staged_id bigint)
RETURNS boolean
LANGUAGE plpgsql
AS $$
DECLARE
  v_map regclass;
  v_disposition text;
BEGIN
  PERFORM delta_ctl.assert_identifier(p_parent_table, delta_ctl.parent_table_kind());
  IF p_staged_id IS NULL THEN
    RETURN false;
  END IF;

  v_map := to_regclass(delta_ctl.map_rel(p_parent_table));
  IF v_map IS NULL THEN
    RETURN false;
  END IF;

  EXECUTE format('SELECT disposition FROM %s WHERE staged_id = $1', v_map)
    INTO v_disposition
    USING p_staged_id;

  RETURN COALESCE(v_disposition LIKE 'NEW%', false);
END;
$$;

CREATE OR REPLACE FUNCTION delta_ctl.jsonb_array_expr(p_exprs text[])
RETURNS text
LANGUAGE plpgsql
AS $$
BEGIN
  IF p_exprs IS NULL OR array_length(p_exprs, 1) IS NULL THEN
    RETURN '''[]''::jsonb';
  END IF;
  RETURN 'jsonb_build_array(' || array_to_string(p_exprs, ', ') || ')';
END;
$$;

CREATE OR REPLACE FUNCTION delta_ctl.null_safe_join(p_left_exprs text[], p_right_exprs text[])
RETURNS text
LANGUAGE plpgsql
AS $$
DECLARE
  i int;
  parts text[] := '{}';
BEGIN
  IF COALESCE(array_length(p_left_exprs, 1), 0) <> COALESCE(array_length(p_right_exprs, 1), 0)
     OR COALESCE(array_length(p_left_exprs, 1), 0) = 0 THEN
    RAISE EXCEPTION 'cannot build null-safe join for mismatched/empty expression lists: % vs %', p_left_exprs, p_right_exprs;
  END IF;

  FOR i IN 1..array_length(p_left_exprs, 1) LOOP
    parts := parts || format('(%s) IS NOT DISTINCT FROM (%s)', p_left_exprs[i], p_right_exprs[i]);
  END LOOP;
  RETURN array_to_string(parts, delta_ctl.and_separator());
END;
$$;

CREATE OR REPLACE FUNCTION delta_ctl.nk_hash_expr(p_exprs text[])
RETURNS text
LANGUAGE plpgsql
AS $$
BEGIN
  IF COALESCE(array_length(p_exprs, 1), 0) = 0 THEN
    RAISE EXCEPTION 'cannot build NK hash expression for empty expression list: %', p_exprs;
  END IF;

  RETURN 'md5(' || delta_ctl.jsonb_array_expr(p_exprs) || '::text)';
END;
$$;

CREATE OR REPLACE FUNCTION delta_ctl.stage_compare_expr(p_table text, p_col text, p_fk_alias text DEFAULT NULL)
RETURNS text
LANGUAGE plpgsql
AS $$
DECLARE
  v_parent text;
BEGIN
  SELECT value INTO v_parent
  FROM delta_ctl.table_config c, jsonb_each_text(c.fk_map)
  WHERE c.table_name = p_table
    AND key = p_col
    AND value NOT LIKE delta_ctl.external_fk_pattern();

  IF v_parent IS NOT NULL THEN
    PERFORM delta_ctl.assert_identifier(v_parent, delta_ctl.parent_table_kind());
    IF p_fk_alias IS NOT NULL THEN
      PERFORM delta_ctl.assert_identifier(p_fk_alias, delta_ctl.fk_alias_kind());
      RETURN format('%I.%I', p_fk_alias, delta_ctl.local_id_col(p_col));
    END IF;
    RETURN delta_ctl.map_fk_expr(v_parent, p_col);
  END IF;
  RETURN format('s.%I', p_col);
END;
$$;

CREATE OR REPLACE FUNCTION delta_ctl.effective_stage_nk_exprs(p_table text, p_fk_alias text DEFAULT NULL)
RETURNS text[]
LANGUAGE plpgsql
AS $$
DECLARE
  v_cfg delta_ctl.table_config%ROWTYPE;
  v_expr text;
  v_col text;
  v_parent text;
  v_out text[] := '{}';
BEGIN
  SELECT * INTO v_cfg FROM delta_ctl.table_config WHERE table_name = p_table;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'missing table_config row for %', p_table; -- NOSONAR
  END IF;

  IF p_fk_alias IS NOT NULL THEN
    PERFORM delta_ctl.assert_identifier(p_fk_alias, delta_ctl.fk_alias_kind());
  END IF;

  FOREACH v_expr IN ARRAY v_cfg.nk_stage_exprs LOOP
    v_col := NULL;
    v_parent := NULL;
    SELECT key, value INTO v_col, v_parent
    FROM jsonb_each_text(v_cfg.fk_map)
    WHERE value NOT LIKE delta_ctl.external_fk_pattern()
      AND v_expr = delta_ctl.map_fk_expr(value, key)
    LIMIT 1;

    IF p_fk_alias IS NOT NULL AND v_col IS NOT NULL THEN
      v_out := v_out || format('%I.%I', p_fk_alias, delta_ctl.local_id_col(v_col));
    ELSE
      v_out := v_out || v_expr;
    END IF;
  END LOOP;

  RETURN v_out;
END;
$$;

CREATE OR REPLACE FUNCTION delta_ctl.local_compare_expr(p_col text)
RETURNS text
LANGUAGE sql
AS $$
SELECT format('l.%I', p_col);
$$;

CREATE OR REPLACE FUNCTION delta_ctl.compare_columns(p_table text)
RETURNS text[]
LANGUAGE plpgsql
AS $$
DECLARE
  v_cfg delta_ctl.table_config%ROWTYPE;
  v_cols text[];
BEGIN
  SELECT * INTO v_cfg FROM delta_ctl.table_config WHERE table_name = p_table;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'missing table_config row for %', p_table;
  END IF;

  SELECT COALESCE(array_agg(a.attname ORDER BY a.attnum), '{}')
    INTO v_cols
  FROM pg_attribute a
  WHERE a.attrelid = delta_ctl.public_rel(p_table)::regclass
    AND a.attnum > 0
    AND NOT a.attisdropped
    AND a.attname <> '_delta_row_id'
    AND (v_cfg.pk_col IS NULL OR a.attname <> v_cfg.pk_col)
    AND NOT (a.attname = ANY(v_cfg.nk_cols))
    AND NOT (a.attname = ANY(v_cfg.classify_ignore_cols))
    AND NOT (a.attname = ANY(v_cfg.compare_ignore_cols));

  RETURN v_cols;
END;
$$;

CREATE OR REPLACE FUNCTION delta_ctl.complete_table_config()
RETURNS void
LANGUAGE plpgsql
AS $$
DECLARE
  c_stage_corp_num CONSTANT text := 's.corp_num';
  c_local_corp_num CONSTANT text := 'l.corp_num';
  c_corp_num CONSTANT text := 'corp_num';
  c_target_environment CONSTANT text := 'target_environment';
  c_stage_target_environment CONSTANT text := 's.target_environment';
  c_local_target_environment CONSTANT text := 'l.target_environment';
  c_stage_flow_name CONSTANT text := 's.flow_name';
  c_stage_environment CONSTANT text := 's.environment';
  c_local_flow_name CONSTANT text := 'l.flow_name';
  c_local_environment CONSTANT text := 'l.environment';
  c_flow_name CONSTANT text := 'flow_name';
  c_environment CONSTANT text := 'environment';
BEGIN
  UPDATE delta_ctl.table_config
  SET pk_col = NULL,
      nk_enforced = false,
      match_mode = 'nk',
      nk_stage_exprs = '{}',
      nk_local_exprs = '{}',
      nk_cols = '{}',
      fk_map = '{}'::jsonb,
      has_last_modified = false,
      compare_ignore_cols = '{}'
  WHERE table_name IS NOT NULL;

  UPDATE delta_ctl.table_config SET
    pk_col = 'id',
    nk_stage_exprs = ARRAY['s.filing_id'],
    nk_local_exprs = ARRAY['l.filing_id'],
    nk_cols = ARRAY['filing_id'],
    nk_enforced = true
  WHERE table_name = 'demigrated_filings';

  UPDATE delta_ctl.table_config SET
    nk_stage_exprs = ARRAY['s.email_domain'],
    nk_local_exprs = ARRAY['l.email_domain'],
    nk_cols = ARRAY['email_domain'],
    nk_enforced = true
  WHERE table_name = 'email_domain_groups';

  UPDATE delta_ctl.table_config SET
    pk_col = 'id',
    nk_stage_exprs = ARRAY['lower(btrim(s.email))'],
    nk_local_exprs = ARRAY['lower(btrim(l.email))'],
    nk_cols = '{}',
    nk_enforced = true
  WHERE table_name = 'bad_emails';

  UPDATE delta_ctl.table_config SET
    nk_stage_exprs = ARRAY['lower(btrim(s.email))'],
    nk_local_exprs = ARRAY['lower(btrim(l.email))'],
    nk_cols = '{}',
    nk_enforced = true
  WHERE table_name = 'excluded_emails';

  UPDATE delta_ctl.table_config SET
    nk_stage_exprs = ARRAY['lower(btrim(s.email_domain))'],
    nk_local_exprs = ARRAY['lower(btrim(l.email_domain))'],
    nk_cols = '{}',
    nk_enforced = true
  WHERE table_name = 'excluded_email_domains';

  UPDATE delta_ctl.table_config SET
    pk_col = 'id',
    nk_stage_exprs = ARRAY['lower(btrim(s.email_domain))', 'lower(btrim(s.local_part_pattern))'],
    nk_local_exprs = ARRAY['lower(btrim(l.email_domain))', 'lower(btrim(l.local_part_pattern))'],
    nk_cols = '{}',
    nk_enforced = true
  WHERE table_name = 'excluded_email_domain_patterns';

  UPDATE delta_ctl.table_config SET
    nk_stage_exprs = ARRAY[c_stage_corp_num],
    nk_local_exprs = ARRAY[c_local_corp_num],
    nk_cols = ARRAY[c_corp_num],
    nk_enforced = true
  WHERE table_name = 'exclude_corps';

  UPDATE delta_ctl.table_config SET
    nk_stage_exprs = ARRAY[c_stage_corp_num, 's.vendor'],
    nk_local_exprs = ARRAY[c_local_corp_num, 'l.vendor'],
    nk_cols = ARRAY[c_corp_num, 'vendor'],
    nk_enforced = false
  WHERE table_name = 'corps_with_third_party';

  UPDATE delta_ctl.table_config SET
    nk_stage_exprs = ARRAY['s.identifier'],
    nk_local_exprs = ARRAY['l.identifier'],
    nk_cols = ARRAY['identifier'],
    nk_enforced = false
  WHERE table_name = 'bar_corps';

  UPDATE delta_ctl.table_config SET
    pk_col = 'id',
    nk_stage_exprs = ARRAY['s.name', c_stage_target_environment, 's.source_db'],
    nk_local_exprs = ARRAY['l.name', c_local_target_environment, 'l.source_db'],
    nk_cols = ARRAY['name', c_target_environment, 'source_db'],
    nk_enforced = false
  WHERE table_name = 'mig_group';

  UPDATE delta_ctl.table_config SET
    pk_col = 'id',
    nk_stage_exprs = ARRAY['delta_ctl.map_fk(''mig_group'', s.mig_group_id::bigint)', 's.name', c_stage_target_environment],
    nk_local_exprs = ARRAY['l.mig_group_id', 'l.name', c_local_target_environment],
    nk_cols = ARRAY['mig_group_id', 'name', c_target_environment],
    nk_enforced = false,
    fk_map = '{"mig_group_id":"mig_group"}'::jsonb
  WHERE table_name = 'mig_batch';

  UPDATE delta_ctl.table_config SET
    pk_col = 'id',
    nk_stage_exprs = ARRAY['delta_ctl.map_fk(''mig_batch'', s.mig_batch_id::bigint)', c_stage_corp_num],
    nk_local_exprs = ARRAY['l.mig_batch_id', c_local_corp_num],
    nk_cols = ARRAY['mig_batch_id', c_corp_num],
    nk_enforced = false,
    fk_map = '{"mig_batch_id":"mig_batch"}'::jsonb
  WHERE table_name = 'mig_corp_batch';

  UPDATE delta_ctl.table_config SET
    pk_col = 'id',
    nk_stage_exprs = ARRAY[c_stage_corp_num, c_stage_target_environment, 's.account_id', 'delta_ctl.map_fk(''mig_batch'', s.mig_batch_id::bigint)'],
    nk_local_exprs = ARRAY[c_local_corp_num, c_local_target_environment, 'l.account_id', 'l.mig_batch_id'],
    nk_cols = ARRAY[c_corp_num, c_target_environment, 'account_id', 'mig_batch_id'],
    nk_enforced = false,
    fk_map = '{"mig_batch_id":"mig_batch"}'::jsonb
  WHERE table_name = 'mig_corp_account';

  UPDATE delta_ctl.table_config SET
    pk_col = 'id',
    nk_stage_exprs = ARRAY[c_stage_corp_num, c_stage_flow_name, c_stage_environment],
    nk_local_exprs = ARRAY[c_local_corp_num, c_local_flow_name, c_local_environment],
    nk_cols = ARRAY[c_corp_num, c_flow_name, c_environment],
    nk_enforced = true,
    has_last_modified = true,
    fk_map = '{"mig_batch_id":"mig_batch","corp_num":"external:corporation.corp_num","last_processed_event_id":"external:event.event_id","failed_event_id":"external:event.event_id"}'::jsonb
  WHERE table_name = 'corp_processing';

  UPDATE delta_ctl.table_config SET
    pk_col = 'id',
    nk_stage_exprs = ARRAY[c_stage_corp_num, c_stage_flow_name, c_stage_environment],
    nk_local_exprs = ARRAY[c_local_corp_num, c_local_flow_name, c_local_environment],
    nk_cols = ARRAY[c_corp_num, c_flow_name, c_environment],
    nk_enforced = true,
    has_last_modified = true,
    fk_map = '{"mig_batch_id":"mig_batch","corp_num":"external:corporation.corp_num"}'::jsonb
  WHERE table_name = 'colin_tracking';

  UPDATE delta_ctl.table_config SET
    pk_col = 'id',
    nk_stage_exprs = ARRAY[c_stage_corp_num, c_stage_flow_name, c_stage_environment, 's.operation', 's.operation_scope', 's.attempt_key'],
    nk_local_exprs = ARRAY[c_local_corp_num, c_local_flow_name, c_local_environment, 'l.operation', 'l.operation_scope', 'l.attempt_key'],
    nk_cols = ARRAY[c_corp_num, c_flow_name, c_environment, 'operation', 'operation_scope', 'attempt_key'],
    nk_enforced = true,
    has_last_modified = true,
    fk_map = '{"mig_batch_id":"mig_batch","corp_num":"external:corporation.corp_num"}'::jsonb
  WHERE table_name = delta_ctl.auth_processing_table();

  UPDATE delta_ctl.table_config SET
    pk_col = 'id',
    match_mode = delta_ctl.hash_parent_mode(),
    compare_ignore_cols = ARRAY['id'],
    fk_map = '{"auth_processing_id":"auth_processing"}'::jsonb
  WHERE table_name = delta_ctl.auth_component_op_table();
END;
$$;

CREATE OR REPLACE FUNCTION delta_ctl.create_class_table(p_table text)
RETURNS void
LANGUAGE plpgsql
AS $$
BEGIN
  PERFORM delta_ctl.assert_table_name(p_table);
  EXECUTE format('DROP TABLE IF EXISTS delta_diff.%I', delta_ctl.class_table_name(p_table));
  EXECUTE format($fmt$
    CREATE TABLE delta_diff.%I (
      _delta_row_id bigint PRIMARY KEY,
      staged_pk bigint NULL,
      local_pk bigint NULL,
      local_ctid tid NULL,
      class text NOT NULL,
      changed_cols text[],
      block_reason text,
      parent_pending boolean NOT NULL DEFAULT false,
      selected boolean NOT NULL DEFAULT false
    )
  $fmt$, delta_ctl.class_table_name(p_table));
END;
$$;

CREATE OR REPLACE FUNCTION delta_ctl.parent_pending_expr(p_table text, p_fk_alias text DEFAULT NULL)
RETURNS text
LANGUAGE plpgsql
AS $$
DECLARE
  r record;
  parts text[] := '{}';
BEGIN
  IF p_fk_alias IS NOT NULL THEN
    PERFORM delta_ctl.assert_identifier(p_fk_alias, delta_ctl.fk_alias_kind());
  END IF;

  FOR r IN
    SELECT key AS fk_col, value AS parent_table
    FROM delta_ctl.table_config c, jsonb_each_text(c.fk_map)
    WHERE c.table_name = p_table AND value NOT LIKE delta_ctl.external_fk_pattern()
  LOOP
    IF p_fk_alias IS NOT NULL THEN
      parts := parts || format('COALESCE(%I.%I, false)', p_fk_alias, delta_ctl.parent_pending_col(r.fk_col));
    ELSE
      parts := parts || format('delta_ctl.parent_pending(%L, s.%I::bigint)', r.parent_table, r.fk_col);
    END IF;
  END LOOP;

  IF array_length(parts, 1) IS NULL THEN
    RETURN delta_ctl.false_expr();
  END IF;
  RETURN array_to_string(parts, ' OR ');
END;
$$;

CREATE OR REPLACE FUNCTION delta_ctl.create_stage_fk_map(p_table text)
RETURNS text
LANGUAGE plpgsql
AS $$
DECLARE
  r record;
  v_temp_name text;
  v_temp_rel text;
  v_selects text[] := ARRAY['s._delta_row_id'];
  v_joins text[] := '{}';
  v_join text;
  v_alias text;
  v_idx int := 0;
BEGIN
  PERFORM delta_ctl.assert_table_name(p_table);
  IF NOT delta_ctl.stage_table_exists(p_table) THEN
    RETURN NULL;
  END IF;

  FOR r IN
    SELECT key AS fk_col, value AS parent_table,
           to_regclass(delta_ctl.map_rel(value)) AS map_rel
    FROM delta_ctl.table_config c, jsonb_each_text(c.fk_map)
    WHERE c.table_name = p_table AND value NOT LIKE delta_ctl.external_fk_pattern()
    ORDER BY key
  LOOP
    PERFORM delta_ctl.assert_identifier(r.fk_col, 'FK column');
    PERFORM delta_ctl.assert_identifier(r.parent_table, delta_ctl.parent_table_kind());
    v_idx := v_idx + 1;
    v_alias := 'm' || v_idx;
    IF r.map_rel IS NOT NULL THEN
      v_joins := v_joins || format('LEFT JOIN %s %I ON %I.staged_id = s.%I', r.map_rel, v_alias, v_alias, r.fk_col);
      v_selects := v_selects || format('CASE WHEN s.%I IS NULL THEN NULL::bigint ELSE %I.local_id END AS %I', r.fk_col, v_alias, delta_ctl.local_id_col(r.fk_col));
      v_selects := v_selects || format('CASE WHEN s.%I IS NULL THEN false ELSE COALESCE(%I.disposition LIKE ''NEW%%'', false) END AS %I', r.fk_col, v_alias, delta_ctl.parent_pending_col(r.fk_col));
    ELSIF to_regclass(delta_ctl.public_rel(r.parent_table)) IS NOT NULL THEN
      v_joins := v_joins || format('LEFT JOIN public.%I %I ON %I.id = s.%I', r.parent_table, v_alias, v_alias, r.fk_col);
      v_selects := v_selects || format('CASE WHEN s.%I IS NULL THEN NULL::bigint ELSE %I.id::bigint END AS %I', r.fk_col, v_alias, delta_ctl.local_id_col(r.fk_col));
      v_selects := v_selects || format('false AS %I', delta_ctl.parent_pending_col(r.fk_col));
    ELSE
      v_selects := v_selects || format('NULL::bigint AS %I', delta_ctl.local_id_col(r.fk_col));
      v_selects := v_selects || format('false AS %I', delta_ctl.parent_pending_col(r.fk_col));
    END IF;
  END LOOP;

  IF v_idx = 0 THEN
    RETURN NULL;
  END IF;

  v_temp_name := 'delta_fk_' || p_table;
  v_temp_rel := delta_ctl.temp_rel(v_temp_name);
  v_join := array_to_string(v_joins, E'\n    ');

  EXECUTE delta_ctl.drop_table_sql(v_temp_rel);
  EXECUTE format($fmt$
    CREATE TEMP TABLE %I AS
    SELECT %s
    FROM delta_stage.%I s
    %s
  $fmt$, v_temp_name, array_to_string(v_selects, ', '), p_table, v_join);
  EXECUTE format('CREATE INDEX ON %s (_delta_row_id)', v_temp_rel);
  EXECUTE delta_ctl.analyze_sql(v_temp_rel);
  RETURN v_temp_rel;
END;
$$;

CREATE OR REPLACE FUNCTION delta_ctl.detect_ambiguity(p_table text, p_fk_temp text DEFAULT NULL)
RETURNS void
LANGUAGE plpgsql
AS $$
DECLARE
  v_cfg delta_ctl.table_config%ROWTYPE;
  v_stage_exprs text[];
  v_local_exprs text[];
  v_stage_selects text[] := '{}';
  v_local_selects text[] := '{}';
  v_stage_join text := '';
  v_stage_dup text;
  v_local_dup text;
  v_staged_pk text;
  v_parent_pending text;
  v_group_by text;
  v_stage_dup_join text;
  v_local_dup_join text;
  v_i int;
  v_sql text;
BEGIN
  SELECT * INTO v_cfg FROM delta_ctl.table_config WHERE table_name = p_table;
  IF NOT FOUND OR v_cfg.nk_enforced OR v_cfg.match_mode <> 'nk' THEN
    RETURN;
  END IF;

  v_stage_exprs := delta_ctl.effective_stage_nk_exprs(p_table, CASE WHEN p_fk_temp IS NULL THEN NULL ELSE 'fk' END);
  v_local_exprs := v_cfg.nk_local_exprs;
  IF COALESCE(array_length(v_stage_exprs, 1), 0) = 0 THEN
    RETURN;
  END IF;

  IF p_fk_temp IS NOT NULL THEN
    v_stage_join := delta_ctl.stage_fk_join(p_fk_temp);
  END IF;

  FOR v_i IN 1..array_length(v_stage_exprs, 1) LOOP
    v_stage_selects := v_stage_selects || delta_ctl.aliased_expr(v_stage_exprs[v_i], 'k' || v_i);
    v_local_selects := v_local_selects || delta_ctl.aliased_expr(v_local_exprs[v_i], 'k' || v_i);
  END LOOP;

  v_stage_dup := delta_ctl.temp_rel(delta_ctl.duplicate_table_name(p_table, 'stage'));
  v_local_dup := delta_ctl.temp_rel(delta_ctl.duplicate_table_name(p_table, 'local'));
  v_staged_pk := CASE WHEN v_cfg.pk_col IS NULL THEN delta_ctl.null_bigint_expr() ELSE format('s.%I::bigint', v_cfg.pk_col) END;
  v_parent_pending := delta_ctl.parent_pending_expr(p_table, CASE WHEN p_fk_temp IS NULL THEN NULL ELSE 'fk' END);
  v_group_by := array_to_string(ARRAY(SELECT gs::text FROM generate_series(1, array_length(v_stage_exprs, 1)) AS gs), ', ');
  v_stage_dup_join := array_to_string(ARRAY(
    SELECT format('sd.%I IS NOT DISTINCT FROM (%s)', 'k' || i, v_stage_exprs[i])
    FROM generate_subscripts(v_stage_exprs, 1) AS i
  ), delta_ctl.and_separator());
  v_stage_dup_join := format('sd.nk_hash = (%s) AND %s', delta_ctl.nk_hash_expr(v_stage_exprs), v_stage_dup_join);
  v_local_dup_join := array_to_string(ARRAY(
    SELECT format('ld.%I IS NOT DISTINCT FROM (%s)', 'k' || i, v_stage_exprs[i])
    FROM generate_subscripts(v_stage_exprs, 1) AS i
  ), delta_ctl.and_separator());
  v_local_dup_join := format('ld.nk_hash = (%s) AND %s', delta_ctl.nk_hash_expr(v_stage_exprs), v_local_dup_join);

  EXECUTE delta_ctl.drop_table_sql(v_stage_dup);
  EXECUTE delta_ctl.drop_table_sql(v_local_dup);
  EXECUTE format($fmt$
    CREATE TEMP TABLE %I AS
    SELECT %s, %s AS nk_hash, count(*)::bigint AS n
    FROM delta_stage.%I s
    %s
    WHERE NOT (%s)
    GROUP BY %s HAVING count(*) > 1
  $fmt$, delta_ctl.duplicate_table_name(p_table, 'stage'), array_to_string(v_stage_selects, ', '),
        delta_ctl.nk_hash_expr(v_stage_exprs), p_table, v_stage_join, v_parent_pending, v_group_by);
  EXECUTE format($fmt$
    CREATE TEMP TABLE %I AS
    SELECT %s, %s AS nk_hash, count(*)::bigint AS n
    FROM public.%I l
    GROUP BY %s HAVING count(*) > 1
  $fmt$, delta_ctl.duplicate_table_name(p_table, 'local'), array_to_string(v_local_selects, ', '),
        delta_ctl.nk_hash_expr(v_local_exprs), p_table, v_group_by);
  EXECUTE delta_ctl.nk_hash_index_sql(v_stage_dup);
  EXECUTE delta_ctl.nk_hash_index_sql(v_local_dup);
  EXECUTE delta_ctl.analyze_sql(v_stage_dup);
  EXECUTE delta_ctl.analyze_sql(v_local_dup);

  v_sql := format($fmt$
    WITH ambiguous AS (
      SELECT s._delta_row_id,
             %s AS staged_pk,
             CASE
               WHEN sd.n IS NOT NULL AND ld.n IS NOT NULL THEN format('duplicate NK in staged dump (%%s rows) and local table (%%s rows)', sd.n, ld.n)
               WHEN sd.n IS NOT NULL THEN format('duplicate NK in staged dump (%%s rows)', sd.n)
               ELSE format('duplicate NK in local table (%%s rows)', ld.n)
             END AS reason
      FROM delta_stage.%I s
      %s
      LEFT JOIN %s sd ON %s
      LEFT JOIN %s ld ON %s
      WHERE NOT (%s)
        AND (sd.n IS NOT NULL OR ld.n IS NOT NULL)
    )
    INSERT INTO delta_diff.%I (_delta_row_id, staged_pk, class, block_reason)
    SELECT _delta_row_id, staged_pk, 'AMBIGUOUS_NK', reason -- NOSONAR
    FROM ambiguous
    ON CONFLICT (_delta_row_id) DO UPDATE
      SET class = EXCLUDED.class, block_reason = EXCLUDED.block_reason
  $fmt$, v_staged_pk, p_table, v_stage_join, v_stage_dup, v_stage_dup_join,
        v_local_dup, v_local_dup_join, v_parent_pending, delta_ctl.class_table_name(p_table));

  EXECUTE v_sql;
END;
$$;

CREATE OR REPLACE FUNCTION delta_ctl.classify_nk_table(p_table text, p_fk_temp text DEFAULT NULL)
RETURNS void
LANGUAGE plpgsql
AS $$
DECLARE
  v_cfg delta_ctl.table_config%ROWTYPE;
  v_join text;
  v_join_residual text;
  v_stage_nk_exprs text[];
  v_fk_join text := '';
  v_fk_alias text := NULL;
  v_staged_pk text;
  v_local_pk text;
  v_compare_cols text[];
  v_stage_compare_exprs text[] := '{}';
  v_local_compare_exprs text[] := '{}';
  v_compare_equal text;
  v_changed_array text;
  v_parent_pending text;
  v_col text;
  v_sql text;
  v_started timestamptz;
BEGIN
  SELECT * INTO v_cfg FROM delta_ctl.table_config WHERE table_name = p_table;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'missing table_config row for %', p_table;
  END IF;

  IF p_fk_temp IS NOT NULL THEN
    v_fk_alias := 'fk';
    v_fk_join := delta_ctl.stage_fk_join(p_fk_temp);
  END IF;

  v_started := delta_ctl.phase_notice(p_table, 'create_class_table');
  PERFORM delta_ctl.create_class_table(p_table);
  PERFORM delta_ctl.phase_notice(p_table, 'create_class_table', v_started);

  v_started := delta_ctl.phase_notice(p_table, 'detect_ambiguity');
  PERFORM delta_ctl.detect_ambiguity(p_table, p_fk_temp);
  PERFORM delta_ctl.phase_notice(p_table, 'detect_ambiguity', v_started);

  v_stage_nk_exprs := delta_ctl.effective_stage_nk_exprs(p_table, v_fk_alias);
  v_join_residual := delta_ctl.null_safe_join(v_cfg.nk_local_exprs, v_stage_nk_exprs);
  v_join := format('(%s) = (%s) AND %s',
    delta_ctl.nk_hash_expr(v_cfg.nk_local_exprs),
    delta_ctl.nk_hash_expr(v_stage_nk_exprs),
    v_join_residual);
  v_staged_pk := CASE WHEN v_cfg.pk_col IS NULL THEN delta_ctl.null_bigint_expr() ELSE format('s.%I::bigint', v_cfg.pk_col) END;
  v_local_pk := CASE WHEN v_cfg.pk_col IS NULL THEN delta_ctl.null_bigint_expr() ELSE format('l.%I::bigint', v_cfg.pk_col) END;
  v_parent_pending := delta_ctl.parent_pending_expr(p_table, v_fk_alias);
  v_compare_cols := delta_ctl.compare_columns(p_table);

  IF array_length(v_compare_cols, 1) IS NULL THEN
    v_compare_equal := 'true';
    v_changed_array := 'NULL::text[]';
  ELSE
    FOREACH v_col IN ARRAY v_compare_cols LOOP
      v_stage_compare_exprs := v_stage_compare_exprs || delta_ctl.stage_compare_expr(p_table, v_col, v_fk_alias);
      v_local_compare_exprs := v_local_compare_exprs || delta_ctl.local_compare_expr(v_col);
    END LOOP;
    v_compare_equal := format('%s IS NOT DISTINCT FROM %s',
      delta_ctl.jsonb_array_expr(v_stage_compare_exprs),
      delta_ctl.jsonb_array_expr(v_local_compare_exprs));
    v_changed_array := 'array_remove(ARRAY[' || array_to_string(ARRAY(
      SELECT format('CASE WHEN %s IS DISTINCT FROM %s THEN %L END',
                    delta_ctl.stage_compare_expr(p_table, c, v_fk_alias), delta_ctl.local_compare_expr(c), c)
      FROM unnest(v_compare_cols) AS c
    ), ', ') || '], NULL)';
  END IF;

  v_sql := format($fmt$
    INSERT INTO delta_diff.%I (_delta_row_id, staged_pk, local_pk, local_ctid, class, changed_cols, parent_pending)
    SELECT s._delta_row_id,
           %s AS staged_pk,
           %s AS local_pk,
           l.ctid AS local_ctid,
           CASE
             WHEN (%s) THEN 'NEW' -- NOSONAR
             WHEN l.ctid IS NULL THEN 'NEW'
             WHEN %s THEN 'UNCHANGED' -- NOSONAR
             WHEN %s THEN 'CHANGED_LOCAL_NEWER' -- NOSONAR
             ELSE 'CHANGED' -- NOSONAR
           END AS class,
           CASE WHEN (%s) OR l.ctid IS NULL OR %s THEN NULL::text[] ELSE %s END AS changed_cols,
           (%s) AS parent_pending
    FROM delta_stage.%I s
    %s
    LEFT JOIN public.%I l ON %s
    WHERE NOT EXISTS (
      SELECT 1 FROM delta_diff.%I d WHERE d._delta_row_id = s._delta_row_id
    )
  $fmt$, delta_ctl.class_table_name(p_table), v_staged_pk, v_local_pk, v_parent_pending,
        v_compare_equal,
        CASE WHEN v_cfg.has_last_modified THEN 'l.last_modified > s.last_modified' ELSE delta_ctl.false_expr() END,
        v_parent_pending, v_compare_equal, v_changed_array, v_parent_pending,
        p_table, v_fk_join, p_table, v_join, delta_ctl.class_table_name(p_table));

  v_started := delta_ctl.phase_notice(p_table, 'main_classify_insert');
  EXECUTE v_sql;
  PERFORM delta_ctl.phase_notice(p_table, 'main_classify_insert', v_started);
END;
$$;

CREATE OR REPLACE FUNCTION delta_ctl.auth_component_hash_expr(p_alias text, p_parent_expr text)
RETURNS text
LANGUAGE plpgsql
AS $$
DECLARE
  v_exprs text[] := ARRAY[p_parent_expr];
  v_col text;
BEGIN
  FOR v_col IN
    SELECT a.attname
    FROM pg_attribute a
    WHERE a.attrelid = 'public.auth_component_operation'::regclass
      AND a.attnum > 0
      AND NOT a.attisdropped
      AND a.attname NOT IN ('id', 'auth_processing_id')
    ORDER BY a.attnum
  LOOP
    v_exprs := v_exprs || format('%s.%I', p_alias, v_col);
  END LOOP;

  RETURN 'md5(' || delta_ctl.jsonb_array_expr(v_exprs) || '::text)';
END;
$$;

CREATE OR REPLACE FUNCTION delta_ctl.classify_auth_component_operation()
RETURNS void
LANGUAGE plpgsql
AS $$
DECLARE
  c_new_pattern CONSTANT text := 'NEW%';
  v_stage_hash text;
  v_local_hash text;
  v_sql text;
BEGIN
  PERFORM delta_ctl.create_class_table(delta_ctl.auth_component_op_table());

  IF to_regclass('delta_map.auth_processing_id_map') IS NULL THEN
    EXECUTE $sql$
      INSERT INTO delta_diff.auth_component_operation_class (_delta_row_id, staged_pk, class, block_reason)
      SELECT s._delta_row_id, s.id::bigint, 'BLOCKED_FK', 'auth_processing map not available' -- NOSONAR
      FROM delta_stage.auth_component_operation s
    $sql$;
    RETURN;
  END IF;

  v_stage_hash := delta_ctl.auth_component_hash_expr('s', 'apm.local_id');
  v_local_hash := delta_ctl.auth_component_hash_expr('l', 'l.auth_processing_id');

  v_sql := format($fmt$
    WITH staged AS (
      SELECT s._delta_row_id,
             s.id::bigint AS staged_pk,
             apm.local_id AS parent_local_id,
             apm.disposition AS parent_disposition,
             %s AS content_hash
      FROM delta_stage.auth_component_operation s
      LEFT JOIN delta_map.auth_processing_id_map apm
        ON apm.staged_id = s.auth_processing_id
    ), relevant_parent_ids AS (
      SELECT DISTINCT parent_local_id
      FROM staged
      WHERE parent_disposition = 'MATCHED' -- NOSONAR
        AND parent_local_id IS NOT NULL
    ), local_hashes AS (
      SELECT min(local_pk)::bigint AS local_pk, content_hash
      FROM (
        SELECT l.id::bigint AS local_pk,
               %s AS content_hash
        FROM public.auth_component_operation l
        JOIN relevant_parent_ids rp ON rp.parent_local_id = l.auth_processing_id
      ) h
      GROUP BY content_hash
    )
    INSERT INTO delta_diff.auth_component_operation_class
      (_delta_row_id, staged_pk, local_pk, class, parent_pending, block_reason)
    SELECT st._delta_row_id,
           st.staged_pk,
           lh.local_pk,
           CASE
             WHEN st.parent_disposition IS NULL THEN 'BLOCKED_FK'
             WHEN st.parent_disposition LIKE %L THEN 'NEW'
             WHEN st.parent_disposition <> 'MATCHED' THEN 'BLOCKED_PARENT' -- NOSONAR
             WHEN lh.local_pk IS NULL THEN 'NEW'
             ELSE 'UNCHANGED'
           END AS class,
           COALESCE(st.parent_disposition LIKE %L, false) AS parent_pending,
           CASE
             WHEN st.parent_disposition IS NULL THEN 'auth_processing parent not present'
             WHEN st.parent_disposition <> 'MATCHED' AND st.parent_disposition NOT LIKE %L
               THEN 'auth_processing parent blocked: ' || st.parent_disposition
           END AS block_reason
    FROM staged st
    LEFT JOIN local_hashes lh
      ON lh.content_hash = st.content_hash
$fmt$, v_stage_hash, v_local_hash, c_new_pattern, c_new_pattern, c_new_pattern);

  EXECUTE v_sql;
END;
$$;

CREATE OR REPLACE FUNCTION delta_ctl.build_id_map(p_table text)
RETURNS void
LANGUAGE plpgsql
AS $$
DECLARE
  v_cfg delta_ctl.table_config%ROWTYPE;
  v_map_name text;
  v_dup_count bigint;
  v_sql text;
BEGIN
  SELECT * INTO v_cfg FROM delta_ctl.table_config WHERE table_name = p_table;
  IF NOT FOUND OR v_cfg.pk_col IS NULL OR NOT delta_ctl.stage_table_exists(p_table) THEN
    RETURN;
  END IF;

  v_map_name := delta_ctl.map_table_name(p_table);

  EXECUTE format('SELECT count(*) FROM (SELECT %I FROM delta_stage.%I WHERE %I IS NOT NULL GROUP BY 1 HAVING count(*) > 1) x',
                 v_cfg.pk_col, p_table, v_cfg.pk_col)
    INTO v_dup_count;
  IF v_dup_count > 0 THEN
    RAISE EXCEPTION 'duplicate staged primary key values in %.%', 'delta_stage', p_table;
  END IF;

  EXECUTE format('DROP TABLE IF EXISTS delta_map.%I', v_map_name);
  EXECUTE format('CREATE TABLE delta_map.%I (staged_id bigint PRIMARY KEY, local_id bigint NULL, disposition text NOT NULL)', v_map_name);

  v_sql := format($fmt$
    INSERT INTO delta_map.%I (staged_id, local_id, disposition)
    SELECT s.%I::bigint AS staged_id,
           CASE
             WHEN d.class IN ('BLOCKED_FK', 'AMBIGUOUS_NK') THEN NULL::bigint
             WHEN d.local_pk IS NOT NULL THEN d.local_pk
             WHEN d.class = 'NEW' AND NOT EXISTS (SELECT 1 FROM public.%I l2 WHERE l2.%I = s.%I) THEN s.%I::bigint
             ELSE NULL::bigint
           END AS local_id,
           CASE
             WHEN d.class IN ('BLOCKED_FK', 'AMBIGUOUS_NK') THEN d.class
             WHEN d.local_pk IS NOT NULL THEN 'MATCHED'
             WHEN d.class = 'NEW' AND NOT EXISTS (SELECT 1 FROM public.%I l2 WHERE l2.%I = s.%I) THEN 'NEW_PRESERVED'
             WHEN d.class = 'NEW' THEN 'NEW_REALLOCATED'
             ELSE d.class
           END AS disposition
    FROM delta_stage.%I s
    JOIN delta_diff.%I d ON d._delta_row_id = s._delta_row_id
    WHERE s.%I IS NOT NULL
      AND d.class IN ('NEW', 'CHANGED', 'CHANGED_LOCAL_NEWER', 'UNCHANGED', 'BLOCKED_FK')
  $fmt$, v_map_name, v_cfg.pk_col, p_table, v_cfg.pk_col, v_cfg.pk_col, v_cfg.pk_col,
        p_table, v_cfg.pk_col, v_cfg.pk_col, p_table, delta_ctl.class_table_name(p_table), v_cfg.pk_col);

  EXECUTE v_sql;
END;
$$;

CREATE OR REPLACE FUNCTION delta_ctl.detect_external_fk_blocking(p_table text)
RETURNS void
LANGUAGE plpgsql
AS $$
DECLARE
  r record;
  v_target text;
  v_target_table text;
  v_target_col text;
  v_sql text;
BEGIN
  FOR r IN
    SELECT key AS fk_col, value AS fk_target
    FROM delta_ctl.table_config c, jsonb_each_text(c.fk_map)
    WHERE c.table_name = p_table AND value LIKE delta_ctl.external_fk_pattern()
  LOOP
    v_target := substring(r.fk_target FROM 10);
    v_target_table := split_part(v_target, '.', 1);
    v_target_col := split_part(v_target, '.', 2);
    PERFORM delta_ctl.assert_identifier(v_target_table, 'external table');
    PERFORM delta_ctl.assert_identifier(v_target_col, 'external column');

    v_sql := format($fmt$
      UPDATE delta_diff.%I d
      SET class = 'BLOCKED_FK',
          block_reason = concat_ws('; ', d.block_reason, format('%I %%s not in local extract', s.%I))
      FROM delta_stage.%I s
      WHERE d._delta_row_id = s._delta_row_id
        AND d.class IN ('NEW', 'CHANGED', 'CHANGED_LOCAL_NEWER')
        AND s.%I IS NOT NULL
        AND NOT EXISTS (
          SELECT 1 FROM public.%I ext WHERE ext.%I = s.%I
        )
    $fmt$, delta_ctl.class_table_name(p_table), r.fk_col, r.fk_col, p_table, r.fk_col, v_target_table, v_target_col, r.fk_col);

    EXECUTE v_sql;
  END LOOP;
END;
$$;

CREATE OR REPLACE FUNCTION delta_ctl.detect_preserved_fk_blocking(p_table text, p_fk_temp text DEFAULT NULL)
RETURNS void
LANGUAGE plpgsql
AS $$
DECLARE
  r record;
  v_sql text;
  v_fk_temp text;
BEGIN
  v_fk_temp := p_fk_temp;
  IF v_fk_temp IS NULL THEN
    v_fk_temp := delta_ctl.create_stage_fk_map(p_table);
  END IF;
  IF v_fk_temp IS NULL THEN
    RETURN;
  END IF;

  FOR r IN
    SELECT key AS fk_col, value AS parent_table
    FROM delta_ctl.table_config c, jsonb_each_text(c.fk_map)
    WHERE c.table_name = p_table AND value NOT LIKE delta_ctl.external_fk_pattern()
  LOOP
    PERFORM delta_ctl.assert_identifier(r.parent_table, delta_ctl.parent_table_kind());

    v_sql := format($fmt$
      UPDATE delta_diff.%I d
      SET class = 'BLOCKED_FK',
          changed_cols = NULL,
          block_reason = concat_ws('; ', d.block_reason, format('%I %%s has no safe mapped/local %s parent', s.%I))
      FROM delta_stage.%I s
      JOIN %s fk ON fk._delta_row_id = s._delta_row_id
      WHERE d._delta_row_id = s._delta_row_id
        AND d.class IN ('NEW', 'CHANGED', 'CHANGED_LOCAL_NEWER', 'UNCHANGED')
        AND s.%I IS NOT NULL
        AND NOT COALESCE(fk.%I, false)
        AND fk.%I IS NULL
    $fmt$, delta_ctl.class_table_name(p_table), r.fk_col, r.parent_table, r.fk_col,
          p_table, v_fk_temp, r.fk_col, delta_ctl.parent_pending_col(r.fk_col), delta_ctl.local_id_col(r.fk_col));

    EXECUTE v_sql;
  END LOOP;
END;
$$;

CREATE OR REPLACE FUNCTION delta_ctl.record_class_counts(p_table text)
RETURNS void
LANGUAGE plpgsql
AS $$
BEGIN
  IF NOT delta_ctl.stage_table_exists(p_table) THEN
    RETURN;
  END IF;

  EXECUTE format($fmt$
    INSERT INTO delta_ctl.run_counts(table_name, count_name, row_count)
    SELECT %L, class, count(*)
    FROM delta_diff.%I
    GROUP BY class
    ON CONFLICT (table_name, count_name) DO UPDATE
      SET row_count = EXCLUDED.row_count, created_at = now()
  $fmt$, p_table, delta_ctl.class_table_name(p_table));
END;
$$;

CREATE OR REPLACE FUNCTION delta_ctl.record_local_only_count(p_table text, p_fk_temp text DEFAULT NULL)
RETURNS void
LANGUAGE plpgsql
AS $$
DECLARE
  v_cfg delta_ctl.table_config%ROWTYPE;
  v_join text;
  v_sql text;
  v_local_hash text;
  v_stage_hash text;
  v_stage_exprs text[];
  v_stage_selects text[] := '{}';
  v_stage_keys text;
  v_stage_join text := '';
  v_fk_alias text := NULL;
  v_i int;
BEGIN
  SELECT * INTO v_cfg FROM delta_ctl.table_config WHERE table_name = p_table;
  IF NOT FOUND THEN
    RETURN;
  END IF;

  IF NOT delta_ctl.stage_table_exists(p_table) THEN
    RETURN;
  END IF;

  IF v_cfg.match_mode = delta_ctl.hash_parent_mode() THEN
    IF p_table <> delta_ctl.auth_component_op_table() THEN
      RETURN;
    END IF;
    IF to_regclass('delta_map.auth_processing_id_map') IS NULL THEN
      INSERT INTO delta_ctl.run_counts(table_name, count_name, row_count)
      VALUES (p_table, 'LOCAL_ONLY', 0) -- NOSONAR
      ON CONFLICT (table_name, count_name) DO UPDATE
        SET row_count = EXCLUDED.row_count, created_at = now();
      RETURN;
    END IF;

    v_local_hash := delta_ctl.auth_component_hash_expr('l', 'l.auth_processing_id');
    v_stage_hash := delta_ctl.auth_component_hash_expr('s', 'apm.local_id');
    v_sql := format($fmt$
      INSERT INTO delta_ctl.run_counts(table_name, count_name, row_count)
      WITH relevant_parent_ids AS (
        SELECT DISTINCT local_id AS parent_local_id
        FROM delta_map.auth_processing_id_map
        WHERE disposition = 'MATCHED'
          AND local_id IS NOT NULL
      ), stage_hashes AS (
        SELECT DISTINCT %s AS content_hash
        FROM delta_stage.auth_component_operation s
        JOIN delta_map.auth_processing_id_map apm
          ON apm.staged_id = s.auth_processing_id
        WHERE apm.disposition = 'MATCHED'
          AND apm.local_id IS NOT NULL
      )
      SELECT %L, 'LOCAL_ONLY', count(*)
      FROM public.auth_component_operation l
      JOIN relevant_parent_ids rp ON rp.parent_local_id = l.auth_processing_id
      WHERE NOT EXISTS (
        SELECT 1 FROM stage_hashes sh
        WHERE sh.content_hash = %s
      )
      ON CONFLICT (table_name, count_name) DO UPDATE
        SET row_count = EXCLUDED.row_count, created_at = now()
    $fmt$, v_stage_hash, p_table, v_local_hash);
    EXECUTE v_sql;
    RETURN;
  END IF;

  IF p_fk_temp IS NOT NULL THEN
    v_fk_alias := 'fk';
    v_stage_join := delta_ctl.stage_fk_join(p_fk_temp);
  END IF;

  v_stage_exprs := delta_ctl.effective_stage_nk_exprs(p_table, v_fk_alias);
  IF COALESCE(array_length(v_stage_exprs, 1), 0) = 0 THEN
    RAISE NOTICE 'delta_restore table=% phase=record_local_only_count skipped reason=no_nk_exprs', p_table;
    RETURN;
  END IF;

  FOR v_i IN 1..array_length(v_stage_exprs, 1) LOOP
    v_stage_selects := v_stage_selects || delta_ctl.aliased_expr(v_stage_exprs[v_i], 'k' || v_i);
  END LOOP;

  v_stage_keys := delta_ctl.temp_rel('delta_stage_keys_' || p_table);
  v_stage_hash := delta_ctl.nk_hash_expr(v_stage_exprs);
  v_local_hash := delta_ctl.nk_hash_expr(v_cfg.nk_local_exprs);
  v_join := array_to_string(ARRAY(
    SELECT format('sk.%I IS NOT DISTINCT FROM (%s)', 'k' || i, v_cfg.nk_local_exprs[i])
    FROM generate_subscripts(v_stage_exprs, 1) AS i
  ), delta_ctl.and_separator());
  v_join := format('sk.nk_hash = (%s) AND %s', v_local_hash, v_join);

  EXECUTE delta_ctl.drop_table_sql(v_stage_keys);
  EXECUTE format($fmt$
    CREATE TEMP TABLE %I AS
    SELECT DISTINCT %s, %s AS nk_hash
    FROM delta_stage.%I s
    %s
  $fmt$, 'delta_stage_keys_' || p_table, array_to_string(v_stage_selects, ', '), v_stage_hash, p_table, v_stage_join);
  EXECUTE delta_ctl.nk_hash_index_sql(v_stage_keys);
  EXECUTE delta_ctl.analyze_sql(v_stage_keys);

  v_sql := format($fmt$
    INSERT INTO delta_ctl.run_counts(table_name, count_name, row_count)
    SELECT %L, 'LOCAL_ONLY', count(*)
    FROM public.%I l
    WHERE NOT EXISTS (
      SELECT 1 FROM %s sk WHERE %s
    )
    ON CONFLICT (table_name, count_name) DO UPDATE
      SET row_count = EXCLUDED.row_count, created_at = now()
  $fmt$, p_table, p_table, v_stage_keys, v_join);
  EXECUTE v_sql;
END;
$$;

CREATE OR REPLACE FUNCTION delta_ctl.classify_table(p_table text)
RETURNS void
LANGUAGE plpgsql
AS $$
DECLARE
  v_cfg delta_ctl.table_config%ROWTYPE;
  v_fk_temp text;
  v_started timestamptz;
  v_table_started timestamptz;
BEGIN
  SELECT * INTO v_cfg FROM delta_ctl.table_config WHERE table_name = p_table;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'missing table_config row for %', p_table;
  END IF;

  IF NOT delta_ctl.stage_table_exists(p_table) THEN
    RETURN;
  END IF;

  v_table_started := delta_ctl.phase_notice(p_table, 'classify_table');

  v_started := delta_ctl.phase_notice(p_table, 'prepare_fk_map');
  v_fk_temp := delta_ctl.create_stage_fk_map(p_table);
  PERFORM delta_ctl.phase_notice(p_table, 'prepare_fk_map', v_started);

  IF v_cfg.match_mode = delta_ctl.hash_parent_mode() THEN
    IF p_table <> delta_ctl.auth_component_op_table() THEN
      RAISE EXCEPTION 'unsupported hash_parent table: %', p_table;
    END IF;
    v_started := delta_ctl.phase_notice(p_table, 'classify_auth_component_operation');
    PERFORM delta_ctl.classify_auth_component_operation();
    PERFORM delta_ctl.phase_notice(p_table, 'classify_auth_component_operation', v_started);
  ELSE
    v_started := delta_ctl.phase_notice(p_table, 'classify_nk_table');
    PERFORM delta_ctl.classify_nk_table(p_table, v_fk_temp);
    PERFORM delta_ctl.phase_notice(p_table, 'classify_nk_table', v_started);
  END IF;

  v_started := delta_ctl.phase_notice(p_table, 'detect_external_fk_blocking');
  PERFORM delta_ctl.detect_external_fk_blocking(p_table);
  PERFORM delta_ctl.phase_notice(p_table, 'detect_external_fk_blocking', v_started);

  v_started := delta_ctl.phase_notice(p_table, 'detect_preserved_fk_blocking');
  PERFORM delta_ctl.detect_preserved_fk_blocking(p_table, v_fk_temp);
  PERFORM delta_ctl.phase_notice(p_table, 'detect_preserved_fk_blocking', v_started);

  v_started := delta_ctl.phase_notice(p_table, 'build_id_map');
  PERFORM delta_ctl.build_id_map(p_table);
  PERFORM delta_ctl.phase_notice(p_table, 'build_id_map', v_started);

  v_started := delta_ctl.phase_notice(p_table, 'record_class_counts');
  PERFORM delta_ctl.record_class_counts(p_table);
  PERFORM delta_ctl.phase_notice(p_table, 'record_class_counts', v_started);

  v_started := delta_ctl.phase_notice(p_table, 'record_local_only_count');
  PERFORM delta_ctl.record_local_only_count(p_table, v_fk_temp);
  PERFORM delta_ctl.phase_notice(p_table, 'record_local_only_count', v_started);

  PERFORM delta_ctl.phase_notice(p_table, 'classify_table', v_table_started);
END;
$$;

CREATE OR REPLACE FUNCTION delta_ctl.run_preview_classification()
RETURNS void
LANGUAGE plpgsql
AS $$
DECLARE
  r record;
  v_started timestamptz;
BEGIN
  v_started := delta_ctl.phase_notice(NULL, 'run_preview_classification');

  DELETE FROM delta_ctl.run_counts
  WHERE count_name NOT IN ('STAGED', 'SKIPPED_ABSENT'); -- NOSONAR
  TRUNCATE delta_ctl.apply_counts;
  TRUNCATE delta_ctl.touched_tables;
  TRUNCATE delta_ctl.dependency_violations;

  PERFORM delta_ctl.complete_table_config();

  FOR r IN
    SELECT table_name
    FROM delta_ctl.table_config
    ORDER BY load_phase, table_name
  LOOP
    PERFORM delta_ctl.classify_table(r.table_name);
  END LOOP;

  PERFORM delta_ctl.phase_notice(NULL, 'run_preview_classification', v_started);
END;
$$;

CREATE OR REPLACE FUNCTION delta_ctl.fn_counts()
RETURNS TABLE(table_name text, count_name text, row_count bigint, load_phase int)
LANGUAGE sql
AS $$
SELECT rc.table_name, rc.count_name, rc.row_count, tc.load_phase
FROM delta_ctl.run_counts rc
LEFT JOIN delta_ctl.table_config tc ON tc.table_name = rc.table_name
ORDER BY tc.load_phase ASC NULLS LAST, rc.table_name ASC, rc.count_name ASC;
$$;

CREATE OR REPLACE FUNCTION delta_ctl.tsv_escape(p_value text, p_max_len int DEFAULT 8192)
RETURNS text
LANGUAGE sql
IMMUTABLE PARALLEL SAFE
AS $$
SELECT CASE
  WHEN p_value IS NULL THEN E'\\N'
  ELSE regexp_replace(
    replace(replace(replace(replace(replace(
      CASE WHEN length(p_value) > GREATEST(p_max_len, 1)
        THEN left(p_value, GREATEST(p_max_len, 1)) || '…[truncated]'
        ELSE p_value END,
      E'\\', E'\\\\'), E'\t', E'\\t'), E'\n', E'\\n'), E'\r', E'\\r'), chr(27), '␛'),
    '[[:cntrl:]]', '�', 'g')
END;
$$;

CREATE OR REPLACE FUNCTION delta_ctl.display_text(p_value text, p_max_len int DEFAULT 60)
RETURNS text
LANGUAGE plpgsql
IMMUTABLE PARALLEL SAFE
AS $$
DECLARE
  v_value text;
BEGIN
  IF p_value IS NULL THEN
    RETURN 'NULL';
  END IF;
  v_value := replace(replace(replace(replace(
    p_value, E'\n', '␤'), E'\t', '␉'), E'\r', '␍'), chr(27), '␛');
  v_value := regexp_replace(v_value, '[[:cntrl:]]', '�', 'g');
  IF length(v_value) > GREATEST(p_max_len, 1) THEN
    v_value := left(v_value, GREATEST(p_max_len, 1)) || '…';
  END IF;
  RETURN v_value;
END;
$$;

CREATE OR REPLACE FUNCTION delta_ctl.display_value(p_row jsonb, p_col text, p_max_len int DEFAULT 60)
RETURNS text
LANGUAGE plpgsql
IMMUTABLE PARALLEL SAFE
AS $$
BEGIN
  IF p_row IS NULL OR NOT (p_row ? p_col) OR p_row -> p_col = 'null'::jsonb THEN
    RETURN 'NULL';
  END IF;
  RETURN delta_ctl.display_text(COALESCE(p_row ->> p_col, ''), p_max_len);
END;
$$;

CREATE OR REPLACE FUNCTION delta_ctl.display_columns(p_table text)
RETURNS text[]
LANGUAGE plpgsql
AS $$
DECLARE
  v_cfg delta_ctl.table_config%ROWTYPE;
  v_cols text[];
  v_expr text;
  v_match text[];
BEGIN
  SELECT * INTO v_cfg FROM delta_ctl.table_config WHERE table_name = p_table;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'missing table_config row for %', p_table;
  END IF;
  IF array_length(v_cfg.nk_cols, 1) IS NOT NULL THEN
    RETURN v_cfg.nk_cols;
  END IF;
  FOREACH v_expr IN ARRAY v_cfg.nk_stage_exprs LOOP
    v_match := regexp_match(v_expr, '^s\\.([a-z_][a-z0-9_]*)$');
    IF v_match IS NOT NULL AND NOT (v_match[1] = ANY(COALESCE(v_cols, '{}'))) THEN
      v_cols := COALESCE(v_cols, '{}') || v_match[1];
    END IF;
  END LOOP;
  IF array_length(v_cols, 1) IS NOT NULL THEN
    RETURN v_cols;
  END IF;
  SELECT COALESCE(array_agg(attname ORDER BY attnum), '{}') INTO v_cols
  FROM (
    SELECT a.attname, a.attnum
    FROM pg_attribute a
    WHERE a.attrelid = delta_ctl.public_rel(p_table)::regclass
      AND a.attnum > 0 AND NOT a.attisdropped
      AND (v_cfg.pk_col IS NULL OR a.attname <> v_cfg.pk_col)
    ORDER BY a.attnum
    LIMIT 3
  ) q;
  RETURN v_cols;
END;
$$;

CREATE OR REPLACE FUNCTION delta_ctl.render_samples(p_table text, p_class text, p_limit int DEFAULT 20)
RETURNS SETOF text
LANGUAGE plpgsql
AS $$
DECLARE
  r record;
  v_cfg delta_ctl.table_config%ROWTYPE;
  v_sql text;
  v_local_join text;
  v_col text;
  v_cols text[];
  v_values text;
  v_line text;
  v_changed_count int;
  v_limit int := GREATEST(COALESCE(p_limit, 20), 0);
BEGIN
  PERFORM delta_ctl.assert_table_name(p_table);
  SELECT * INTO v_cfg FROM delta_ctl.table_config WHERE table_name = p_table;
  IF v_limit = 0 OR NOT FOUND
     OR to_regclass(format('delta_diff.%I', delta_ctl.class_table_name(p_table))) IS NULL THEN -- NOSONAR
    RETURN;
  END IF;

  v_cols := delta_ctl.display_columns(p_table);
  v_local_join := CASE
    WHEN v_cfg.pk_col IS NULL THEN 'LEFT JOIN public.' || quote_ident(p_table) || ' l ON l.ctid = d.local_ctid'
    ELSE format('LEFT JOIN public.%I l ON l.%I = d.local_pk', p_table, v_cfg.pk_col)
  END;
  v_sql := format($fmt$
    SELECT d._delta_row_id, d.staged_pk, d.local_pk, d.changed_cols,
           d.block_reason, d.parent_pending, to_jsonb(s) AS staged_json,
           to_jsonb(l) AS local_json
    FROM delta_diff.%I d
    JOIN delta_stage.%I s ON s._delta_row_id = d._delta_row_id
    %s
    WHERE d.class = $1
    ORDER BY d.staged_pk NULLS LAST, d._delta_row_id
    LIMIT $2
  $fmt$, delta_ctl.class_table_name(p_table), p_table, v_local_join);

  FOR r IN EXECUTE v_sql USING p_class, v_limit LOOP
    v_values := '';
    FOREACH v_col IN ARRAY v_cols LOOP
      v_values := v_values || format(' · %s=%s', v_col,
        delta_ctl.display_value(r.staged_json, v_col, 40));
    END LOOP;
    v_line := format('▸ %s%srow %s%s%s',
      CASE WHEN v_cfg.pk_col IS NOT NULL THEN format('id %s · ', COALESCE(r.staged_pk::text, '—')) ELSE '' END,
      '',
      r._delta_row_id,
      v_values,
      CASE WHEN r.parent_pending THEN ' · parent pending' ELSE '' END
        || CASE WHEN r.block_reason IS NOT NULL
             THEN ' · ' || delta_ctl.display_text(r.block_reason, 80) ELSE '' END);
    IF length(v_line) > 220 THEN
      v_line := left(v_line, 219) || '…';
    END IF;
    RETURN NEXT v_line;
    IF r.changed_cols IS NOT NULL THEN
      v_changed_count := 0;
      FOREACH v_col IN ARRAY r.changed_cols LOOP
        EXIT WHEN v_changed_count >= 5;
        RETURN NEXT format('    changed %s: %s → %s', v_col,
          delta_ctl.display_value(r.local_json, v_col, 60),
          delta_ctl.display_value(r.staged_json, v_col, 60));
        v_changed_count := v_changed_count + 1;
      END LOOP;
    END IF;
  END LOOP;
END;
$$;

CREATE OR REPLACE FUNCTION delta_ctl.render_new_rows_tsv(p_table text, p_limit int DEFAULT 10000)
RETURNS SETOF text
LANGUAGE plpgsql
AS $$
DECLARE
  v_cfg delta_ctl.table_config%ROWTYPE;
  v_cols text[];
  v_col text;
  v_sql text;
  v_line text;
  r record;
  v_limit int := GREATEST(COALESCE(p_limit, 10000), 0);
BEGIN
  PERFORM delta_ctl.assert_table_name(p_table);
  SELECT * INTO v_cfg FROM delta_ctl.table_config WHERE table_name = p_table;
  IF NOT FOUND OR NOT delta_ctl.stage_table_exists(p_table) THEN RETURN; END IF;
  SELECT array_agg(a.attname ORDER BY a.attnum) INTO v_cols
  FROM pg_attribute a
  WHERE a.attrelid = delta_ctl.public_rel(p_table)::regclass
    AND a.attnum > 0 AND NOT a.attisdropped;
  RETURN NEXT 'selector_id' || E'\t' || 'delta_row_id' || E'\t' || array_to_string(v_cols, E'\t'); -- NOSONAR
  v_sql := format($fmt$
    SELECT d.staged_pk, d._delta_row_id, to_jsonb(s) AS staged_json
    FROM delta_diff.%I d
    JOIN delta_stage.%I s ON s._delta_row_id = d._delta_row_id
    WHERE d.class = 'NEW'
    ORDER BY d.staged_pk NULLS LAST, d._delta_row_id
    LIMIT $1
  $fmt$, delta_ctl.class_table_name(p_table), p_table);
  FOR r IN EXECUTE v_sql USING v_limit LOOP
    v_line := delta_ctl.tsv_escape(COALESCE(r.staged_pk, r._delta_row_id)::text)
      || E'\t' || r._delta_row_id::text;
    FOREACH v_col IN ARRAY v_cols LOOP
      v_line := v_line || E'\t' || delta_ctl.tsv_escape(r.staged_json ->> v_col);
    END LOOP;
    RETURN NEXT v_line;
  END LOOP;
  IF (SELECT row_count FROM delta_ctl.run_counts
      WHERE table_name = p_table AND count_name = 'NEW') > v_limit THEN
    RETURN NEXT delta_ctl.truncated_rows_marker(v_limit);
  END IF;
END;
$$;

CREATE OR REPLACE FUNCTION delta_ctl.render_changed_rows_tsv(p_table text, p_limit int DEFAULT 10000)
RETURNS SETOF text
LANGUAGE plpgsql
AS $$
DECLARE
  v_cfg delta_ctl.table_config%ROWTYPE;
  v_local_join text;
  v_sql text;
  v_col text;
  r record;
  v_limit int := GREATEST(COALESCE(p_limit, 10000), 0);
BEGIN
  PERFORM delta_ctl.assert_table_name(p_table);
  SELECT * INTO v_cfg FROM delta_ctl.table_config WHERE table_name = p_table;
  IF NOT FOUND OR NOT delta_ctl.stage_table_exists(p_table) THEN RETURN; END IF;
  RETURN NEXT 'selector_id' || E'\t' || 'delta_row_id' || E'\t' || 'local_pk' -- NOSONAR
    || E'\t' || delta_ctl.class_header() || E'\t' || 'column' || E'\t' || 'local_value' || E'\t' || 'dump_value';
  v_local_join := CASE
    WHEN v_cfg.pk_col IS NULL THEN format('JOIN public.%I l ON l.ctid = d.local_ctid', p_table)
    ELSE format('JOIN public.%I l ON l.%I = d.local_pk', p_table, v_cfg.pk_col)
  END;
  v_sql := format($fmt$
    WITH ranked AS (
      SELECT d.staged_pk, d._delta_row_id, d.local_pk, d.class, d.changed_cols,
             to_jsonb(s) AS staged_json, to_jsonb(l) AS local_json,
             row_number() OVER (
               PARTITION BY d.class ORDER BY d.staged_pk NULLS LAST, d._delta_row_id
             ) AS class_row_number
      FROM delta_diff.%I d
      JOIN delta_stage.%I s ON s._delta_row_id = d._delta_row_id
      %s
      WHERE d.class IN ('CHANGED', 'CHANGED_LOCAL_NEWER')
    )
    SELECT staged_pk, _delta_row_id, local_pk, class, changed_cols, staged_json, local_json
    FROM ranked
    WHERE class_row_number <= $1
    ORDER BY staged_pk NULLS LAST, _delta_row_id
  $fmt$, delta_ctl.class_table_name(p_table), p_table, v_local_join);
  FOR r IN EXECUTE v_sql USING v_limit LOOP
    FOREACH v_col IN ARRAY COALESCE(r.changed_cols, '{}') LOOP
      RETURN NEXT delta_ctl.tsv_escape(COALESCE(r.staged_pk, r._delta_row_id)::text)
        || E'\t' || r._delta_row_id::text
        || E'\t' || delta_ctl.tsv_escape(r.local_pk::text)
        || E'\t' || r.class
        || E'\t' || delta_ctl.tsv_escape(v_col)
        || E'\t' || delta_ctl.tsv_escape(r.local_json ->> v_col)
        || E'\t' || delta_ctl.tsv_escape(r.staged_json ->> v_col);
    END LOOP;
  END LOOP;
  IF EXISTS (SELECT 1 FROM delta_ctl.run_counts
      WHERE table_name = p_table AND count_name IN ('CHANGED', 'CHANGED_LOCAL_NEWER')
        AND row_count > v_limit) THEN
    RETURN NEXT delta_ctl.truncated_rows_marker(v_limit);
  END IF;
END;
$$;

CREATE OR REPLACE FUNCTION delta_ctl.render_blocked_rows_tsv(p_table text, p_limit int DEFAULT 10000)
RETURNS SETOF text
LANGUAGE plpgsql
AS $$
DECLARE
  v_cols text[];
  v_col text;
  v_sql text;
  v_line text;
  r record;
  v_limit int := GREATEST(COALESCE(p_limit, 10000), 0);
BEGIN
  PERFORM delta_ctl.assert_table_name(p_table);
  SELECT array_agg(a.attname ORDER BY a.attnum) INTO v_cols
  FROM pg_attribute a
  WHERE a.attrelid = delta_ctl.public_rel(p_table)::regclass
    AND a.attnum > 0 AND NOT a.attisdropped;
  RETURN NEXT 'selector_id' || E'\t' || 'delta_row_id' || E'\t' || delta_ctl.class_header()
    || E'\t' || array_to_string(v_cols, E'\t') || E'\t' || 'block_reason';
  v_sql := format($fmt$
    WITH ranked AS (
      SELECT d.staged_pk, d._delta_row_id, d.class, d.block_reason,
             to_jsonb(s) AS staged_json,
             row_number() OVER (
               PARTITION BY d.class ORDER BY d.staged_pk NULLS LAST, d._delta_row_id
             ) AS class_row_number
      FROM delta_diff.%I d
      JOIN delta_stage.%I s ON s._delta_row_id = d._delta_row_id
      WHERE d.class IN ('BLOCKED_FK', 'AMBIGUOUS_NK')
    )
    SELECT staged_pk, _delta_row_id, class, block_reason, staged_json
    FROM ranked
    WHERE class_row_number <= $1
    ORDER BY staged_pk NULLS LAST, _delta_row_id
  $fmt$, delta_ctl.class_table_name(p_table), p_table);
  FOR r IN EXECUTE v_sql USING v_limit LOOP
    v_line := delta_ctl.tsv_escape(COALESCE(r.staged_pk, r._delta_row_id)::text)
      || E'\t' || r._delta_row_id::text || E'\t' || r.class;
    FOREACH v_col IN ARRAY v_cols LOOP
      v_line := v_line || E'\t' || delta_ctl.tsv_escape(r.staged_json ->> v_col);
    END LOOP;
    RETURN NEXT v_line || E'\t' || delta_ctl.tsv_escape(r.block_reason);
  END LOOP;
  IF EXISTS (SELECT 1 FROM delta_ctl.run_counts
      WHERE table_name = p_table AND count_name IN ('BLOCKED_FK', 'AMBIGUOUS_NK')
        AND row_count > v_limit) THEN
    RETURN NEXT delta_ctl.truncated_rows_marker(v_limit);
  END IF;
END;
$$;

CREATE OR REPLACE FUNCTION delta_ctl.render_preview_lines(p_sample_size int DEFAULT 20)
RETURNS SETOF text
LANGUAGE plpgsql
AS $$
DECLARE
  c_table_hdr CONSTANT text := delta_ctl.table_kind();
  t record;
  c record;
  sample text;
  summary text;
BEGIN
  RETURN NEXT 'Class counts';
  RETURN NEXT '------------';
  RETURN NEXT format('%-36s %10s %10s %10s %18s %12s %13s %12s %12s',
    c_table_hdr, 'NEW', 'CHANGED', 'UNCHANGED', 'CHANGED_LOCAL_NEWER', 'BLOCKED_FK', 'AMBIGUOUS_NK', 'LOCAL_ONLY', 'SKIPPED');

  FOR t IN
    SELECT tc.table_name, tc.load_phase,
           COALESCE(max(rc.row_count) FILTER (WHERE rc.count_name = 'NEW'), 0) AS new_n,
           COALESCE(max(rc.row_count) FILTER (WHERE rc.count_name = 'CHANGED'), 0) AS changed_n,
           COALESCE(max(rc.row_count) FILTER (WHERE rc.count_name = 'UNCHANGED'), 0) AS unchanged_n,
           COALESCE(max(rc.row_count) FILTER (WHERE rc.count_name = 'CHANGED_LOCAL_NEWER'), 0) AS local_newer_n,
           COALESCE(max(rc.row_count) FILTER (WHERE rc.count_name = 'BLOCKED_FK'), 0) AS blocked_fk_n,
           COALESCE(max(rc.row_count) FILTER (WHERE rc.count_name = 'AMBIGUOUS_NK'), 0) AS ambiguous_n,
           COALESCE(max(rc.row_count) FILTER (WHERE rc.count_name = 'LOCAL_ONLY'), 0) AS local_only_n,
           COALESCE(max(rc.row_count) FILTER (WHERE rc.count_name = 'SKIPPED_ABSENT'), 0) AS skipped_n
    FROM delta_ctl.table_config tc
    LEFT JOIN delta_ctl.run_counts rc ON rc.table_name = tc.table_name
    GROUP BY tc.table_name, tc.load_phase
    ORDER BY tc.load_phase, tc.table_name
  LOOP
    RETURN NEXT format('%-36s %10s %10s %10s %18s %12s %13s %12s %12s',
      t.table_name, t.new_n, t.changed_n, t.unchanged_n, t.local_newer_n, t.blocked_fk_n, t.ambiguous_n, t.local_only_n, t.skipped_n);
  END LOOP;

  RETURN NEXT '';
  RETURN NEXT 'Samples';
  RETURN NEXT '-------';

  FOR t IN
    SELECT table_name, load_phase
    FROM delta_ctl.table_config
    WHERE delta_ctl.stage_table_exists(table_name)
    ORDER BY load_phase, table_name
  LOOP
    summary := NULL;
    SELECT string_agg(format('%s %s', count_name, row_count), ' · ' ORDER BY count_name)
      INTO summary
    FROM delta_ctl.run_counts
    WHERE table_name = t.table_name
      AND count_name <> 'STAGED';

    RETURN NEXT '';
    RETURN NEXT format('── %s ──', t.table_name);
    RETURN NEXT COALESCE(summary, 'no class counts');

    FOR c IN
      SELECT count_name, row_count
      FROM delta_ctl.run_counts
      WHERE table_name = t.table_name
        AND count_name IN ('NEW', 'CHANGED', 'CHANGED_LOCAL_NEWER', 'BLOCKED_FK', 'AMBIGUOUS_NK')
        AND row_count > 0
      ORDER BY CASE count_name
        WHEN 'CHANGED' THEN 1
        WHEN 'CHANGED_LOCAL_NEWER' THEN 2
        WHEN 'NEW' THEN 3
        WHEN 'BLOCKED_FK' THEN 4
        WHEN 'AMBIGUOUS_NK' THEN 5
        ELSE 99 END
    LOOP
      RETURN NEXT format('%s — showing up to %s of %s', c.count_name, p_sample_size, c.row_count);
      FOR sample IN SELECT * FROM delta_ctl.render_samples(t.table_name, c.count_name, p_sample_size) LOOP
        RETURN NEXT sample;
      END LOOP;
    END LOOP;
  END LOOP;

  RETURN NEXT '';
  RETURN NEXT 'Selection: copy and edit selection.conf, check it with --mode validate, then run --mode apply.';
END;
$$;

CREATE OR REPLACE FUNCTION delta_ctl.render_selection_manifest()
RETURNS SETOF text
LANGUAGE plpgsql
AS $$
DECLARE
  t record;
  c record;
  v_sha text;
  v_staged text;
  v_manifest_default text;
  v_selector_limit_raw text;
  v_selector_limit_normalized text;
  v_selector_limit_present boolean;
  v_selector_suggestion_limit integer := 50;
  v_selector_suggestion_limit_max constant integer := 100000;
  v_default_include text;
  v_default_new bigint := 0;
  v_default_changed bigint := 0;
  v_default_total bigint := 0;
  v_default_tables bigint := 0;
  v_range_tokens text[];
  v_range_sizes bigint[];
  v_singleton_tokens text[];
  v_singleton_lines text[];
  v_total_rows bigint;
  v_singleton_count bigint;
  v_range_count bigint;
  v_id_col text;
  v_primary_kind text;
  v_example_values text;
  v_invalid_ids boolean;
  v_class_width integer;
  v_selector_line_max constant integer := 120;
  v_selector_prefix text;
  v_selector_line text;
  v_range_annotation text;
  v_token text;
  v_count_token text;
  v_token_index integer;
  v_singleton_line_index integer;
BEGIN
  SELECT value INTO v_sha FROM delta_ctl.run_metadata WHERE key = 'dump_sha256';
  SELECT COALESCE(
           (SELECT value FROM delta_ctl.run_metadata WHERE key = 'manifest_default'),
           'new,changed') -- NOSONAR
    INTO v_manifest_default;
  IF v_manifest_default NOT IN ('new,changed', 'none') THEN
    RAISE EXCEPTION 'unsupported manifest_default metadata value: %', v_manifest_default;
  END IF;

  SELECT EXISTS (
           SELECT 1 FROM delta_ctl.run_metadata WHERE key = 'selector_suggestion_limit'), -- NOSONAR
         (SELECT value FROM delta_ctl.run_metadata WHERE key = 'selector_suggestion_limit')
    INTO v_selector_limit_present, v_selector_limit_raw;
  IF v_selector_limit_present THEN
    IF v_selector_limit_raw IS NULL OR v_selector_limit_raw !~ '^[0-9]+$' THEN
      RAISE EXCEPTION
        'invalid selector_suggestion_limit metadata value: % (allowed range: 0..100000)', -- NOSONAR
        COALESCE(v_selector_limit_raw, '<NULL>');
    END IF;
    v_selector_limit_normalized := COALESCE(
      NULLIF(regexp_replace(v_selector_limit_raw, '^0+', ''), ''), '0');
    IF length(v_selector_limit_normalized) > length(v_selector_suggestion_limit_max::text) THEN
      RAISE EXCEPTION
        'invalid selector_suggestion_limit metadata value: % (allowed range: 0..100000)', -- NOSONAR
        v_selector_limit_raw;
    END IF;
    v_selector_suggestion_limit := v_selector_limit_normalized::integer;
    IF v_selector_suggestion_limit > v_selector_suggestion_limit_max THEN
      RAISE EXCEPTION
        'invalid selector_suggestion_limit metadata value: % (allowed range: 0..100000)', -- NOSONAR
        v_selector_limit_raw;
    END IF;
  END IF;

  v_default_include := CASE WHEN v_manifest_default = 'none' THEN '' ELSE 'new,changed' END;

  SELECT string_agg(format('%s=%s', tc.table_name, COALESCE(rc.row_count, 0)), ' ' ORDER BY tc.load_phase, tc.table_name)
    INTO v_staged
  FROM delta_ctl.table_config tc
  LEFT JOIN delta_ctl.run_counts rc
    ON rc.table_name = tc.table_name AND rc.count_name = 'STAGED';

  SELECT GREATEST(3, COALESCE(max(length(tc.table_name) + 2), 3)) + 2
    INTO v_class_width
  FROM delta_ctl.table_config tc;

  IF v_manifest_default = 'new,changed' THEN
    SELECT COALESCE(sum(counts.new_n), 0),
           COALESCE(sum(counts.changed_n), 0),
           count(*) FILTER (WHERE counts.new_n + counts.changed_n > 0)
      INTO v_default_new, v_default_changed, v_default_tables
    FROM (
      SELECT tc.table_name,
             COALESCE(max(rc.row_count) FILTER (WHERE rc.count_name = 'NEW'), 0) AS new_n,
             COALESCE(max(rc.row_count) FILTER (WHERE rc.count_name = 'CHANGED'), 0) AS changed_n
      FROM delta_ctl.table_config tc
      LEFT JOIN delta_ctl.run_counts rc ON rc.table_name = tc.table_name
      GROUP BY tc.table_name
    ) counts;
    v_default_total := v_default_new + v_default_changed;
  END IF;

  RETURN NEXT '# delta-selection v2';
  RETURN NEXT '# dump_sha256=' || COALESCE(v_sha, '');
  RETURN NEXT '# staged ' || COALESCE(v_staged, '');
  RETURN NEXT '#';
  RETURN NEXT '# The two binding headers above tie row selectors to this reviewed preview.';
  RETURN NEXT '# Keep them unchanged when uncommenting any .rows selector.';
  RETURN NEXT '# Class-only selection files remain backward compatible and do not require bindings.';
  RETURN NEXT '#';
  RETURN NEXT '# ---------------------------------------------------------------------------'; -- NOSONAR
  RETURN NEXT '# ACTIVE SELECTION';
  RETURN NEXT '# Edit these lines to choose which classes are eligible for apply.';
  RETURN NEXT '# ---------------------------------------------------------------------------'; -- NOSONAR
  RETURN NEXT '#';
  RETURN NEXT rpad('[*]', v_class_width, ' ') || 'include=' || v_default_include;
  RETURN NEXT format(
    '# Default selection ([*] %s) currently matches %s rows across %s tables (new=%s changed=%s).',
    v_manifest_default, v_default_total, v_default_tables, v_default_new, v_default_changed);
  RETURN NEXT '#';

  FOR t IN
    SELECT tc.table_name, tc.load_phase,
           COALESCE(max(rc.row_count) FILTER (WHERE rc.count_name = 'NEW'), 0) AS new_n,
           COALESCE(max(rc.row_count) FILTER (WHERE rc.count_name = 'CHANGED'), 0) AS changed_n,
           COALESCE(max(rc.row_count) FILTER (WHERE rc.count_name = 'CHANGED_LOCAL_NEWER'), 0) AS local_newer_n,
           COALESCE((
             SELECT string_agg(DISTINCT fk.parent_name, ',' ORDER BY fk.parent_name)
             FROM jsonb_each_text(tc.fk_map) AS fk(child_col, parent_name)
             WHERE fk.parent_name NOT LIKE 'external:%'
           ), '') AS parents
    FROM delta_ctl.table_config tc
    LEFT JOIN delta_ctl.run_counts rc ON rc.table_name = tc.table_name
    GROUP BY tc.table_name, tc.load_phase, tc.fk_map
    ORDER BY tc.load_phase, tc.table_name
  LOOP
    RETURN NEXT rpad(format('[%s]', t.table_name), v_class_width, ' ')
      || format('include=%s # new=%s changed=%s changed_local_newer=%s%s',
        v_default_include, t.new_n, t.changed_n, t.local_newer_n,
        CASE WHEN t.parents = '' THEN '' ELSE ' parents=' || t.parents END);
  END LOOP;

  RETURN NEXT '#';
  FOR c IN
    SELECT class_name, selector_name
    FROM (VALUES ('NEW', 'new'), ('CHANGED', 'changed')) AS classes(class_name, selector_name)
  LOOP
    RETURN NEXT format(
      '# Small %s sets receive ready-to-uncomment suggestions:', c.class_name);
    FOR t IN
      SELECT tc.table_name, tc.load_phase, tc.pk_col
      FROM delta_ctl.table_config tc
      LEFT JOIN delta_ctl.run_counts rc ON rc.table_name = tc.table_name
      GROUP BY tc.table_name, tc.load_phase, tc.pk_col
      HAVING COALESCE(max(rc.row_count) FILTER (WHERE rc.count_name = c.class_name), 0)
             BETWEEN 1 AND v_selector_suggestion_limit
      ORDER BY tc.load_phase, tc.table_name
    LOOP
      IF delta_ctl.stage_table_exists(t.table_name) THEN
        v_id_col := CASE WHEN t.pk_col IS NULL THEN '_delta_row_id' ELSE t.pk_col END;
        EXECUTE format($fmt$
          WITH source AS (
            SELECT s.%I::numeric AS n
            FROM delta_stage.%I s
            JOIN delta_diff.%I d ON d._delta_row_id = s._delta_row_id
            WHERE d.class = $1
          ), ordered AS (
            SELECT n, n - row_number() OVER (ORDER BY n)::numeric AS grp
            FROM source
          ), runs AS (
            SELECT min(n) AS lo, max(n) AS hi, count(*)::bigint AS row_count
            FROM ordered
            GROUP BY grp
          )
          SELECT
            COALESCE(
              array_agg((lo::text || '-' || hi::text) ORDER BY lo)
                FILTER (WHERE row_count > 1),
              '{}'::text[]),
            COALESCE(
              array_agg(row_count ORDER BY lo)
                FILTER (WHERE row_count > 1),
              '{}'::bigint[]),
            COALESCE(
              array_agg(lo::text ORDER BY lo)
                FILTER (WHERE row_count = 1),
              '{}'::text[]),
            COALESCE(sum(row_count), 0)::bigint,
            count(*) FILTER (WHERE row_count = 1)::bigint,
            count(*) FILTER (WHERE row_count > 1)::bigint,
            EXISTS (SELECT 1 FROM source WHERE n < 0)
          FROM runs
        $fmt$, v_id_col, t.table_name, delta_ctl.class_table_name(t.table_name))
        INTO v_range_tokens, v_range_sizes, v_singleton_tokens,
             v_total_rows, v_singleton_count, v_range_count, v_invalid_ids
        USING c.class_name;

        -- An actual blank line separates each table block, including the first
        -- block from its section heading.
        RETURN NEXT '';
        RETURN NEXT format(
          '# [%s] Exact %s set: rows=%s singletons=%s ranges=%s',
          t.table_name, c.class_name, v_total_rows, v_singleton_count, v_range_count);

        IF v_invalid_ids THEN
          RETURN NEXT format(
            '# [%s] Exact %s selector unavailable for this small set.',
            t.table_name, c.class_name);
          RETURN NEXT format(
            '#   Review details/%s.%s.tsv; negative id: values are outside the selector grammar.',
            t.table_name, c.selector_name);
        ELSE
          v_selector_prefix := format(
            '# [%s] %s.rows include=%s:',
            t.table_name, c.selector_name,
            CASE WHEN t.pk_col IS NULL THEN 'row' ELSE 'id' END);

          IF cardinality(v_range_tokens) > 0 THEN
            v_selector_line := v_selector_prefix;
            v_range_annotation := '#   Range counts:'; -- NOSONAR
            FOR v_token_index IN 1..cardinality(v_range_tokens) LOOP
              v_token := v_range_tokens[v_token_index];
              v_count_token := format(
                '%s (%s rows)', v_token, v_range_sizes[v_token_index]);
              IF v_selector_line <> v_selector_prefix
                 AND (length(v_selector_line) + 1 + length(v_token) > v_selector_line_max
                      OR length(v_range_annotation) + 2 + length(v_count_token)
                           > v_selector_line_max) THEN
                RETURN NEXT v_selector_line;
                RETURN NEXT v_range_annotation;
                v_selector_line := v_selector_prefix;
                v_range_annotation := '#   Range counts:'; -- NOSONAR
              END IF;
              v_selector_line := v_selector_line
                || CASE WHEN v_selector_line = v_selector_prefix THEN '' ELSE ',' END
                || v_token;
              v_range_annotation := v_range_annotation
                || CASE WHEN v_range_annotation = '#   Range counts:' THEN ' ' ELSE ', ' END
                || v_count_token;
            END LOOP;
            RETURN NEXT v_selector_line;
            RETURN NEXT v_range_annotation;
          END IF;

          IF cardinality(v_singleton_tokens) > 0 THEN
            -- Keep the range/count pair adjacent, then separate singleton IDs
            -- with one actual blank line when both categories exist.
            IF cardinality(v_range_tokens) > 0 THEN
              RETURN NEXT '';
            END IF;

            -- Build singleton lines before emitting them so long lists can be
            -- split into visual paragraphs after every four selector lines.
            v_singleton_lines := '{}'::text[];
            v_selector_line := v_selector_prefix;
            FOREACH v_token IN ARRAY v_singleton_tokens LOOP
              IF v_selector_line <> v_selector_prefix
                 AND length(v_selector_line) + 1 + length(v_token) > v_selector_line_max THEN
                v_singleton_lines := array_append(v_singleton_lines, v_selector_line);
                v_selector_line := v_selector_prefix;
              END IF;
              v_selector_line := v_selector_line
                || CASE WHEN v_selector_line = v_selector_prefix THEN '' ELSE ',' END
                || v_token;
            END LOOP;
            v_singleton_lines := array_append(v_singleton_lines, v_selector_line);

            FOR v_singleton_line_index IN 1..cardinality(v_singleton_lines) LOOP
              IF cardinality(v_singleton_lines) > 8
                 AND v_singleton_line_index > 1
                 AND mod(v_singleton_line_index - 1, 4) = 0 THEN
                RETURN NEXT '';
              END IF;
              RETURN NEXT v_singleton_lines[v_singleton_line_index];
            END LOOP;
          END IF;
        END IF;
      END IF;
    END LOOP;
    RETURN NEXT '#';
  END LOOP;

  FOR c IN
    SELECT class_name, selector_name
    FROM (VALUES ('NEW', 'new'), ('CHANGED', 'changed')) AS classes(class_name, selector_name)
  LOOP
    RETURN NEXT format(
      '# Large %s sets receive a useful pointer rather than no guidance:', c.class_name);
    FOR t IN
      SELECT tc.table_name, tc.load_phase, tc.pk_col,
             COALESCE(max(rc.row_count)
               FILTER (WHERE rc.count_name = c.class_name), 0) AS class_n
      FROM delta_ctl.table_config tc
      LEFT JOIN delta_ctl.run_counts rc ON rc.table_name = tc.table_name
      GROUP BY tc.table_name, tc.load_phase, tc.pk_col
      HAVING COALESCE(max(rc.row_count)
               FILTER (WHERE rc.count_name = c.class_name), 0) > v_selector_suggestion_limit
      ORDER BY tc.load_phase, tc.table_name
    LOOP
      v_primary_kind := CASE WHEN t.pk_col IS NULL THEN 'row' ELSE 'id' END;
      v_example_values := CASE WHEN t.pk_col IS NULL THEN '4,10-15' ELSE '100,200-210' END;
      RETURN NEXT format(
        '# %s has %s %s rows; choose selector_id%s from:',
        t.table_name, t.class_n, c.class_name,
        CASE
          WHEN t.table_name = delta_ctl.auth_component_op_table() THEN ''
          WHEN delta_ctl.corp_col_expr(t.table_name) IS NOT NULL
            THEN ' or corp values'
          ELSE ''
        END);
      RETURN NEXT format('# details/%s.%s.tsv', t.table_name, c.selector_name);
      RETURN NEXT '# Example syntax:';
      RETURN NEXT format('# [%s] %s.rows include=%s:%s',
        t.table_name, c.selector_name, v_primary_kind, v_example_values);
      IF delta_ctl.corp_col_expr(t.table_name) IS NOT NULL THEN
        IF t.table_name = delta_ctl.auth_component_op_table() THEN
          RETURN NEXT '# corp: selectors are also supported via the staged auth_processing parent:';
        END IF;
        RETURN NEXT format('# [%s] %s.rows include=corp:BC0000001,BC0000002',
          t.table_name, c.selector_name);
      END IF;
      RETURN NEXT '#';
    END LOOP;
  END LOOP;

  RETURN NEXT '# ---------------------------------------------------------------------------'; -- NOSONAR
  RETURN NEXT '# Full selector grammar and 13 worked examples: selection_cookbook.txt (this run dir)';
  RETURN NEXT '# ---------------------------------------------------------------------------'; -- NOSONAR
END;
$$;

CREATE OR REPLACE FUNCTION delta_ctl.render_selection_cookbook()
RETURNS SETOF text
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN NEXT '# Classes: new | changed | changed_local_newer (other classes are never applyable).';
  RETURN NEXT '# Selector kinds: id: for PK tables; row: for PK-less tables; corp: only where supported.';
  RETURN NEXT '# Multiple includes union their matches; excludes subtract; --only-corps is a final intersection.';
  RETURN NEXT '#';
  RETURN NEXT '# ---------------------------------------------------------------------------'; -- NOSONAR
  RETURN NEXT '# OPERATOR COOKBOOK';
  RETURN NEXT '# Everything below is commented documentation. Copy or uncomment only the';
  RETURN NEXT '# examples you intend to use. Row selectors never enable a class by themselves.';
  RETURN NEXT '# ---------------------------------------------------------------------------'; -- NOSONAR
  RETURN NEXT '#';
  RETURN NEXT '# 1. Apply all NEW and CHANGED rows for a table:';
  RETURN NEXT '#';
  RETURN NEXT '# [mig_corp_batch] include=new,changed';
  RETURN NEXT '#';
  RETURN NEXT '# 2. Apply only NEW rows for a table:';
  RETURN NEXT '#';
  RETURN NEXT '# [mig_corp_batch] include=new';
  RETURN NEXT '#';
  RETURN NEXT '# 3. Apply only CHANGED rows for a table:';
  RETURN NEXT '#';
  RETURN NEXT '# [corp_processing] include=changed';
  RETURN NEXT '#';
  RETURN NEXT '# 4. Disable a table entirely:';
  RETURN NEXT '#';
  RETURN NEXT '# [mig_corp_batch] include=';
  RETURN NEXT '#';
  RETURN NEXT '# 5. Apply specific NEW rows by staged primary key.';
  RETURN NEXT '#    Lists and inclusive ranges may be mixed:';
  RETURN NEXT '#';
  RETURN NEXT '# [mig_corp_batch] include=new,changed';
  RETURN NEXT '# [mig_corp_batch] new.rows include=id:3067,7922,8241-8242';
  RETURN NEXT '#';
  RETURN NEXT '# 6. Apply every NEW row except specific IDs:';
  RETURN NEXT '#';
  RETURN NEXT '# [mig_corp_account] include=new,changed';
  RETURN NEXT '# [mig_corp_account] new.rows exclude=id:23,100-105';
  RETURN NEXT '#';
  RETURN NEXT '# 7. Combine multiple includes, then subtract exclusions.';
  RETURN NEXT '#    Include lines are unioned; exclude lines are applied afterward:';
  RETURN NEXT '#';
  RETURN NEXT '# [corp_processing] include=new,changed'; -- NOSONAR
  RETURN NEXT '# [corp_processing] new.rows include=id:53946-53959';
  RETURN NEXT '# [corp_processing] new.rows include=corp:BC0000001,BC0000002';
  RETURN NEXT '# [corp_processing] new.rows exclude=id:53947,53952';
  RETURN NEXT '#';
  RETURN NEXT '# 8. Apply specific CHANGED rows:';
  RETURN NEXT '#';
  RETURN NEXT '# [corp_processing] include=new,changed'; -- NOSONAR
  RETURN NEXT '# [corp_processing] changed.rows include=id:881,900-905';
  RETURN NEXT '#';
  RETURN NEXT '# 9. Apply CHANGED rows for selected corporations:';
  RETURN NEXT '#';
  RETURN NEXT '# [corp_processing] include=new,changed'; -- NOSONAR
  RETURN NEXT '# [corp_processing] changed.rows include=corp:BC0000001,BC0000002';
  RETURN NEXT '#';
  RETURN NEXT '# 10. Explicitly opt into locally newer rows.';
  RETURN NEXT '#     CAUTION: these may overwrite more recently modified local values:';
  RETURN NEXT '#';
  RETURN NEXT '# [corp_processing] include=new,changed,changed_local_newer';
  RETURN NEXT '# [corp_processing] changed_local_newer.rows include=id:901';
  RETURN NEXT '#';
  RETURN NEXT '# 11. Select rows from a PK-less table using the staged row ordinal:';
  RETURN NEXT '#';
  RETURN NEXT '# [email_domain_groups] include=new';
  RETURN NEXT '# [email_domain_groups] new.rows include=row:4,10-15';
  RETURN NEXT '#';
  RETURN NEXT '# 12. Parent dependency reminder:';
  RETURN NEXT '#     A selected NEW child whose preserved parent is also NEW requires that';
  RETURN NEXT '#     parent row to remain selected.';
  RETURN NEXT '#';
  RETURN NEXT '# [mig_batch] include=new';
  RETURN NEXT '# [mig_batch] new.rows include=id:152';
  RETURN NEXT '# [mig_corp_account] include=new';
  RETURN NEXT '# [mig_corp_account] new.rows include=id:23643-23658';
  RETURN NEXT '#';
  RETURN NEXT '# 13. --only-corps is an additional global intersection:';
  RETURN NEXT '#';
  RETURN NEXT '# ./delta_restore_extract.sh ... ' || chr(92);
  RETURN NEXT '#   --selection-file selection.conf ' || chr(92);
  RETURN NEXT '#   --only-corps selected_corps.txt';
END;
$$;

CREATE OR REPLACE FUNCTION delta_ctl.corp_col_expr(p_table text)
RETURNS text
LANGUAGE plpgsql
AS $$
BEGIN
  PERFORM delta_ctl.assert_table_name(p_table);
  CASE p_table
    WHEN delta_ctl.auth_component_op_table() THEN
      IF delta_ctl.stage_table_exists(delta_ctl.auth_processing_table()) THEN
        RETURN '(SELECT ap.corp_num::text FROM delta_stage.auth_processing ap WHERE ap.id = s.auth_processing_id LIMIT 1)';
      END IF;
      RETURN NULL;
    WHEN 'corp_processing', 'colin_tracking', delta_ctl.auth_processing_table(),
         'mig_corp_batch', 'mig_corp_account', 'exclude_corps', 'corps_with_third_party'
      THEN RETURN 's.corp_num::text';
    WHEN 'bar_corps' THEN RETURN 's.identifier::text';
    ELSE RETURN NULL;
  END CASE;
END;
$$;

CREATE OR REPLACE FUNCTION delta_ctl.selection_filter_expr(p_table text)
RETURNS text
LANGUAGE plpgsql
AS $$
DECLARE
  v_corp text;
BEGIN
  PERFORM 1 FROM delta_ctl.only_corps LIMIT 1;
  IF NOT FOUND THEN RETURN 'true'; END IF;
  v_corp := delta_ctl.corp_col_expr(p_table);
  IF v_corp IS NULL THEN RETURN 'true'; END IF;
  RETURN format('EXISTS (SELECT 1 FROM delta_ctl.only_corps oc WHERE oc.corp_num = (%s))', v_corp);
END;
$$;

CREATE OR REPLACE FUNCTION delta_ctl.verify_row_selection()
RETURNS void
LANGUAGE plpgsql
AS $$
DECLARE
  r record;
  v_cfg delta_ctl.table_config%ROWTYPE;
  v_condition text;
  v_corp text;
  v_filter text;
  v_matched bigint;
  v_problem text;
  v_dups boolean;
BEGIN
  TRUNCATE delta_ctl.selection_diagnostics;
  FOR r IN
    SELECT *, CASE WHEN kind = 'corp' THEN corp_num
      WHEN is_range THEN value_from || '-' || value_to ELSE value_from::text END AS selector
    FROM delta_ctl.row_selection
    ORDER BY source_line, table_name, class, mode, kind, value_from, corp_num
  LOOP
    SELECT * INTO v_cfg FROM delta_ctl.table_config WHERE table_name = r.table_name;
    v_problem := NULL;
    v_matched := NULL;
    IF NOT EXISTS (SELECT 1 FROM delta_ctl.selection s
                   WHERE s.table_name = r.table_name AND s.class = r.class) THEN
      v_problem := 'CLASS_NOT_INCLUDED';
    ELSIF NOT delta_ctl.stage_table_exists(r.table_name)
       OR to_regclass(format('delta_diff.%I', delta_ctl.class_table_name(r.table_name))) IS NULL THEN
      v_matched := 0;
      v_problem := 'NO_MATCH';
    ELSIF r.kind = 'id' AND v_cfg.pk_col IS NULL THEN
      v_problem := 'KIND_UNSUPPORTED';
    ELSIF r.kind = 'corp' AND delta_ctl.corp_col_expr(r.table_name) IS NULL THEN
      v_problem := 'KIND_UNSUPPORTED';
    END IF;

    IF v_problem IS NULL AND r.kind = 'id' THEN
      EXECUTE format('SELECT EXISTS (SELECT 1 FROM delta_stage.%I GROUP BY %I HAVING count(*) > 1)',
        r.table_name, v_cfg.pk_col) INTO v_dups;
      IF v_dups THEN v_problem := 'DUP_STAGED_PK'; END IF;
    END IF;

    IF v_problem IS NULL THEN
      IF r.kind = 'id' THEN
        v_condition := format('s.%I::bigint BETWEEN $2 AND $3', v_cfg.pk_col);
      ELSIF r.kind = 'row' THEN
        v_condition := 's._delta_row_id BETWEEN $2 AND $3';
      ELSE
        v_corp := delta_ctl.corp_col_expr(r.table_name);
        v_condition := format('(%s) = $4', v_corp);
      END IF;
      v_filter := delta_ctl.selection_filter_expr(r.table_name);
      EXECUTE format($fmt$
        SELECT count(*)
        FROM delta_diff.%I d
        JOIN delta_stage.%I s ON s._delta_row_id = d._delta_row_id
        WHERE d.class = $1 AND (%s) AND (%s)
      $fmt$, delta_ctl.class_table_name(r.table_name), r.table_name, v_condition, v_filter)
      INTO v_matched USING r.class, r.value_from, r.value_to, r.corp_num;
      IF v_matched = 0 THEN
        v_problem := 'NO_MATCH';
      ELSIF r.kind IN ('id', 'row') AND NOT r.is_range AND v_matched > 1 THEN
        v_problem := 'SCALAR_MULTI_MATCH';
      END IF;
    END IF;

    INSERT INTO delta_ctl.selection_diagnostics(
      table_name, class, mode, kind, selector, source_line, matched, problem)
    VALUES (r.table_name, r.class, r.mode, r.kind, r.selector,
            r.source_line, v_matched, v_problem);
  END LOOP;

END;
$$;

CREATE OR REPLACE FUNCTION delta_ctl.stamp_selection()
RETURNS void
LANGUAGE plpgsql
AS $$
DECLARE
  r record;
  v_filter text;
  v_corp text;
  v_match text;
BEGIN
  PERFORM delta_ctl.verify_row_selection();
  IF EXISTS (SELECT 1 FROM delta_ctl.selection_diagnostics WHERE problem IS NOT NULL) THEN
    RAISE EXCEPTION 'SELECTION_INVALID: row selectors failed validation; query delta_ctl.selection_diagnostics';
  END IF;
  FOR r IN
    SELECT table_name, pk_col
    FROM delta_ctl.table_config
    WHERE delta_ctl.stage_table_exists(table_name)
    ORDER BY load_phase, table_name
  LOOP
    EXECUTE format('UPDATE delta_diff.%I SET selected = false', delta_ctl.class_table_name(r.table_name));
    v_filter := delta_ctl.selection_filter_expr(r.table_name);
    EXECUTE format($fmt$
      UPDATE delta_diff.%I d
      SET selected = true
      FROM delta_stage.%I s
      WHERE d._delta_row_id = s._delta_row_id
        AND d.class IN ('NEW', 'CHANGED', 'CHANGED_LOCAL_NEWER')
        AND EXISTS (
          SELECT 1 FROM delta_ctl.selection sel
          WHERE sel.table_name = %L AND sel.class = d.class
        )
        AND (%s)
    $fmt$, delta_ctl.class_table_name(r.table_name), r.table_name, r.table_name, v_filter);

    IF EXISTS (SELECT 1 FROM delta_ctl.row_selection rs WHERE rs.table_name = r.table_name) THEN
      v_corp := delta_ctl.corp_col_expr(r.table_name);
      v_match := '('
        || CASE WHEN r.pk_col IS NULL THEN 'false'
             ELSE format('(rs.kind = ''id'' AND s.%I::bigint BETWEEN rs.value_from AND rs.value_to)', r.pk_col) END
        || ' OR (rs.kind = ''row'' AND s._delta_row_id BETWEEN rs.value_from AND rs.value_to)'
        || CASE WHEN v_corp IS NULL THEN ''
             ELSE format(' OR (rs.kind = ''corp'' AND (%s) = rs.corp_num)', v_corp) END
        || ')';
      EXECUTE format($fmt$
        UPDATE delta_diff.%I d
        SET selected = false
        FROM delta_stage.%I s
        WHERE d._delta_row_id = s._delta_row_id
          AND d.selected
          AND (
            (
              EXISTS (
                SELECT 1 FROM delta_ctl.row_selection rs
                WHERE rs.table_name = %L AND rs.class = d.class AND rs.mode = 'include'
              )
              AND NOT EXISTS (
                SELECT 1 FROM delta_ctl.row_selection rs
                WHERE rs.table_name = %L AND rs.class = d.class AND rs.mode = 'include'
                  AND %s
              )
            )
            OR EXISTS (
              SELECT 1 FROM delta_ctl.row_selection rs
              WHERE rs.table_name = %L AND rs.class = d.class AND rs.mode = 'exclude'
                AND %s
            )
          )
      $fmt$, delta_ctl.class_table_name(r.table_name), r.table_name,
        r.table_name, r.table_name, v_match, r.table_name, v_match);
    END IF;
  END LOOP;
END;
$$;

CREATE OR REPLACE FUNCTION delta_ctl.selected_counts()
RETURNS TABLE(table_name text, class text, row_count bigint, load_phase int)
LANGUAGE plpgsql
AS $$
DECLARE
  r record;
BEGIN
  FOR r IN
    SELECT tc.table_name, tc.load_phase
    FROM delta_ctl.table_config tc
    WHERE delta_ctl.stage_table_exists(tc.table_name)
    ORDER BY tc.load_phase, tc.table_name
  LOOP
    RETURN QUERY EXECUTE format(
      'SELECT %L::text, class::text, count(*)::bigint, %s::int FROM delta_diff.%I WHERE selected GROUP BY class',
      r.table_name, r.load_phase, delta_ctl.class_table_name(r.table_name));
  END LOOP;
END;
$$;

CREATE OR REPLACE FUNCTION delta_ctl.validate_dependencies()
RETURNS void
LANGUAGE plpgsql
AS $$
DECLARE
  c record;
  p record;
  v_parent_pk text;
  v_count bigint;
  v_sample_ids text;
BEGIN
  TRUNCATE delta_ctl.dependency_violations;

  FOR c IN
    SELECT table_name, fk_map
    FROM delta_ctl.table_config
    WHERE delta_ctl.stage_table_exists(table_name)
  LOOP
    FOR p IN
      SELECT key AS fk_col, value AS parent_table
      FROM jsonb_each_text(c.fk_map)
      WHERE value NOT LIKE delta_ctl.external_fk_pattern()
    LOOP
      SELECT pk_col INTO v_parent_pk FROM delta_ctl.table_config WHERE table_name = p.parent_table;
      IF v_parent_pk IS NULL
         OR NOT delta_ctl.stage_table_exists(p.parent_table)
         OR to_regclass(format('delta_diff.%I', delta_ctl.class_table_name(p.parent_table))) IS NULL THEN
        CONTINUE;
      END IF;

      EXECUTE format($fmt$
        WITH violations AS (
          SELECT COALESCE(cd.staged_pk::text, cd._delta_row_id::text) AS sample_id
          FROM delta_diff.%I cd
          JOIN delta_stage.%I cs ON cs._delta_row_id = cd._delta_row_id
          LEFT JOIN delta_stage.%I ps ON ps.%I = cs.%I
          LEFT JOIN delta_diff.%I pd ON pd._delta_row_id = ps._delta_row_id
          WHERE cd.selected
            AND cs.%I IS NOT NULL
            AND (
              pd._delta_row_id IS NULL
              OR pd.class IN ('BLOCKED_FK', 'AMBIGUOUS_NK', 'BLOCKED_PARENT')
              OR (pd.class = 'NEW' AND NOT pd.selected)
            )
        )
        SELECT count(*),
               (SELECT string_agg(sample_id, ',' ORDER BY sample_id)
                FROM (SELECT sample_id FROM violations ORDER BY sample_id LIMIT 10) q)
        FROM violations
      $fmt$, delta_ctl.class_table_name(c.table_name), c.table_name, p.parent_table, v_parent_pk, p.fk_col,
            delta_ctl.class_table_name(p.parent_table), p.fk_col)
      INTO v_count, v_sample_ids;

      IF v_count > 0 THEN
        INSERT INTO delta_ctl.dependency_violations(child_table, parent_table, reason, row_count, sample_ids)
        VALUES (c.table_name, p.parent_table,
                format('selected child rows require selected/non-blocked parent via %I', p.fk_col),
                v_count, v_sample_ids);
      END IF;
    END LOOP;
  END LOOP;

END;
$$;

CREATE OR REPLACE FUNCTION delta_ctl.insert_expr(p_table text, p_col text)
RETURNS text
LANGUAGE plpgsql
AS $$
DECLARE
  v_cfg delta_ctl.table_config%ROWTYPE;
  v_parent text;
BEGIN
  SELECT * INTO v_cfg FROM delta_ctl.table_config WHERE table_name = p_table;
  IF v_cfg.pk_col IS NOT NULL AND p_col = v_cfg.pk_col THEN
    RETURN 'm.local_id';
  END IF;

  SELECT value INTO v_parent
  FROM delta_ctl.table_config c, jsonb_each_text(c.fk_map)
  WHERE c.table_name = p_table
    AND key = p_col
    AND value NOT LIKE delta_ctl.external_fk_pattern();

  IF v_parent IS NOT NULL THEN
    RETURN delta_ctl.map_fk_expr(v_parent, p_col);
  END IF;

  RETURN format('s.%I', p_col);
END;
$$;

CREATE OR REPLACE FUNCTION delta_ctl.update_columns(p_table text)
RETURNS text[]
LANGUAGE plpgsql
AS $$
DECLARE
  v_cfg delta_ctl.table_config%ROWTYPE;
  v_cols text[];
BEGIN
  SELECT c.table_name,
         c.load_phase,
         c.pk_col,
         c.nk_exprs,
         c.nk_stage_exprs,
         c.nk_local_exprs,
         c.nk_cols,
         c.nk_enforced,
         c.fk_map,
         c.has_last_modified,
         c.match_mode,
         c.classify_ignore_cols,
         c.compare_ignore_cols
    INTO v_cfg
  FROM delta_ctl.table_config c
  WHERE c.table_name = p_table;

  SELECT COALESCE(array_agg(a.attname ORDER BY a.attnum), '{}')
    INTO v_cols
  FROM pg_attribute a
  WHERE a.attrelid = delta_ctl.public_rel(p_table)::regclass
    AND a.attnum > 0
    AND NOT a.attisdropped
    AND (v_cfg.pk_col IS NULL OR a.attname <> v_cfg.pk_col)
    AND NOT (a.attname = ANY(v_cfg.nk_cols));

  RETURN v_cols;
END;
$$;

CREATE OR REPLACE FUNCTION delta_ctl.allocate_ids(p_table text)
RETURNS void
LANGUAGE plpgsql
AS $$
DECLARE
  v_cfg delta_ctl.table_config%ROWTYPE;
  v_seq text;
  v_sql text;
  v_missing bigint;
BEGIN
  SELECT * INTO v_cfg FROM delta_ctl.table_config WHERE table_name = p_table;
  IF NOT FOUND OR v_cfg.pk_col IS NULL OR NOT delta_ctl.stage_table_exists(p_table) THEN
    RETURN;
  END IF;

  v_seq := pg_get_serial_sequence(delta_ctl.public_rel(p_table), v_cfg.pk_col);
  IF v_seq IS NULL THEN
    RETURN;
  END IF;

  v_sql := format($fmt$
    SELECT setval(%L, GREATEST(
      (SELECT last_value FROM %s),
      (SELECT COALESCE(max(%I), 0) FROM public.%I),
      (SELECT COALESCE(max(local_id), 0) FROM delta_map.%I),
      1
    ), true)
  $fmt$, v_seq, v_seq::regclass, v_cfg.pk_col, p_table, delta_ctl.map_table_name(p_table));
  EXECUTE v_sql;

  EXECUTE format($fmt$
    UPDATE delta_map.%I m
    SET local_id = nextval(%L)
    FROM delta_stage.%I s
    JOIN delta_diff.%I d ON d._delta_row_id = s._delta_row_id
    WHERE m.staged_id = s.%I
      AND m.disposition = 'NEW_REALLOCATED'
      AND d.class = 'NEW'
      AND d.selected
  $fmt$, delta_ctl.map_table_name(p_table), v_seq, p_table, delta_ctl.class_table_name(p_table), v_cfg.pk_col);

  EXECUTE format($fmt$
    SELECT count(*)
    FROM delta_stage.%I s
    JOIN delta_diff.%I d ON d._delta_row_id = s._delta_row_id
    JOIN delta_map.%I m ON m.staged_id = s.%I
    WHERE d.class = 'NEW' AND d.selected AND m.local_id IS NULL
  $fmt$, p_table, delta_ctl.class_table_name(p_table), delta_ctl.map_table_name(p_table), v_cfg.pk_col)
  INTO v_missing;

  IF v_missing > 0 THEN
    RAISE EXCEPTION 'APPLY_VERIFICATION_FAILED: selected NEW rows in % lack allocated local IDs (%)', p_table, v_missing;
  END IF;
END;
$$;

CREATE OR REPLACE FUNCTION delta_ctl.apply_table(p_table text)
RETURNS void
LANGUAGE plpgsql
AS $$
DECLARE
  v_cfg delta_ctl.table_config%ROWTYPE;
  v_cols text[];
  v_insert_cols text;
  v_insert_exprs text;
  v_update_cols text[];
  v_set_list text;
  v_join_map text := '';
  v_where_target text;
  v_expected bigint;
  v_affected bigint;
  v_class text;
BEGIN
  SELECT * INTO v_cfg FROM delta_ctl.table_config WHERE table_name = p_table;
  IF NOT FOUND OR NOT delta_ctl.stage_table_exists(p_table) THEN
    RETURN;
  END IF;

  PERFORM delta_ctl.allocate_ids(p_table);

  SELECT COALESCE(array_agg(a.attname ORDER BY a.attnum), '{}') INTO v_cols
  FROM pg_attribute a
  WHERE a.attrelid = delta_ctl.public_rel(p_table)::regclass
    AND a.attnum > 0
    AND NOT a.attisdropped;

  v_insert_cols := array_to_string(ARRAY(SELECT format('%I', c) FROM unnest(v_cols) AS c), ', ');
  v_insert_exprs := array_to_string(ARRAY(SELECT delta_ctl.insert_expr(p_table, c) FROM unnest(v_cols) AS c), ', ');
  IF v_cfg.pk_col IS NOT NULL THEN
    v_join_map := format('JOIN delta_map.%I m ON m.staged_id = s.%I', delta_ctl.map_table_name(p_table), v_cfg.pk_col);
  END IF;

  EXECUTE format('SELECT count(*) FROM delta_diff.%I WHERE class = ''NEW'' AND selected', delta_ctl.class_table_name(p_table)) INTO v_expected;
  EXECUTE format($fmt$
    INSERT INTO public.%I (%s)
    SELECT %s
    FROM delta_stage.%I s
    JOIN delta_diff.%I d ON d._delta_row_id = s._delta_row_id
    %s
    WHERE d.class = 'NEW' AND d.selected
  $fmt$, p_table, v_insert_cols, v_insert_exprs, p_table, delta_ctl.class_table_name(p_table), v_join_map);
  GET DIAGNOSTICS v_affected = ROW_COUNT;
  INSERT INTO delta_ctl.apply_counts(table_name, class, action, expected_count, affected_count)
  VALUES (p_table, 'NEW', 'INSERT', v_expected, v_affected)
  ON CONFLICT (table_name, class, action) DO UPDATE
    SET expected_count = EXCLUDED.expected_count, affected_count = EXCLUDED.affected_count;
  IF v_expected <> v_affected THEN
    RAISE EXCEPTION 'APPLY_VERIFICATION_FAILED: %.NEW insert expected %, affected %', p_table, v_expected, v_affected;
  END IF;

  IF v_affected > 0 THEN
    INSERT INTO delta_ctl.touched_tables(table_name) VALUES (p_table) ON CONFLICT DO NOTHING;
  END IF;

  IF p_table = delta_ctl.auth_component_op_table() THEN
    RETURN;
  END IF;

  v_update_cols := delta_ctl.update_columns(p_table);
  IF array_length(v_update_cols, 1) IS NULL THEN
    RETURN;
  END IF;

  v_set_list := array_to_string(ARRAY(
    SELECT format('%I = %s', c, delta_ctl.insert_expr(p_table, c))
    FROM unnest(v_update_cols) AS c
  ), ', ');
  v_where_target := CASE WHEN v_cfg.pk_col IS NULL THEN 'l.ctid = d.local_ctid' ELSE format('l.%I = d.local_pk', v_cfg.pk_col) END;

  FOREACH v_class IN ARRAY ARRAY['CHANGED', 'CHANGED_LOCAL_NEWER'] LOOP
    EXECUTE format('SELECT count(*) FROM delta_diff.%I WHERE class = %L AND selected', delta_ctl.class_table_name(p_table), v_class) INTO v_expected;
    EXECUTE format($fmt$
      UPDATE public.%I l
      SET %s
      FROM delta_stage.%I s
      JOIN delta_diff.%I d ON d._delta_row_id = s._delta_row_id
      WHERE d.class = %L AND d.selected AND %s
    $fmt$, p_table, v_set_list, p_table, delta_ctl.class_table_name(p_table), v_class, v_where_target);
    GET DIAGNOSTICS v_affected = ROW_COUNT;
    INSERT INTO delta_ctl.apply_counts(table_name, class, action, expected_count, affected_count)
    VALUES (p_table, v_class, 'UPDATE', v_expected, v_affected)
    ON CONFLICT (table_name, class, action) DO UPDATE
      SET expected_count = EXCLUDED.expected_count, affected_count = EXCLUDED.affected_count;
    IF v_expected <> v_affected THEN
      RAISE EXCEPTION 'APPLY_VERIFICATION_FAILED: %.% update expected %, affected %', p_table, v_class, v_expected, v_affected;
    END IF;
    IF v_affected > 0 THEN
      INSERT INTO delta_ctl.touched_tables(table_name) VALUES (p_table) ON CONFLICT DO NOTHING;
    END IF;
  END LOOP;
END;
$$;

CREATE OR REPLACE FUNCTION delta_ctl.run_apply()
RETURNS void
LANGUAGE plpgsql
AS $$
DECLARE
  r record;
BEGIN
  PERFORM delta_ctl.run_preview_classification();
  PERFORM delta_ctl.stamp_selection();
  PERFORM delta_ctl.validate_dependencies();
  IF EXISTS (SELECT 1 FROM delta_ctl.dependency_violations) THEN
    RAISE EXCEPTION 'SELECTION_INVALID: selected child rows have blocked, missing, or unselected NEW preserved parents. Query delta_ctl.dependency_violations for details.';
  END IF;

  TRUNCATE delta_ctl.apply_counts;
  TRUNCATE delta_ctl.touched_tables;

  FOR r IN
    SELECT table_name
    FROM delta_ctl.table_config
    WHERE delta_ctl.stage_table_exists(table_name)
    ORDER BY load_phase, table_name
  LOOP
    PERFORM delta_ctl.apply_table(r.table_name);
  END LOOP;
END;
$$;

CREATE OR REPLACE FUNCTION delta_ctl.render_apply_summary_lines()
RETURNS SETOF text
LANGUAGE plpgsql
AS $$
DECLARE
  r record;
  m record;
  c_table_hdr CONSTANT text := delta_ctl.table_kind();
  c_summary_row_format CONSTANT text := '%-36s %-20s %10s';
BEGIN
  RETURN NEXT 'Apply summary';
  RETURN NEXT '=============';
  RETURN NEXT '';

  RETURN NEXT 'Selected counts';
  RETURN NEXT '---------------';
  RETURN NEXT format(c_summary_row_format, c_table_hdr, delta_ctl.class_header(), 'selected');
  FOR r IN
    SELECT table_name, class, row_count, load_phase
    FROM delta_ctl.selected_counts()
    ORDER BY load_phase, table_name, class
  LOOP
    RETURN NEXT format(c_summary_row_format, r.table_name, r.class, r.row_count);
  END LOOP;

  RETURN NEXT '';
  RETURN NEXT 'Affected counts';
  RETURN NEXT '---------------';
  RETURN NEXT format('%-36s %-20s %-8s %10s %10s', c_table_hdr, delta_ctl.class_header(), 'action', 'expected', 'affected');
  FOR r IN
    SELECT table_name, class, action, expected_count, affected_count
    FROM delta_ctl.apply_counts
    ORDER BY table_name, class, action
  LOOP
    RETURN NEXT format('%-36s %-20s %-8s %10s %10s', r.table_name, r.class, r.action, r.expected_count, r.affected_count);
  END LOOP;

  RETURN NEXT '';
  RETURN NEXT 'ID map dispositions';
  RETURN NEXT '-------------------';
  FOR r IN
    SELECT table_name
    FROM delta_ctl.table_config
    WHERE delta_ctl.map_table_exists(table_name)
    ORDER BY load_phase, table_name
  LOOP
    FOR m IN EXECUTE format(
      'SELECT disposition, count(*)::bigint AS n FROM delta_map.%I GROUP BY disposition ORDER BY disposition',
      delta_ctl.map_table_name(r.table_name))
    LOOP
      RETURN NEXT format(c_summary_row_format, r.table_name, m.disposition, m.n);
    END LOOP;
  END LOOP;

  RETURN NEXT '';
  RETURN NEXT 'Blocked/skipped counts';
  RETURN NEXT '----------------------';
  FOR r IN
    SELECT table_name, count_name, row_count
    FROM delta_ctl.run_counts
    WHERE count_name IN ('BLOCKED_FK', 'BLOCKED_PARENT', 'AMBIGUOUS_NK', 'SKIPPED_ABSENT', 'LOCAL_ONLY')
      AND row_count > 0
    ORDER BY table_name, count_name
  LOOP
    RETURN NEXT format(c_summary_row_format, r.table_name, r.count_name, r.row_count);
  END LOOP;

  RETURN NEXT '';
  RETURN NEXT 'Touched tables';
  RETURN NEXT '--------------';
  FOR r IN SELECT table_name FROM delta_ctl.touched_tables ORDER BY table_name LOOP
    RETURN NEXT '- ' || r.table_name;
  END LOOP;
END;
$$;
