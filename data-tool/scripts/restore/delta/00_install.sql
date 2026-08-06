-- Delta restore control schemas and run metadata.
-- Functions are installed separately from 10_functions.sql.

DROP SCHEMA IF EXISTS delta_stage CASCADE;
DROP SCHEMA IF EXISTS delta_map CASCADE;
DROP SCHEMA IF EXISTS delta_diff CASCADE;
DROP SCHEMA IF EXISTS delta_ctl CASCADE;

CREATE SCHEMA delta_stage;
CREATE SCHEMA delta_map;
CREATE SCHEMA delta_diff;
CREATE SCHEMA delta_ctl;

CREATE TABLE delta_ctl.table_config (
  table_name text PRIMARY KEY,
  load_phase int NOT NULL,
  pk_col text NULL,
  nk_exprs text[] NULL,
  nk_stage_exprs text[] NOT NULL DEFAULT '{}',
  nk_local_exprs text[] NOT NULL DEFAULT '{}',
  nk_cols text[] NOT NULL DEFAULT '{}',
  nk_enforced boolean NOT NULL DEFAULT false,
  fk_map jsonb NOT NULL DEFAULT '{}'::jsonb,
  has_last_modified boolean NOT NULL DEFAULT false,
  match_mode text NOT NULL DEFAULT 'nk',
  classify_ignore_cols text[] NOT NULL DEFAULT '{}',
  compare_ignore_cols text[] NOT NULL DEFAULT '{}'
);

CREATE TABLE delta_ctl.run_metadata (
  key text PRIMARY KEY,
  value text,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE delta_ctl.dump_columns (
  table_name text NOT NULL,
  column_name text NOT NULL,
  ordinal int NOT NULL,
  PRIMARY KEY (table_name, column_name)
);

CREATE TABLE delta_ctl.drift_warnings (
  table_name text NOT NULL,
  column_name text NOT NULL,
  warning text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE delta_ctl.run_counts (
  table_name text NOT NULL,
  count_name text NOT NULL,
  row_count bigint NOT NULL DEFAULT 0,
  details jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (table_name, count_name)
);

CREATE TABLE delta_ctl.selection (
  table_name text NOT NULL,
  class text NOT NULL,
  PRIMARY KEY (table_name, class)
);

CREATE TABLE delta_ctl.row_selection (
  table_name text NOT NULL,
  class text NOT NULL,
  mode text NOT NULL CHECK (mode IN ('include', 'exclude')),
  kind text NOT NULL CHECK (kind IN ('id', 'row', 'corp')),
  value_from bigint,
  value_to bigint,
  corp_num text,
  is_range boolean NOT NULL DEFAULT false,
  source_line int NOT NULL,
  CHECK (
    (kind IN ('id', 'row') AND value_from IS NOT NULL AND value_to IS NOT NULL AND corp_num IS NULL)
    OR (kind = 'corp' AND value_from IS NULL AND value_to IS NULL AND corp_num IS NOT NULL)
  )
);
CREATE INDEX row_selection_lookup_idx
  ON delta_ctl.row_selection (table_name, class, mode, kind);

CREATE TABLE delta_ctl.selection_diagnostics (
  table_name text,
  class text,
  mode text,
  kind text,
  selector text,
  source_line int,
  matched bigint,
  problem text
);

CREATE TABLE delta_ctl.only_corps (
  corp_num text PRIMARY KEY
);

CREATE TABLE delta_ctl.dependency_violations (
  child_table text NOT NULL,
  parent_table text NOT NULL,
  reason text NOT NULL,
  row_count bigint NOT NULL,
  sample_ids text
);

CREATE TABLE delta_ctl.apply_counts (
  table_name text NOT NULL,
  class text NOT NULL,
  action text NOT NULL,
  expected_count bigint NOT NULL DEFAULT 0,
  affected_count bigint NOT NULL DEFAULT 0,
  PRIMARY KEY (table_name, class, action)
);

CREATE TABLE delta_ctl.touched_tables (
  table_name text PRIMARY KEY
);
