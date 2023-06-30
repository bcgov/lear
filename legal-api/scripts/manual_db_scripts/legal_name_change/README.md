
## DB Model & Data Migration Steps
The following will serve as steps required to get the LEAR database model and data up to date to support the [legal name changes](https://app.zenhub.com/workspaces/entities-team-space-6143567664fb320019b81f39/issues/gh/bcgov/entity/15527).  Note that as a part of the legal name changes, the database was updated to no longer use sqlcontinuum as the database versioning mechanism.

### 1. Transfer LEAR data in old data model to new LEAR database model
1. Create a new empty new LEAR database and apply the new data model using alembic scripts.
2. Install dbshell -  [DbShell | Free Universal SQL Command-Line Client](https://dbschema.com/dbshell.html)  More general info around configuration and data transfer can be found at [DbShell | Multi-Database SQL Command Line Client](https://dbschema.com/documentation/dbshell.html)
3. Add `/Applications/DbShell` to path
4. Register source db by adding db connection in  `~/.DbSchema/dbshell/init.sql`
   e.g. `connection lear_old PostgreSql "user=postgres password=postgres host=localhost port=5432 db=lear"`
5. Register target db by adding db connection in  `~/.DbSchema/dbshell/init.sql`
   e.g. `connection lear_new PostgreSql "user=postgres password=postgres host=localhost port=5432 db=lear_new"`
6. Prep new LEAR db for data transfer.
   Run `<lear-repo-base-path>/legal-api/scripts/manual_db_scripts/legal_name_change/transfer_to_new_lear_before.sql` against new LEAR db
7. Transfer data from old LEAR to new LEAR db
   `dbshell <lear-repo-base-path>/legal-api/scripts/manual_db_scripts/legal_name_change/transfer_to_new_lear.sql`
   A successful run will look like the following:
``` bash

(legal-api-py3.10) argus@Argus-Mac-Studio ~/h3/git/bcreg/lear/legal-api (dev_legal_name_changes) $ dbshell /Users/argus/h3/git/bcreg/lear/legal-api/scripts/manual_db_scripts/legal_name_change/transfer_to_new_lear.sql
DbShell 1.3.2 Build #210311
Type 'help' for a list of commands.

Processing file /Users/argus/h3/git/bcreg/lear/legal-api/scripts/manual_db_scripts/legal_name_change/transfer_to_new_lear.sql

...

Transfer using 8 thread(s) users ...                                368 rows in 00:01. Reader waited 00:00, writer 00:08.
Transfer using 8 thread(s) users_history ...                        472 rows in 00:01. Reader waited 00:00, writer 00:08.
Transfer using 8 thread(s) legal_entities ...                       3707 rows in 00:01. Reader waited 00:00, writer 00:08.
Transfer using 8 thread(s) legal_entities_history ...               19232 rows in 00:01. Reader waited 00:00, writer 00:09.
Transfer using 8 thread(s) filings ...                              32674 rows in 00:02. Reader waited 00:00, writer 00:09.
Transfer using 8 thread(s) addresses ...                            28079 rows in 00:01. Reader waited 00:00, writer 00:08.
Transfer using 8 thread(s) addresses_history ...                    31928 rows in 00:01. Reader waited 00:00, writer 00:08.
Transfer using 8 thread(s) aliases ...                              551 rows in 00:01. Reader waited 00:00, writer 00:08.
Transfer using 8 thread(s) aliases_history ...                      756 rows in 00:01. Reader waited 00:00, writer 00:08.
Transfer using 8 thread(s) colin_event_ids ...                      27857 rows in 00:01. Reader waited 00:00, writer 00:08.
Transfer using 8 thread(s) colin_last_update ...                    34 rows in 00:01. Reader waited 00:00, writer 00:08.
Transfer using 8 thread(s) comments ...                             1205 rows in 00:01. Reader waited 00:00, writer 00:08.
Transfer using 8 thread(s) dc_connections ...                       28 rows in 00:01. Reader waited 00:00, writer 00:08.
Transfer using 8 thread(s) dc_definitions ...                       1 rows in 00:01. Reader waited 00:00, writer 00:08.
Transfer using 8 thread(s) dc_issued_credentials ...                13 rows in 00:01. Reader waited 00:00, writer 00:08.
Transfer using 8 thread(s) documents ...                            457 rows in 00:01. Reader waited 00:00, writer 00:08.
Transfer using 8 thread(s) documents_history ...                    457 rows in 00:01. Reader waited 00:00, writer 00:08.
Transfer using 8 thread(s) offices ...                              4347 rows in 00:01. Reader waited 00:00, writer 00:08.
Transfer using 8 thread(s) offices_history ...                      5863 rows in 00:01. Reader waited 00:00, writer 00:08.
Transfer using 8 thread(s) parties ...                              11901 rows in 00:01. Reader waited 00:00, writer 00:08.
Transfer using 8 thread(s) parties_history ...                      12828 rows in 00:01. Reader waited 00:00, writer 00:08.
Transfer using 8 thread(s) party_roles ...                          13307 rows in 00:01. Reader waited 00:00, writer 00:08.
Transfer using 8 thread(s) party_roles_history ...                  14360 rows in 00:01. Reader waited 00:00, writer 00:08.
Transfer using 8 thread(s) registration_bootstrap ...               2722 rows in 00:01. Reader waited 00:00, writer 00:08.
Transfer using 8 thread(s) request_tracker ...                      830 rows in 00:01. Reader waited 00:00, writer 00:08.
Transfer using 8 thread(s) resolutions ...                          271 rows in 00:01. Reader waited 00:00, writer 00:08.
Transfer using 8 thread(s) resolutions_history ...                  271 rows in 00:01. Reader waited 00:00, writer 00:08.
Transfer using 8 thread(s) share_classes ...                        1037 rows in 00:02. Reader waited 00:00, writer 00:08.
Transfer using 8 thread(s) share_classes_history ...                2166 rows in 00:01. Reader waited 00:00, writer 00:08.
Transfer using 8 thread(s) share_series ...                         137 rows in 00:01. Reader waited 00:00, writer 00:08.
Transfer using 8 thread(s) share_series_history ...                 573 rows in 00:01. Reader waited 00:00, writer 00:08.
Transfer using 8 thread(s) consent_continuation_outs ...            11 rows in 00:01. Reader waited 00:00, writer 00:08.
Transfer using 8 thread(s) sent_to_gazette ...                      1038 rows in 00:01. Reader waited 00:00, writer 00:08.


...

Done

```

### 2. Migrate data in new LEAR database for legal name changes

1. Run `<lear-repo-base-path>/legal-api/scripts/manual_db_scripts/legal_name_change/legal_name_updates.sql` against new LEAR db
2. Cleanup temporary artifacts and states created by data transfer scripts.
   Run `<lear-repo-base-path>/legal-api/scripts/manual_db_scripts/legal_name_change/transfer_to_new_lear_after.sql` against new LEAR db

