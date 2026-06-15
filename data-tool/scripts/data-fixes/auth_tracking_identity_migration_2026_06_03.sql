-- Description:
-- Extend COLIN extract auth tracking for repeatable auth operations.
--
-- This migration aligns existing databases with the source DDL changes in
-- data-tool/scripts/colin_corps_extract_postgres_ddl:
--   - adds operation identity columns to auth_processing;
--   - adds auth attempt identity audit context to auth_processing (not part of uniqueness);
--   - replaces the legacy unique constraint on (corp_num, flow_name, environment);
--   - creates auth_component_operation with ON DELETE CASCADE to auth_processing;
--   - backfills legacy auth_processing rows using the explicit mapping below.
--
-- Dry-run assumption:
--   Legacy dry-run rows are identified only when action_detail contains the token
--   'DRY_RUN'. Rows without that reliable marker are treated as real rows.

BEGIN;

CREATE SEQUENCE IF NOT EXISTS auth_component_operation_id_seq;
ALTER SEQUENCE auth_component_operation_id_seq OWNER TO postgres;

ALTER TABLE auth_processing
    ADD COLUMN IF NOT EXISTS operation varchar(25) DEFAULT 'CREATE' NOT NULL,
    ADD COLUMN IF NOT EXISTS operation_scope varchar(25) DEFAULT 'ENTITY' NOT NULL,
    ADD COLUMN IF NOT EXISTS operation_target varchar(500),
    ADD COLUMN IF NOT EXISTS repeatability varchar(25) DEFAULT 'ONE_SHOT' NOT NULL,
    ADD COLUMN IF NOT EXISTS attempt_key varchar(100) DEFAULT 'ONE_SHOT' NOT NULL,
    -- Auth attempt identity audit context only; not part of uniqueness.
    ADD COLUMN IF NOT EXISTS attempt_key_context text,
    ADD COLUMN IF NOT EXISTS dry_run boolean DEFAULT false NOT NULL;

-- Explicit legacy-row mapping table required by the implementation plan.
-- Inference notes:
--   * auth-affiliation-flow action_detail containing 'del_affiliations' maps to DELETE/AFFILIATION.
--   * auth-delete-flow with entity_action set maps to RESET/FULL_ENTITY.
--   * auth-delete-flow without entity_action maps to DELETE/INVITE when invite_action is set;
--     otherwise it maps to DELETE/AFFILIATION.
CREATE TEMP TABLE auth_processing_legacy_identity_map (
    legacy_flow_name varchar(100) PRIMARY KEY,
    default_operation varchar(25) NOT NULL,
    default_operation_scope varchar(25) NOT NULL,
    default_repeatability varchar(25) NOT NULL,
    notes text
) ON COMMIT DROP;

INSERT INTO auth_processing_legacy_identity_map (
    legacy_flow_name,
    default_operation,
    default_operation_scope,
    default_repeatability,
    notes
)
VALUES
    ('auth-create-flow', 'CREATE', 'ENTITY', 'ONE_SHOT',
     'One-shot entity create rows keep ONE_SHOT attempt identity.'),
    ('auth-contact-flow', 'UPSERT', 'CONTACT', 'REPEATABLE',
     'Repeatable contact upsert rows use flow_run_id, else LEGACY:<id>.'),
    ('auth-affiliation-flow', 'CREATE', 'AFFILIATION', 'REPEATABLE',
     'Infer DELETE from action_detail containing del_affiliations; default CREATE.'),
    ('auth-invite-flow', 'SEND', 'INVITE', 'REPEATABLE',
     'Repeatable invite send rows use flow_run_id, else LEGACY:<id>.'),
    ('auth-delete-flow', 'DELETE', 'AFFILIATION', 'REPEATABLE',
     'Infer RESET/FULL_ENTITY when entity_action is set; infer INVITE when invite_action is set; default AFFILIATION.');

