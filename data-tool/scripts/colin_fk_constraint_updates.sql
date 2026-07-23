/*
FK constraint suppression for COLIN extract refreshes.

This module is included from colin_corps_extract_postgres_ddl with psql's
\ir command. Apply the base DDL with psql; do not point DbSchemaCLI or
SQLAlchemy directly at that DDL.

The procedures intentionally COMMIT after each constraint change. They must
therefore be invoked by a top-level CALL outside an explicit transaction.
The helper table makes interrupted drops and restores resumable.
*/

CREATE TABLE IF NOT EXISTS public.colin_dropped_fks
(
    table_schema name        NOT NULL,
    table_name   name        NOT NULL,
    conname      name        NOT NULL,
    condef       text        NOT NULL,
    dropped_at   timestamptz NOT NULL DEFAULT current_timestamp,
    CONSTRAINT pk_colin_dropped_fks
        PRIMARY KEY (table_schema, table_name, conname)
);

CREATE OR REPLACE PROCEDURE public.colin_fk_drop_all(
    OUT dropped_count bigint
)
LANGUAGE plpgsql
SECURITY INVOKER
AS $$
DECLARE
    fk record;
    constraint_definition text;
BEGIN
    dropped_count := 0;

    FOR fk IN
        SELECT
            constraint_row.oid AS constraint_oid,
            namespace.nspname AS table_schema,
            relation.relname AS table_name,
            constraint_row.conname
        FROM pg_catalog.pg_constraint AS constraint_row
        JOIN pg_catalog.pg_class AS relation
          ON relation.oid = constraint_row.conrelid
        JOIN pg_catalog.pg_namespace AS namespace
          ON namespace.oid = relation.relnamespace
        LEFT JOIN public.colin_dropped_fks AS dropped
          ON dropped.table_schema = namespace.nspname
         AND dropped.table_name = relation.relname
         AND dropped.conname = constraint_row.conname
        WHERE constraint_row.contype = 'f'
          AND relation.relkind = 'r'
          AND namespace.nspname = 'public'
          AND dropped.conname IS NULL
        ORDER BY namespace.nspname, relation.relname, constraint_row.conname
    LOOP
        -- Force pg_get_constraintdef() to schema-qualify every non-catalog
        -- relation, independent of the caller's search_path. SET LOCAL is
        -- intentionally repeated because each loop iteration commits.
        PERFORM pg_catalog.set_config('search_path', 'pg_catalog', true);
        constraint_definition := pg_catalog.pg_get_constraintdef(fk.constraint_oid);

        INSERT INTO public.colin_dropped_fks (
            table_schema,
            table_name,
            conname,
            condef
        )
        VALUES (
            fk.table_schema,
            fk.table_name,
            fk.conname,
            constraint_definition
        );

        EXECUTE pg_catalog.format(
            'ALTER TABLE %I.%I DROP CONSTRAINT %I',
            fk.table_schema,
            fk.table_name,
            fk.conname
        );

        dropped_count := dropped_count + 1;
        COMMIT;
    END LOOP;
END;
$$;

CREATE OR REPLACE PROCEDURE public.colin_fk_restore_all(
    OUT restored_count bigint
)
LANGUAGE plpgsql
SECURITY INVOKER
AS $$
DECLARE
    fk record;
    constraint_definition text;
BEGIN
    restored_count := 0;

    FOR fk IN
        SELECT
            table_schema,
            table_name,
            conname,
            condef
        FROM public.colin_dropped_fks
        ORDER BY table_schema, table_name, conname
    LOOP
        -- New captures contain qualified relation names. Keep public on a
        -- controlled path as backward-compatible recovery for helper rows
        -- captured by an earlier module version with unqualified names.
        PERFORM pg_catalog.set_config('search_path', 'pg_catalog, public', true);

        constraint_definition := pg_catalog.rtrim(fk.condef);
        IF constraint_definition !~* '[[:space:]]+NOT[[:space:]]+VALID[[:space:]]*$' THEN
            constraint_definition := constraint_definition || ' NOT VALID';
        END IF;

        EXECUTE pg_catalog.format(
            'ALTER TABLE %I.%I ADD CONSTRAINT %I %s',
            fk.table_schema,
            fk.table_name,
            fk.conname,
            constraint_definition
        );

        DELETE FROM public.colin_dropped_fks
        WHERE table_schema = fk.table_schema
          AND table_name = fk.table_name
          AND conname = fk.conname;

        restored_count := restored_count + 1;
        COMMIT;
    END LOOP;
END;
$$;

COMMENT ON TABLE public.colin_dropped_fks IS
'Foreign key definitions captured while a COLIN extract refresh is in progress.';

COMMENT ON PROCEDURE public.colin_fk_drop_all() IS
'Captures and drops every foreign key on ordinary tables in public, committing each drop for resumability.';

COMMENT ON PROCEDURE public.colin_fk_restore_all() IS
'Restores captured foreign keys as NOT VALID constraints, committing and removing each saved definition on success.';
