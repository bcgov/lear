vset cli.settings.ignore_errors=false
vset cli.settings.replace_variables=false
vset cli.settings.transfer_threads=4
vset format.date=YYYY-MM-dd'T'hh:mm:ss'Z'
vset format.timestamp=YYYY-MM-dd'T'hh:mm:ss'Z'

connect cprd_pg_subset;
-- Serialize subset runs on this target DB.
execute /home/kdeodhar/repos/lear/data-tool/scripts/subset/subset_pg_acquire_advisory_lock.sql

-- Prepare shared address staging table before learning schema
execute /home/kdeodhar/repos/lear/data-tool/scripts/subset/subset_pg_prepare_address_stage.sql
learn schema public;

truncate table public.colin_extract_version; insert into public.colin_extract_version (extracted_at) values (current_timestamp); 

-- Postgres fast-load mode (session-level settings)
execute /home/kdeodhar/repos/lear/data-tool/scripts/subset/subset_pg_fastload_begin.sql

-- Postgres helper: allow VARCHAR/BPCHAR -> BOOLEAN assignment (DbSchemaCLI boolean inserts)
execute /home/kdeodhar/repos/lear/data-tool/scripts/subset/subset_pg_boolean_casts.sql
-- Fail-fast: verify varchar/bpchar -> boolean casts exist
select 't'::varchar::boolean;
select 'f'::bpchar::boolean;

execute /home/kdeodhar/repos/lear/data-tool/scripts/subset/subset_disable_triggers.sql

-- global cars* refresh (not corp-scoped; full dataset truncate + reload)
execute /home/kdeodhar/repos/lear/data-tool/scripts/subset/subset_delete_cars.sql
execute /home/kdeodhar/repos/lear/data-tool/scripts/subset/subset_transfer_cars.sql

-- transfer corp-scoped subset from Oracle to Postgres
-- transfer chunk 001/001
execute /home/kdeodhar/repos/lear/data-tool/scripts/_generated/subset_load_chunks/transfer_all.sql

-- purge BCOMPS-excluded corps (computed in Postgres after load)
execute /home/kdeodhar/repos/lear/data-tool/scripts/subset/subset_pg_purge_bcomps_excluded.sql

execute /home/kdeodhar/repos/lear/data-tool/scripts/subset/subset_enable_triggers.sql

-- Cleanup shared address staging table
execute /home/kdeodhar/repos/lear/data-tool/scripts/subset/subset_pg_cleanup_address_stage.sql

-- Release subset-run advisory lock
execute /home/kdeodhar/repos/lear/data-tool/scripts/subset/subset_pg_release_advisory_lock.sql

-- Reset Postgres fast-load session settings
execute /home/kdeodhar/repos/lear/data-tool/scripts/subset/subset_pg_fastload_end.sql