WITH mapped AS (
    SELECT
        ap.id,
        CASE
            WHEN ap.flow_name = 'auth-affiliation-flow'
                 AND COALESCE(ap.action_detail, '') ILIKE '%del_affiliations%'
                THEN 'DELETE'
            WHEN ap.flow_name = 'auth-delete-flow'
                 AND ap.entity_action IS NOT NULL
                 AND ap.entity_action <> 'NOT_RUN'
                THEN 'RESET'
            WHEN ap.flow_name = 'auth-delete-flow'
                THEN 'DELETE'
            ELSE m.default_operation
        END AS operation,
        CASE
            WHEN ap.flow_name = 'auth-delete-flow'
                 AND ap.entity_action IS NOT NULL
                 AND ap.entity_action <> 'NOT_RUN'
                THEN 'FULL_ENTITY'
            WHEN ap.flow_name = 'auth-delete-flow'
                 AND ap.invite_action IS NOT NULL
                 AND ap.invite_action <> 'NOT_RUN'
                THEN 'INVITE'
            ELSE m.default_operation_scope
        END AS operation_scope,
        CASE
            WHEN ap.flow_name = 'auth-delete-flow'
                 AND ap.entity_action IS NOT NULL
                 AND ap.entity_action <> 'NOT_RUN'
                THEN 'RESET'
            ELSE m.default_repeatability
        END AS repeatability,
        (COALESCE(ap.action_detail, '') ILIKE '%DRY_RUN%') AS dry_run,
        CASE
            WHEN COALESCE(ap.action_detail, '') ILIKE '%DRY_RUN%'
                THEN 'DRY_RUN:' || COALESCE(ap.flow_run_id::text, ap.id::text)
            WHEN ap.flow_name = 'auth-create-flow'
                THEN 'ONE_SHOT'
            WHEN ap.flow_name = 'auth-delete-flow'
                 AND ap.entity_action IS NOT NULL
                 AND ap.entity_action <> 'NOT_RUN'
                THEN 'RESET'
            ELSE COALESCE(ap.flow_run_id::text, 'LEGACY:' || ap.id::text)
        END AS attempt_key
    FROM auth_processing ap
    JOIN auth_processing_legacy_identity_map m
      ON m.legacy_flow_name = ap.flow_name
)
UPDATE auth_processing ap
   SET operation = mapped.operation,
       operation_scope = mapped.operation_scope,
       repeatability = mapped.repeatability,
       dry_run = mapped.dry_run,
       attempt_key = mapped.attempt_key
  FROM mapped
 WHERE ap.id = mapped.id;

-- Replace the legacy uniqueness with operation/attempt identity.
ALTER TABLE auth_processing
    DROP CONSTRAINT IF EXISTS unq_auth_processing;

ALTER TABLE auth_processing
    ADD CONSTRAINT unq_auth_processing UNIQUE (
        corp_num,
        flow_name,
        environment,
        operation,
        operation_scope,
        attempt_key
    );

CREATE INDEX IF NOT EXISTS idx_auth_processing_claim_batch
    ON auth_processing (environment, flow_name, flow_run_id, processed_status, claimed_at);

CREATE INDEX IF NOT EXISTS idx_auth_processing_flow_env_status
    ON auth_processing (flow_name, environment, processed_status, corp_num);

CREATE INDEX IF NOT EXISTS idx_auth_processing_identity
    ON auth_processing (corp_num, flow_name, environment, operation, operation_scope, attempt_key);

CREATE INDEX IF NOT EXISTS idx_auth_processing_reset_guard
    ON auth_processing (corp_num, environment, flow_name, operation, operation_scope, dry_run, processed_status);

CREATE TABLE IF NOT EXISTS auth_component_operation
(
    id                  integer DEFAULT nextval('auth_component_operation_id_seq'::regclass) NOT NULL
        CONSTRAINT pk_auth_component_operation PRIMARY KEY,
    auth_processing_id  integer NOT NULL
        CONSTRAINT fk_auth_component_operation_auth_processing
            REFERENCES auth_processing (id) ON DELETE CASCADE,

    corp_num            varchar(10) NOT NULL,
    flow_name           varchar(100) NOT NULL,
    environment         varchar(25) NOT NULL,
    flow_run_id         uuid,

    operation           varchar(25) NOT NULL,
    operation_scope     varchar(25) NOT NULL,
    component           varchar(25) NOT NULL,
    target_type         varchar(50),
    target_value        varchar(500),
    action              varchar(50),
    status_code         integer,
    error               varchar(1000),
    detail              varchar(2000),
    dry_run             boolean DEFAULT false NOT NULL,
    create_date         timestamp with time zone DEFAULT current_timestamp NOT NULL
);

ALTER TABLE auth_component_operation OWNER TO postgres;

CREATE INDEX IF NOT EXISTS idx_auth_component_operation_auth_processing_id
    ON auth_component_operation (auth_processing_id);

CREATE INDEX IF NOT EXISTS idx_auth_component_operation_lookup
    ON auth_component_operation (corp_num, environment, flow_name, create_date);

COMMIT;

-- Verification helpers (run manually after migration):
-- SELECT flow_name, operation, operation_scope, repeatability, dry_run, count(*)
--   FROM auth_processing
--  GROUP BY flow_name, operation, operation_scope, repeatability, dry_run
--  ORDER BY flow_name, operation, operation_scope, repeatability, dry_run;
--
-- SELECT conname, pg_get_constraintdef(oid)
--   FROM pg_constraint
--  WHERE conrelid = 'auth_processing'::regclass
--    AND conname = 'unq_auth_processing';
