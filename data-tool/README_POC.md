
# Prefect ETL POC

## Summary
This folder(data-tool) was created to test using Prefect as a potential tool for ETL pipelines as well as for data 
analytics workflows.  A POC ETL pipeline was created in `./flows/test_flow.py` which contains a very small example 
of transforming data from small subset of pre-processed COLIN tables and loading the transformed data into LEAR db.

Besides serving as a lightweight example of how to perform ETL specific activities in Prefect, the test flow also tests
failure, retry, logging, flow visualization, manual flow runs, backfilling, dynamic tasks, parent/child relationships 
and ease of tracking down data processing issues.

## Local Setup instructions

1. Create .env with appropriate db values for colin migration db and lear db
2. `make install`
3. Run `prefect backend server` to ensure BE is running on server mode as opposed to cloud mode
4. Start up prefect server.  `docker-compose up -d`
5. `prefect server create-tenant —-name default --slug default`
6. `prefect create project "test"`
7. `prefect register --project "test" --path /<folder-placeholder-name>/bcreg/lear/data-tool/flows/test_flow.py --force`  Note: force is needed to bump version num
8. Start a local agent.  The local agent communicates with prefect server and the UI. 
` prefect agent local start --name "Default Agent" -p /<folder-placeholder-name>/bcreg/lear/data-tool/flows --show-flow-logs`
9. Open prefect ui in browser to monitor and trigger flow runs - http://localhost:8080 
