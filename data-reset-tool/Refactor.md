
## Objective

The goal is to decouple the logic in the data reset tool from the models in legal API. This will result in a simpler, easier to maintain tool with no dependencies on the code in legal-api. We do not want to change the endpoints or the reset tool's API structure too much to reduce the amount of refactoring that has to be done in the nightwatch scripts.   

## Motivation

The models and the database structure in LEAR change frequently. If a change goes in without being reflected in the data reset tool, there could either be missed data or catastrophic failures. Decoupling the data reset tool from the models in legal-api would result in more reliability and predicatability within the data reset tool. By using postgres' built in bulk copy methods we should also see a performance improvement over the current design.   

## Design Proposal

The proposal is to gut the dependencies on the legal-api models from the current data-reset tool code and replace them with native postgres bulk import and export mechanisms (copy and copy_expert). Postgres has the ability to map columnar data in CSV format to tables. This would change the current code structure in the following ways:

* The JSONConverter class would either no longer be needed, or would be changed to not call methods of the entities. A more agnostic approach may be to use the GET methods in legal API to retrieve entity data.

* The folder structure where the test data is held (e2e/lear-data) would change to have a folder per corp num. Each folder would have a csv file per table (ie CP0000001/directors.csv) since bulk copy cannot work with multiple tables.

* The removal of the legal-api.models dependency

* It is unclear how an export would work, some options are:
  * Have an endpoint for each table, resulting in a url structure similar to that of legal-api (GET api/CP0000001/parties -> returns a binary stream of this corp's parties)
  * Return text/json representation of the corp requested
  * Zip all files to return the entire folder structure for the requested corp number
  * Suggestions?

The same problem exists on import. One option could be to maintain the current use of spreadsheet(excel) files, and retain the use of the xlwt library to parse those sheets to an array of csv formatted text before copying

PROS:
 * Doesn't require code changes in the data reset tool every time code in legal-api.models changes
 * Less data-manipulation/ object mapping (reduced complexity)
 * Make use of legal-api to do object serialization
 * Quicker and less error prone
 * Easy to implement

CONS:
 * Potentially more spreadsheets/ CSV files for QA to maintain
 * Possibly adding more endpoints to the data reset API
 * copy does not dynamically track foreign keys, so those will have to be manually added (i.e - an address CSV would need to have a column for the business_id in order to link the two)
 * If multiple endpoints are used for each entity, multiple calls to either GET or POST an entity would have to be made from the nightwatch scripts

### Alternatives Considered
* A hybrid design where a config file of some sort could be used to map foreign keys to columns/csv Headers before an import is done
* Jupyter notebooks, not clear how a nightwatch script would interact with this

### Performance Implications
* The expectation is that performance will improve based on the reduction of dependencies and the postgres copy working closer to the database. The data reset tool has always been a small utility so a performance gain may be difficult to gauge. The assumption is that concurrent requests will succeed as the psycopg2 copy is threadsafe. 

### Dependencies
* legal-api for retrieving businesses
* psycopg2 copy
* a database

### Engineering Impact
* Once this is built and deployed, the csv files will still periodically need to be changed when new columns/ tables are introduced.
