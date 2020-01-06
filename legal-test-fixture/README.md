
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)


# Application Name

Test Fixture API

## Purpose
In order to run test scenarios repeatedly, a known database state is required at the start of each test. This is surprisingly hard to set up in the current architecture. There are a limited number of businesses set up in the auth service and the pay service, so once they are affected by testing they are no longer usable for specific test scenarios. Many user activities are "one-way" in the sense that they can not be undone using the GUI for the application.

All the current data loading is currently scripted by Python and requires an Oracle COLIN database instance as a source. This is not great for local development as nobody really runs Oracle locally (because it is a beast). QA team members are not necessarily equipped to run Python and would also need to manually reset the Oracle database before running a reload. The database loads are configured as all or nothing, which means single records can't be reset.

Additionally, it is not at all simple for QA to inspect the current state of the data for a business, or to write a test that can set the precondition state of a business and know exactly the values it should be expecting. 

This API serves the need for a simple tool that allows for bulk import/export of individual records or entire data sets for the PostgreSQL database. The specific use case that this API was designed to enable is to "snapshot" to file a known state for a business (maybe right after it was reset from COLIN) and then be able to "reset" that business back to that state whenever necessary. Because it is an API, a NightWatch test can be configured to execute the "reset" before (or after) each execution of a test. We can collect or create as many states as we like and check them into the repo in order to maintain a collection of data states for testing purposes.

## Entities affected
* Businesses
* Business addresses
* Directors
* Director addresses
* Filings

## Limitations
* Not intended to work with huge datasets
* Does not maintain the state of the historical versioning of records (flask-continuum)
* Does not in any way interact with the auth database or the payments database
* Piggybacks off the current model. If there are bugs in the model, it will show up here. For example, the model currently validates for business identifiers that start with "CP" or "XCP", so a "BC" (benefit corporation) cannot be imported.


## Technology Stack Used
* Python, Flask, xlrd, xlwt
* Postgres -  SQLAlchemy 

## Files in this repository

```
legal-api/							- source dicrectory
└── api/  
    └── blueprints/ 
            fixture.py				- contains the routes and main logic      
    └── converter/           
            ExcelConverter.py		- converts an incoming spreadsheet into database records
            ExcelWriter.py			- converts a list of businesses from sqlalchemy into a spreadsheet
            JsonWriter.py			- converts a list of businesses from sqlalchemy into a json document
            utils.py				- shared code (formatting methods)     
test/                      
└── spreadsheets/  
    └── businesses.xls				- sample import file     
__init.py__							- initialization script
config.py							- config script
```

## Deployment (Local Development)
This service is intended to be built by the `make` command and run as a Docker container. 

There is a cheat sheet for the manual steps that are still required to download the code from GitHub and build the solution: [https://docs.google.com/document/d/1tj4UgPoi698vS7F6HA-vxNXuveEODyUzImTBmXsARlo]() Hopefully these manual steps can be refactored and/or scripted away over time.

Specifically, the command `make local-project` triggers a copy of models, exceptions, and schemas.py from the lear-api service folder to the source folder of the test fixture API. This way, the model is re-used and kept up to date automagically. ;-)

## Deployment (Connect from local environment to OpenShift)
If you have access to a database in OpenShift, you can connect your local instance of the test fixture API to that database. **BE CAREFUL**

The way to do this is to edit the file docker-compose.yml locally to inject a different value for `DATABASE_URL` environment variable to point to the database you want to import to and export from. In the example below, the local environment has port forwarded local host 65432 to the openshift pod and port that is running PostgreSQL.

Example: `- DATABASE_URL=postgres://user5SJ:password@host.docker.internal:65432/lear`

In this usage scenario, there is no guarantee that the model you are using locally matches the model of the remote database, so you must confirm this yourself. YMMV

## Deployment (Deploy to OpenShift)
It's just a Docker container. By setting the single environment variable, it can be deployed in a Pod and configured to interact with a PostgreSQL database instance. Obviously this should never be done in production. *Deferred to Jenkins (or GitHub Actions) pipeline as per the preferences of the team.*

## Usage
The following examples assume that the make file has been used to deploy to a local Docker network and that the Test Fixture API has been mapped to port 5005. This is the default configuration. The domain and port would change if we were connecting to a running instance somewhere else (like OpenShift).

See businesses.xls in this repository for an example of a file that can be used for import (or just get yourself a new file by doing an export). 

### Export
Export requires a GET request and returns either JSON or a file that is a spreadsheet in the same format used by the import function. This can be called in a browser, from a script, or from PostMan. (Hint: in PostMan you can click the little down arrow next to the big blue "Send" button and select the option "Send and Download"). Export does not affect the records in the database in any way.

* `http://localhost:5005/api/fixture/export/CP0000393` - Exports the business record from the database in the default format (JSON). 
* `http://localhost:5005/api/fixture/export/CP0000393/excel` - Exports the business record from the database in the excel format (downloads a file)
* `http://localhost:5005/api/fixture/export/all_YES_IM_SURE` - Exports the all the business records from the database in the default format (JSON). **Will probably blow up for a large data set.**
* `http://localhost:5005/api/fixture/export/all_YES_IM_SURE/excel` - Exports the all the business records from the database in the excel format (downloads a file). **Will probably blow up for a large data set.**


### Import
Import requires a POST request with a spreadsheet attached with the key "file". This is easily accomplished using PostMan. There are a few options that can be used to change the behaviour.

* `http://localhost:5005/api/fixture/import` - Imports all the business records from the spreadsheet. For each business identifier, the API deletes the business from the database (and all child records) and rebuilds it from the data in the spreadsheet.
* `http://localhost:5005/api/fixture/import/CP0000393` - Imports only the business record from the spreadsheet with the business ID "CP0000393". The API deletes this single business from the database (and all child records) and rebuilds it from the data in the spreadsheet. This is probably the most useful command for NightWatch scripts as they can save a state and reload it before each run of the test to ensure a known state.
* `http://localhost:5005/api/fixture/import?rebuild=true` - **First DROPS all the records from the database and rebuilds the database according to the SqlAlchemy model.** Imports all the business records from the spreadsheet. 
* `http://localhost:5005/api/fixture/import?rebuild=true` - **First DROPS all the records from the database and rebuilds the database according to the SqlAlchemy model.** Imports a single business record from the spreadsheet. There will only be one business in the database after this operation.