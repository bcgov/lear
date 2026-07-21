SET search_path TO TARGET_SCHEMA;

DO $body$
declare
    r record;
begin
    for r in 
        select n.nspname as schema_name,
        c.relname as table_name,
        con.conname as constraint_name
        from pg_constraint con
        join pg_class c on c.oid = con.conrelid
        join pg_namespace n on n.oid = c.relnamespace
        where con.contype = 'f'
        and n.nspname = 'colin_extract'
        order by c.relname, con.conname
    loop
        execute format(
            'ALTER TABLE %I.%I DROP CONSTRAINT',
            r.schema_name,
            r.table_name,
            r.constraint_name
        );
    end loop;
end
$body$;
