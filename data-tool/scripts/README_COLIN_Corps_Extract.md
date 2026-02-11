### Steps to Transfer COLIN(Oracle) Corps Data to PostgreSQL Extract Database 

## Full refresh (existing workflow)

1. Create empty postgres extract db
   `createdb -h localhost -p 5432 -U postgres -T template0 colin-mig-corps-data-test`

2. Create COLIN corps postgres extract table structure via ddl in `/data-tool/scripts/colin_corps_extract_postgres_ddl`

### create empty db for the first time
```bash
createdb -h localhost -p 5432 -U postgres -T template0 colin-mig-corps-data-test &&
psql -h localhost -p 5432 -U postgres -d colin-mig-corps-data-test -f <lear-repo-base-path>/data-tool/scripts/colin_corps_extract_postgres_ddl

kill connection & recreate empty db

psql -h localhost -p 5432 -U postgres -d colin-mig-corps-data-test -c "SELECT pg_terminate_backend(pg_stat_activity.pid) FROM pg_stat_activity WHERE datname = 'colin-mig-corps-data-test' AND pid <> pg_backend_pid();" &&
dropdb -h localhost -p 5432 -U postgres colin-mig-corps-data-test &&
createdb -h localhost -p 5432 -U postgres -T template0 colin-mig-corps-data-test &&
psql -h localhost -p 5432 -U postgres -d colin-mig-corps-test -f <lear-repo-base-path>/data-tool/scripts/colin_corps_extract_postgres_ddl
```

