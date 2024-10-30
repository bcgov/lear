

# Corps Migration Flow

The corps migration prefect flow(`/lear/data-tool/flows/migrate_corps_flow.py`) is used to COLIN corporation data to the 
LEAR database.

The source database of the corps migration pipeline is a subset of the COLIN(Oracle database) tables required to
represent corporation data and is contained within a postgres database.

## Steps to run migration flow locally

Assumptions:
- source database is in place
- target database is in place

1. Setup prefect server database.  Use existing postgres db instance if that makes more sense.
```bash
docker rm -f prefect-postgres && \
sudo rm -rf /Users/argus/data/prefect-postgresql && \
sudo mkdir -p /Users/argus/data/prefect-postgresql && \
sudo chown -R argus /Users/argus/data/prefect-postgresql && \
docker run -d --name prefect-postgres -v /Users/argus/data/prefect-postgresql/data:/var/lib/postgresql/data -p 5130:5432 -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=prefect postgres:latest
```
2. Setup prefect profile
```bash
prefect profile use default && \
yes | prefect profile delete local-prefect-server && \
prefect profile create local-prefect-server && \
prefect -p 'local-prefect-server' config set PREFECT_API_URL="http://127.0.0.1:4200/api" && \
prefect -p 'local-prefect-server' config set PREFECT_API_DATABASE_CONNECTION_URL="postgresql+asyncpg://postgres:postgres@localhost:5130/prefect" && \    
prefect profile use local-prefect-server
```
3. cd to `/lear/data-tool`
4. Update .env file to properly use source and target databases.  Reference 
`/data-tool/.corps.env.sample` for an example .env file.  
```
# Source database config
DATABASE_USERNAME_COLIN_MIGR=
DATABASE_PASSWORD_COLIN_MIGR=
DATABASE_NAME_COLIN_MIGR=
DATABASE_HOST_COLIN_MIGR=
DATABASE_PORT_COLIN_MIGR=

# Target database config
DATABASE_USERNAME=
DATABASE_PASSWORD=
DATABASE_NAME=
DATABASE_HOST=
DATABASE_PORT=
```
5. Install prefect server and migration flow related dependencies.
```bash
make install-all
```
6. `make run-prefect-server`
7. Verify prefect dashboard works via http://127.0.0.1:4200
8. Open new console window and cd to `/lear/data-tool`
9. `make run-corps-migration`
10. Verify corps migration flow ran to completion
  - Verify flow run via prefect ui
  - Verify corp was migrated as expected by checking target database
  - Verify migrated corps were properly tracked in `corp_processing` table of source database 

