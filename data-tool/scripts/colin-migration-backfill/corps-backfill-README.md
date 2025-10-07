# COLIN BC Corps Data Migration Backfill Notes.
Refer to the colin extract load worksheet 
[here](https://docs.google.com/spreadsheets/d/1MrhqyxPkFH6WV-KL16DVEx9s4bS1zK2j/edit?gid=816814136#gid=816814136) for instructions on loading the colin extract tables into the target business database under the colin_extract schema. The latest extract should be loaded prior to migrating the COLIN BC corps filing history.

The migration process determines which BC corps to migrate by looking at 2 database tables: colin_extract.corp_processing and mig_corp_processing_history.
The colin_extract.corp_processing contains the set of COLIN BC corporations where the tombstone data has been loaded.
The mig_corp_processing_history table contains the set of COLIN BC corporations where the filing history (tombstone backfill) data has been loaded.

The migration process executes as database functions or procedures. Connect to the target environment business database using the api user credentials.

There are 3 ways to migrate a COLIN BC corp filing history as 3 different database functions or procedures. Each function has an environment parameter that must match one of the corp_processing table environment column values.


1. Migrate a single BC corp. Call the function colin_hist_backfill_corp and commit the change. This function could be added to the tombstone process as a final step when migrating a  COLIN BC corp.
    ```
    select colin_hist_backfill_corp('prod', 'BC0956039');
    commit;
    
    ```
1. Migrate a range of corp_processing table id values. Execute the procedure colin_hist_backfill_range. This procedure commits the changes every 200 corps and as a final step.
    ```
    call colin_hist_backfill_range('prod', 1226, 1230);
    ```
1. As all outsanding tomstone loade BC corps where the backfill data has not been loaded. Run the procedure colin_hist_backfill. This procedure commits the changes every 200 corps and as a final step.
    ```
    call colin_hist_backfill('prod');
    ```
Note: do not use colin_hist_backfill until all development is complete for all COLIN filing and event types.
Note: if for some reason during testing in a non-production environment a backfill needs to be undone/reset, the corp can be deleted and the tombstone and backfill loads rerun.

## Files
### ./colin_lear_create_functions.sql
Script to:
- Create the corp backfill tracking table mig_corp_processing_history.
- Create all corp backfill database functions and procedures. All start with "colin_hist_".
Included for reference. All target environments have the latest definitions. 

A summary of the database functions can be found  
[here](https://docs.google.com/spreadsheets/d/1MrhqyxPkFH6WV-KL16DVEx9s4bS1zK2j/edit?gid=961769119#gid=961769119).

### ./colin_lear_drop.sql
Script to:
- Drop all corp backfill database functions and procedures.
- Drop the corp backfill tracking table mig_corp_processing_history.

### ./colin_business_officers.sql
Definitions for various functions to update officers information for previously loaded tombstone corporations. Intended to only be run once as a patch script.

As the API user connect to the target database and run:
```
select colin_tombstone_officers_cleanup();
commit;
select colin_tombstone_officers();
commit;
```

- The function colin_tombstone_officers_cleanup removes all existing tombstone officer data that uses the offices_held table.
- The function colin_tombstone_officers loads active officers in the party_roles and related tables.
- Only corps where the tombstone data was successfully loaded (looking in the colin_extract.corp_processing table) are updated.
