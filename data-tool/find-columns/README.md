# Data Analysis - Find Columns Tool

## About the NULL-Columns_Finder tool
- This is a tool helps you find out non-null columns in tables related to a particular filing type
- Will need to find out the related tables first, consider using the tool created by Leo or the scripts stored in the `sql_scripts` folder to help you on that.

## How to use the NULL Columns finder tool
- open the `find-columns` folder in an IDE to treat it as a project (or WSL project). To prevent version clashes, set up a virtual environment to install the Python packages used by this project.
- make a copy of `.evn.example` and add your secrets to your `.env`
- `make setup` for install all dependencies
- configure parameters in `find_null_columns.py` as needed
- `make run` for running the tool

### To re-install
- Run `make clean` first
- Then run `make setup` to install all dependencies

## Update Notes
- Support limited number of random-sampling or full range mode to check all rows. You can enable it by tweaking the `random_sampling` config in `find_null_columns.py`
- A feature to help finding out non-null columns from tables not directly connected to EVENT_ID related tables. You can enable it by tweaking the `NON_DIRECT_MODE` config. (Need to figure out these table names and connected column names in DbSchema first)
    - e.g. CORP_PARTY table is related to x filing, and ADDRESS table connected to CORP_PARTY table by ADDR_ID
