
### Steps to Transfer COLIN(Oracle) Corps Data to PostgreSQL Extract Database 

1. Create empty postgres extract db
   `createdb -h localhost -p 5432 -U postgres -T template0 colin-mig-corps-data-test`
2. Create COLIN corps postgres extract table structure via ddl in `/data-tool/scripts/colin_corps_extract_postgres_ddl`
3. Install dbshell -  [DbShell | Free Universal SQL Command-Line Client](https://dbschema.com/dbshell.html)  More general info around configuration and data transfer can be found at [DbShell | Multi-Database SQL Command Line Client](https://dbschema.com/documentation/dbshell.html)
4. Add `/Applications/DbShell` to path
5. Register extract source db by adding db connection in  `~/.DbSchema/dbshell/init.sql`
   e.g. `connection cprd Oracle "user=<some_user> password=<some_password> host=<host_name> db=<SID>"`
5. Register extract target db by adding db connection in  `~/.DbSchema/dbshell/init.sql`
   e.g. `connection cprd_pg PostgreSql "user=postgres password=<some_password> host=localhost db=colin-mig-corps-data-test"`
6. Disable triggers in target extract db using sql snippet found in `misc_extract_corps_queries.sql`
7. Transfer data `dbshell <lear-repo-base-path>/data-tool/scripts/transfer_cprd_corps.sql`
8. Successful output will look something like following:
```
argus@Argus-Mac ~/h3/git/bcreg/lear/data-tool/scripts $ dbshell /Users/argus/h3/git/bcreg/lear/data-tool/scripts/transfer_cprd_corps.sql
DbShell 1.3.2 Build #210311
Type 'help' for a list of commands.

Processing file /Users/argus/h3/git/bcreg/lear/data-tool/scripts/transfer_cprd_corps.sql
Connected

Transfer using 4 thread(s) corporation ...                          5 rows in 00:01. Reader waited 00:00, writer 00:04.
Transfer using 4 thread(s) event ...                                5 rows in 00:01. Reader waited 00:00, writer 00:04.
Transfer using 4 thread(s) corp_name ...                            5 rows in 00:01. Reader waited 00:00, writer 00:04.
Transfer using 4 thread(s) corp_state ...                           5 rows in 00:01. Reader waited 00:00, writer 00:04.
Transfer using 4 thread(s) filing ...                               5 rows in 00:01. Reader waited 00:00, writer 00:04.
Transfer using 4 thread(s) filing_user ...                          5 rows in 00:01. Reader waited 00:00, writer 00:04.
Transfer using 4 thread(s) office ...                               5 rows in 00:01. Reader waited 00:00, writer 00:04.
...
```
8. Re-enable triggers in target extract db using sql snippet found in `misc_extract_corps_queries.sql`
9. Re-index target extract db.


Notes: Update number of threads(`vset transfer.threads=4`) to use as appropriate in `transfer_cprd_corps.sql`.   
