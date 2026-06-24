vset cli.settings.ignore_errors=false
vset cli.settings.transfer_threads=4
vset format.date=YYYY-MM-dd'T'hh:mm:ss'Z'
vset format.timestamp=YYYY-MM-dd'T'hh:mm:ss'Z'

connect cdev_pg_test;

learn schema colin_extract_temp;

-- cutoff timestamp
insert into colin_extract_temp.colin_extract_version (extracted_at)
values (current_timestamp);
