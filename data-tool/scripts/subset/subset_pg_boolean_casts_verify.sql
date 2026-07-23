-- Verify the one-time superuser bootstrap installed the DbSchemaCLI boolean casts.
-- Automatic explicit string I/O casts are not enough: DbSchemaCLI assignments require implicit pg_cast entries.
select 1 / case when count(*) = 2 then 1 else 0 end as required_implicit_boolean_casts_present
from pg_catalog.pg_cast
where castsource in ('varchar'::regtype, 'bpchar'::regtype)
  and casttarget = 'boolean'::regtype
  and castcontext = 'i';

-- Also verify representative values accepted by the installed conversion functions.
select 't'::varchar::boolean;
select 'f'::bpchar::boolean;