3. Install DbSchemaCLI (previously named DbShell) - [DbSchemaCLI | Free Universal SQL Command-Line Client](https://dbschema.com/dbschemacli.html).
   More general info around configuration and data transfer can be found at: [DbSchemaCLI | Universal Command Line Client](https://dbschema.com/documentation/dbschemacli.html)

4. Add `/Applications/DbSchema` to path

5. Register Oracle driver and extract source db in `~/.DbSchema/cli/init.sql`
```bash
register driver Oracle oracle.jdbc.OracleDriver jdbc:oracle:thin:@<host>:<port>:<db> "port=1521"
connection cprd -d Oracle -u <some_user> -p <some_password> -h <host_name> -P <port> -D <database_name>
```

6. Register PostgreSQL driver and extract target db in `~/.DbSchema/cli/init.sql`
```bash
register driver PostgreSql org.postgresql.Driver jdbc:postgresql://<host>:<port>/<db> "port=5432"
connection cprd_pg -d PostgreSql -u postgres -p <some_password> -h localhost -P <port> -D colin-mig-corps-data-test
```

7. Transfer data (full refresh)
   `dbschemacli <lear-repo-base-path>/data-tool/scripts/transfer_cprd_corps.sql`

8. Successful output will look something like following:
```bash
argus@Argus-Mac ~/h3/git/bcreg/lear/data-tool/scripts $ dbschemacli /Users/argus/h3/git/bcreg/lear/data-tool/scripts/transfer_cprd_corps.sql
DbSchemaCLI #250319
Type 'help' for a list of commands.

Processing file /Users/argus/h3/git/bcreg/lear/data-tool/scripts/transfer_cprd_corps.sql
Connected

Transfer using 8 thread(s) corporation ...      2936 rows in 00:39. Reader waited 00:00, writer 03:21.
Transfer using 8 thread(s) event ...            22415 rows in 00:16. Reader waited 00:00, writer 01:13.
Transfer using 8 thread(s) corp_name ...        3171 rows in 00:16. Reader waited 00:00, writer 01:04.
Transfer using 8 thread(s) corp_state ...       2939 rows in 00:17. Reader waited 00:00, writer 01:20.
Transfer using 8 thread(s) filing ...           21680 rows in 00:24. Reader waited 00:00, writer 02:08.
Transfer using 8 thread(s) filing_user ...      20889 rows in 00:27. Reader waited 00:00, writer 02:17.
...
```

9. Re-index target extract db.

10. Use "count overview" SQL snippet in `misc_extract_corps_queries.sql` to verify the db changes.

Notes:
1. Update number of threads (e.g. `vset cli.settings.transfer_threads=4`) to use as appropriate in `transfer_cprd_corps.sql`.
2. As of February 2026, the database extract script runs without error using DbSchema 9.7.1(DbSchemaCLI #250319).

---

## Subset refresh / subset load (corp-id list; 10k+ supported)

This workflow is for when you want to:
- **refresh**: delete + reload a specific list of businesses in an existing Postgres extract DB, or
- **load**: load only a specific list of businesses (useful for empty/sandbox extract DBs).

Key constraints handled:
- No Oracle temp tables required.
- Oracle IN-list limit (~1000 items) is handled via `--oracle-in-strategy` (default `auto`) using `--chunk-size` (default 900).
- Subset scripts do **not** run boolean↔integer ALTER COLUMN TYPE flips (important when the extract DB is already populated).

### Files involved

Core templates (always used in subset workflow):
- `data-tool/scripts/subset/subset_disable_triggers.sql`
- `data-tool/scripts/subset/subset_enable_triggers.sql`
- `data-tool/scripts/subset/subset_delete_chunk.sql`
- `data-tool/scripts/subset/subset_transfer_chunk.sql`
- `data-tool/scripts/subset/subset_pg_boolean_casts.sql` (required so DbSchemaCLI can insert 't'/'f' into boolean columns)
- `data-tool/scripts/subset/subset_pg_purge_bcomps_excluded.sql` (run once after transfer)

Optional Postgres session performance templates (only when `--pg-fastload` is used):
- `data-tool/scripts/subset/subset_pg_fastload_begin.sql`
- `data-tool/scripts/subset/subset_pg_fastload_end.sql`

cars* global refresh templates (only when cars are included; skipped with `--no-cars`):
- `data-tool/scripts/subset/subset_delete_cars.sql`
- `data-tool/scripts/subset/subset_transfer_cars.sql`

Generator:
- `data-tool/scripts/generate_cprd_subset_extract.py`

Generated scripts (gitignored by default):
- **Main script**: runs templates + the per-chunk scripts, e.g. `data-tool/scripts/_generated/subset_refresh.sql`
- **Chunk scripts**: generated per chunk in `data-tool/scripts/_generated/chunks/`
  - `subset_delete_chunk_0001.sql`, `subset_transfer_chunk_0001.sql`, etc.

### Steps

1. Put your corp list into a text file, 1 per line (comments allowed using `#`).
   Example: `data-tool/scripts/corp_ids.txt`

2. Generate the subset scripts:

   **Refresh mode** (delete then reload those corps):
   ```bash
   python <lear-repo-base-path>/data-tool/scripts/generate_cprd_subset_extract.py \
     --corp-file <lear-repo-base-path>/data-tool/scripts/corp_ids.txt \
     --mode refresh \
     --chunk-size 500 \
     --threads 4 \
     --pg-fastload \ 
     --pg-disable-method replica_role \   
     --out <lear-repo-base-path>/data-tool/scripts/_generated/subset_refresh.sql
   ```

   **Load mode** (load only those corps; no deletes):
   ```bash
   python <lear-repo-base-path>/data-tool/scripts/generate_cprd_subset_extract.py \
     --corp-file <lear-repo-base-path>/data-tool/scripts/corp_ids.txt \
     --mode load \
     --chunk-size 500 \
     --threads 4 \
     --pg-fastload \ 
     --pg-disable-method replica_role \      
     --out <lear-repo-base-path>/data-tool/scripts/_generated/subset_load.sql
   ```

   Optional performance flags:
   - Add `--pg-fastload` to enable Postgres session settings for faster bulk writes (templates `subset_pg_fastload_begin.sql` / `subset_pg_fastload_end.sql`).
   - Use `--pg-disable-method replica_role` (default) or `session_replication_role` to suppress triggers during load.

3. Run the generated main script with DbSchemaCLI:

   ```bash
   dbschemacli <lear-repo-base-path>/data-tool/scripts/_generated/subset_refresh.sql
   ```
   OR
   ```bash
   dbschemacli <lear-repo-base-path>/data-tool/scripts/_generated/subset_load.sql
   ```

    
### Notes / gotchas

- Chunk size is configurable. Keep `--chunk-size` <= 1000 to avoid Oracle IN-list failures.
- For small/medium subsets, consider `--oracle-in-strategy or_of_in_lists` (or leave it as the default `auto`) to avoid repeating the full transfer suite per chunk. See **Oracle IN-list strategy** below for details.
- Subset scripts automatically install a Postgres helper cast to allow DbSchemaCLI inserts of `t/f` into boolean columns.
- DbSchemaCLI build issue: If you get errors about `"bsh: for: No collection"` ensure you are using DbSchemaCLI 9.4.3+.
- If `--no-cars` is used, cars* tables are skipped entirely.
- Chunk templates are rendered at generation time (inline mode), so the resulting SQL is self-contained.
- If you need legacy runtime substitution behavior, generate with `--render-mode vset` (uses DbSchemaCLI `vset` + &placeholders).

### Oracle IN-list strategy (`--oracle-in-strategy`)

Oracle has a practical limit of ~1000 items per `IN (...)` list. The subset generator supports two ways to stay under that limit, which are easy to conflate:

1. **Transfer execution chunking**: how many times we run the full transfer suite (all table transfers).
2. **IN-list grouping**: how many `IN (...)` groups are OR'd together inside a single transfer query.

Both are driven by `--chunk-size`, but you only get execution chunking when `--oracle-in-strategy` is `chunk_files` (or `auto` decides to fall back to it).

#### Decision logic

- `--oracle-in-strategy chunk_files`
  Always uses **transfer execution chunking**. The generator repeats the full transfer suite once per chunk: `ceil(N / chunk_size)` passes.

- `--oracle-in-strategy or_of_in_lists`
  Uses **IN-list grouping** inside the Oracle predicate so the transfer suite runs **once**, while still respecting the per-`IN` limit. The predicate looks like:
  `(corp_num IN (...<=chunk_size...)) OR (corp_num IN (...<=chunk_size...)) OR ...`
  In **refresh** mode, deletes are still executed in chunks, but the expensive transfer suite is a single pass.

- `--oracle-in-strategy auto` (default)
  Uses `or_of_in_lists` only when `N <= --or-of-in-max-ids` (default **10,000**). If the corp list is larger than that threshold, it falls back to `chunk_files`.

#### Strategy matrix

| Strategy | When used | Transfer suite runs | Oracle predicate shape |
|---|---|---:|---|
| `chunk_files` | Forced, or chosen by `auto` for very large lists | `ceil(N / chunk_size)` | `corp_num IN (...)` (single list per chunk file) |
| `or_of_in_lists` | Forced, or chosen by `auto` for small/medium lists | `1` | `(corp_num IN (...)) OR (corp_num IN (...)) ...` (many groups) |
| `auto` | Default | `1` or `ceil(N / chunk_size)` | Depends on threshold |

#### Concrete examples

- **Auto strategy, 30,000 corp ids (the common misunderstanding)**
  With defaults `--oracle-in-strategy auto --or-of-in-max-ids 10000 --chunk-size 1000`:
  - Because `30,000 > 10,000`, `auto` selects **`chunk_files`**.
  - You will get **30 chunk passes** (and ~30 transfer-suite executions) — *not* 3.
  - To reduce passes under `auto`, raise the threshold: `--or-of-in-max-ids 50000`.

- **Forced OR-of-IN-lists, 30,000 corp ids**
  If you explicitly set `--oracle-in-strategy or_of_in_lists --chunk-size 1000`:
  - The transfer suite runs **once**.
  - The Oracle predicate contains **30 IN groups OR'd together**.
  - In refresh mode, deletes still run in 30 chunks.

- **Small list, defaults**
  For `N=2,500` with defaults (`auto`, `chunk-size 900`):
  - `N <= 10,000` so `auto` uses **`or_of_in_lists`**.
  - Transfer suite runs once with `ceil(2500/900)=3` OR'd IN groups.

### Performance tuning

- Increase `--threads` for DbSchemaCLI transfer if your workstation and DB can handle it.
- Consider enabling `--pg-fastload` (see above) for faster bulk writes.
- If you have very large corp lists and performance is poor, consider switching `--oracle-in-strategy`:
  - `or_of_in_lists` is typically best for small/medium lists (single transfer pass).
  - `chunk_files` may be necessary for very large lists (because `auto` will fall back once the list exceeds `--or-of-in-max-ids`).
