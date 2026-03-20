-- Generate dependency-safe DROP statements for the COLIN extract derived view layer.
--
-- Usage examples:
--   psql -X -qAt -v schema_name=public \
--     -f data-tool/scripts/colin_corps_extract_generate_view_drop.sql
--
-- The script:
--   - scopes itself to an allowlist of COLIN-owned views/materialized views
--   - raises an error if an allowlisted object exists with the wrong kind
--   - raises an error if any non-allowlisted view/materialized view depends on an allowlisted object
--   - emits DROP statements in dependency-safe reverse order
--   - emits comment lines for missing allowlisted objects
--
-- Pipe the output back into psql to execute the drop plan, or use
-- data-tool/reset_colin_extract_views.sh for a higher-level wrapper.

\if :{?schema_name}
\else
\set schema_name public
\endif

SET colin_extract.reset_schema TO :'schema_name';

CREATE TEMP TABLE IF NOT EXISTS colin_extract_reset_allowlist (
  obj_name text PRIMARY KEY,
  expected_relkind "char" NOT NULL CHECK (expected_relkind IN ('v', 'm'))
);

TRUNCATE colin_extract_reset_allowlist;

INSERT INTO colin_extract_reset_allowlist (obj_name, expected_relkind)
VALUES
  ('v_addr_links', 'v'),
  ('v_addr_issues', 'v'),
  ('v_business_state', 'v'),
  ('v_corp_issue_flags_long', 'v'),
  ('mv_corps_with_officers', 'm'),
  ('mv_corps_party_role_count', 'm'),
  ('mv_admin_email_count', 'm'),
  ('mv_admin_email_domain_count', 'm'),
  ('mv_addr_quality_by_corp', 'm'),
  ('mv_share_class_issue_flags', 'm'),
  ('mv_legacy_corps_data', 'm'),
  ('mv_corp_issue_flags', 'm'),
  ('mv_issue_counts_by_corp_type', 'm');

DO $$
DECLARE
  v_schema text := current_setting('colin_extract.reset_schema');
  v_wrong_type_details text;
  v_external_dep_details text;
BEGIN
  WITH schema_ns AS (
    SELECT oid
    FROM pg_namespace
    WHERE nspname = v_schema
  ),
  existing AS (
    SELECT
      a.obj_name,
      a.expected_relkind,
      c.oid,
      c.relkind
    FROM pg_temp.colin_extract_reset_allowlist a
    LEFT JOIN schema_ns ns ON TRUE
    LEFT JOIN pg_class c
      ON c.relnamespace = ns.oid
     AND c.relname = a.obj_name
  )
  SELECT string_agg(
           format('%I.%I exists as relkind=%s but expected=%s',
                  v_schema,
                  obj_name,
                  relkind,
                  expected_relkind),
           E'\n'
         )
    INTO v_wrong_type_details
  FROM existing
  WHERE oid IS NOT NULL
    AND relkind <> expected_relkind;

  IF v_wrong_type_details IS NOT NULL THEN
    RAISE EXCEPTION
      USING MESSAGE = format(
        'Refusing to generate drop SQL because one or more allowlisted objects in schema %I have the wrong kind:%s%s',
        v_schema,
        E'\n',
        v_wrong_type_details
      );
  END IF;

  WITH src_objs AS (
    SELECT c.oid, n.nspname AS schema_name, c.relname AS obj_name
    FROM pg_class c
    JOIN pg_namespace n
      ON n.oid = c.relnamespace
    JOIN pg_temp.colin_extract_reset_allowlist a
      ON a.obj_name = c.relname
    WHERE n.nspname = v_schema
      AND c.relkind IN ('v', 'm')
  ),
  external_dependents AS (
    SELECT DISTINCT
      format('%I.%I depends on %I.%I',
             dep_n.nspname,
             dep_c.relname,
             src.schema_name,
             src.obj_name) AS detail
    FROM src_objs src
    JOIN pg_depend d
      ON d.refobjid = src.oid
     AND d.deptype = 'n'
    JOIN pg_rewrite rw
      ON rw.oid = d.objid
    JOIN pg_class dep_c
      ON dep_c.oid = rw.ev_class
     AND dep_c.relkind IN ('v', 'm')
    JOIN pg_namespace dep_n
      ON dep_n.oid = dep_c.relnamespace
    LEFT JOIN pg_temp.colin_extract_reset_allowlist dep_allow
      ON dep_allow.obj_name = dep_c.relname
     AND dep_n.nspname = v_schema
    WHERE dep_allow.obj_name IS NULL
      AND dep_n.nspname NOT IN ('pg_catalog', 'information_schema')
  )
  SELECT string_agg(detail, E'\n')
    INTO v_external_dep_details
  FROM external_dependents;

  IF v_external_dep_details IS NOT NULL THEN
    RAISE EXCEPTION
      USING MESSAGE = format(
        'Refusing to generate drop SQL because unexpected external view/materialized-view dependents exist:%s%s',
        E'\n',
        v_external_dep_details
      );
  END IF;
