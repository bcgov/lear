
### Steps to Transfer COLIN(Oracle) Corps Data to PostgreSQL Extract Database 

1. Create empty postgres extract db
   `createdb -h localhost -p 5432 -U postgres -T template0 colin-mig-corps-data-test`
2. Create COLIN corps postgres extract table structure via ddl in `/data-tool/scripts/colin_corps_extract_postgres_ddl`
```
# create empty db for the first time
createdb -h localhost -p 5432 -U postgres -T template0 colin-mig-corps-data-test && \
psql -h localhost -p 5432 -U postgres -d colin-mig-corps-data-test -f <lear-repo-base-path>/data-tool/scripts/colin_corps_extract_postgres_ddl

# kill connection & recreate empty db
psql -h localhost -p 5432 -U postgres -d colin-mig-corps-data-test -c "SELECT pg_terminate_backend(pg_stat_activity.pid) FROM pg_stat_activity WHERE datname = 'colin-mig-corps-data-test' AND pid <> pg_backend_pid();" && \
dropdb -h localhost -p 5432 -U postgres colin-mig-corps-data-test && \
createdb -h localhost -p 5432 -U postgres -T template0 colin-mig-corps-data-test && \
psql -h localhost -p 5432 -U postgres -d colin-mig-corps-test -f <lear-repo-base-path>/data-tool/scripts/colin_corps_extract_postgres_ddl
```
3. Install DbSchemaCLI (previously named DbShell) -  [DbSchemaCLI | Free Universal SQL Command-Line Client](https://dbschema.com/dbschemacli.html). More general info around configuration and data transfer can be found at [DbSchemaCLI | Universal Command Line Client](https://dbschema.com/documentation/dbschemacli.html)
4. Add `/Applications/DbSchema` to path
5. Register Oracle driver and extract source db in `~/.DbSchema/cli/init.sql`
```
register driver Oracle oracle.jdbc.OracleDriver jdbc:oracle:thin:@<host>:<port>:<db> "port=1521"
connection cprd -d Oracle -u <some_user> -p <some_password> -h <host_name> -P <port> -D <database_name>
```
6. Register PostgreSQL driver and extract target db in  `~/.DbSchema/cli/init.sql`
```
register driver PostgreSql org.postgresql.Driver jdbc:postgresql://<host>:<port>/<db> "port=5432"
connection cprd_pg -d PostgreSql -u postgres -p <some_password> -h localhost -P <port> -D colin-mig-corps-data-test
```
7. Transfer data `dbschemacli <lear-repo-base-path>/data-tool/scripts/transfer_cprd_corps.sql`
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
9. Re-index target extract db.
10. Use "count overview" SQL snippet in `misc_extract_corps_queries.sql` to verify the db changes.


Notes:
1. Update number of threads (e.g. `vset cli.settings.transfer_threads=4`) to use as appropriate in `transfer_cprd_corps.sql`.
2. As of November 4, 2024, the database extract script runs without error using DbSchemaCLI 9.4.3
