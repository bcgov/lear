-- Selection manifest structure, default behavior, dependencies, and selector assistance.
TRUNCATE delta_ctl.table_config, delta_ctl.run_metadata, delta_ctl.run_counts,
  delta_ctl.selection, delta_ctl.row_selection, delta_ctl.selection_diagnostics;
DROP SCHEMA delta_stage CASCADE; DROP SCHEMA delta_map CASCADE; DROP SCHEMA delta_diff CASCADE;
CREATE SCHEMA delta_stage; CREATE SCHEMA delta_map; CREATE SCHEMA delta_diff;

INSERT INTO delta_ctl.run_metadata(key, value) VALUES
  ('dump_sha256', 'manifest-test-sha'),
  ('manifest_default', 'new,changed');
INSERT INTO delta_ctl.table_config(table_name, load_phase, pk_col, fk_map) VALUES
  ('bad_emails', 10, 'id', '{}'::jsonb), -- NOSONAR
  ('selector_limit_boundary', 12, 'id', '{}'::jsonb), -- NOSONAR
  ('mig_batch', 15, NULL, -- NOSONAR
    '{"mig_group_id":"mig_group","external_id":"external:other.id"}'::jsonb),
  ('mig_group', 20, 'id', '{}'::jsonb), -- NOSONAR
  ('bar_corps', 30, NULL, '{}'::jsonb), -- NOSONAR
  ('corp_processing', 40, 'id', -- NOSONAR
    '{"mig_batch_id":"mig_batch","corp_num":"external:corporation.corp_num"}'::jsonb),
  ('auth_component_operation', 45, 'id', -- NOSONAR
    '{"auth_processing_id":"auth_processing"}'::jsonb);

CREATE TABLE delta_stage.bad_emails (
  id bigint,
  _delta_row_id bigint
);
CREATE TABLE delta_diff.bad_emails_class (
  _delta_row_id bigint,
  class text
);
INSERT INTO delta_stage.bad_emails(id, _delta_row_id) VALUES
  (2, 1), (3, 2), (5, 3), (7, 4), (9, 5);
INSERT INTO delta_diff.bad_emails_class(_delta_row_id, class) VALUES
  (1, 'NEW'), (2, 'NEW'), (3, 'NEW'), (4, 'CHANGED'), (5, 'CHANGED'); -- NOSONAR

CREATE TABLE delta_stage.selector_limit_boundary (
  id bigint,
  _delta_row_id bigint
);
CREATE TABLE delta_diff.selector_limit_boundary_class (
  _delta_row_id bigint,
  class text
);
INSERT INTO delta_stage.selector_limit_boundary(id, _delta_row_id)
SELECT CASE
         -- Five separated two-value runs force wrapped range/count pairs.
         WHEN n <= 10 THEN
           100000000000000::bigint + ((n - 1) / 2) * 3 + ((n - 1) % 2)
         -- Forty long, separated values force more than eight singleton lines
         -- and therefore exercise four-line visual paragraph breaks.
         WHEN n <= 50 THEN
           2000000000000000000::bigint + (n - 11) * 2
         ELSE 3000000000000000000::bigint
       END,
       n
FROM generate_series(1, 51) AS ids(n);
INSERT INTO delta_diff.selector_limit_boundary_class(_delta_row_id, class)
SELECT n, CASE WHEN n <= 50 THEN 'NEW' ELSE 'UNCHANGED' END
FROM generate_series(1, 51) AS ids(n);

CREATE TABLE delta_stage.mig_batch (
  _delta_row_id bigint
);
CREATE TABLE delta_diff.mig_batch_class (
  _delta_row_id bigint,
  class text
);
INSERT INTO delta_stage.mig_batch(_delta_row_id) VALUES (4), (5), (8), (10), (11);
INSERT INTO delta_diff.mig_batch_class(_delta_row_id, class) VALUES
  (4, 'NEW'), (5, 'NEW'), (8, 'NEW'), (10, 'CHANGED'), (11, 'CHANGED');

-- auth_component_operation supports corp: through this staged parent, not its own TSV columns.
CREATE TABLE delta_stage.auth_processing (
  id bigint,
  corp_num text,
  _delta_row_id bigint
);

INSERT INTO delta_ctl.run_counts(table_name, count_name, row_count) VALUES
  ('bad_emails', 'STAGED', 5), -- NOSONAR
  ('bad_emails', 'NEW', 3),
  ('bad_emails', 'CHANGED', 2),
  ('selector_limit_boundary', 'STAGED', 51),
  ('selector_limit_boundary', 'NEW', 50),
  ('mig_batch', 'STAGED', 5),
  ('mig_batch', 'NEW', 3),
  ('mig_batch', 'CHANGED', 2),
  ('mig_group', 'STAGED', 51),
  ('mig_group', 'NEW', 51),
  ('bar_corps', 'STAGED', 52),
  ('bar_corps', 'NEW', 52),
  ('corp_processing', 'STAGED', 106),
  ('corp_processing', 'NEW', 53),
  ('corp_processing', 'CHANGED', 53),
  ('auth_component_operation', 'STAGED', 54),
  ('auth_component_operation', 'NEW', 54);