END $$;

WITH params AS (
  SELECT :'schema_name'::text AS target_schema
),
existing AS (
  SELECT
    p.target_schema,
    a.obj_name,
    a.expected_relkind,
    c.oid
  FROM params p
  CROSS JOIN pg_temp.colin_extract_reset_allowlist a
  LEFT JOIN pg_namespace n
    ON n.nspname = p.target_schema
  LEFT JOIN pg_class c
    ON c.relnamespace = n.oid
   AND c.relname = a.obj_name
)
SELECT format('-- Missing %s %I.%I; skipping drop and expecting recreate on reapply.',
              CASE expected_relkind
                WHEN 'm' THEN 'materialized view'
                ELSE 'view'
              END,
              target_schema,
              obj_name)
FROM existing
WHERE oid IS NULL
ORDER BY obj_name ASC;

WITH RECURSIVE params AS (
  SELECT :'schema_name'::text AS target_schema
),
existing AS (
  SELECT
    n.nspname AS schema_name,
    c.relname AS obj_name,
    c.oid,
    c.relkind
  FROM params p
  JOIN pg_namespace n
    ON n.nspname = p.target_schema
  JOIN pg_class c
    ON c.relnamespace = n.oid
  JOIN pg_temp.colin_extract_reset_allowlist a
    ON a.obj_name = c.relname
   AND a.expected_relkind = c.relkind
),
edges AS (
  SELECT DISTINCT
    dep_c.oid AS dependent_oid,
    src_c.oid AS source_oid
  FROM pg_depend d
  JOIN pg_rewrite rw
    ON rw.oid = d.objid
  JOIN pg_class dep_c
    ON dep_c.oid = rw.ev_class
   AND dep_c.relkind IN ('v', 'm')
  JOIN pg_class src_c
    ON src_c.oid = d.refobjid
   AND src_c.relkind IN ('v', 'm')
  JOIN existing dep_e
    ON dep_e.oid = dep_c.oid
  JOIN existing src_e
    ON src_e.oid = src_c.oid
  WHERE d.deptype = 'n'
    AND dep_c.oid <> src_c.oid
),
depths AS (
  SELECT e.oid, 0 AS depth
  FROM existing e

  UNION

  SELECT ed.dependent_oid, depths.depth + 1
  FROM edges ed
  JOIN depths
    ON depths.oid = ed.source_oid
),
ordered AS (
  SELECT
    e.schema_name,
    e.obj_name,
    e.relkind,
    COALESCE(MAX(d.depth), 0) AS depth
  FROM existing e
  LEFT JOIN depths d
    ON d.oid = e.oid
  GROUP BY e.schema_name, e.obj_name, e.relkind
)
SELECT format('DROP %s IF EXISTS %I.%I;',
              CASE relkind
                WHEN 'm' THEN 'MATERIALIZED VIEW'
                ELSE 'VIEW'
              END,
              schema_name,
              obj_name)
FROM ordered
ORDER BY depth DESC, obj_name ASC;
