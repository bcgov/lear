import pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv
import os
from tqdm import tqdm


################################################################################################
############################### Configure them as you wish #####################################
################################################################################################
#### Configures for finding columns in tables directly related to, by EVENT_ID or their fks #####
TABLE_NAME = 'CORP_PARTY' # table name
SCHEMA_NAME = 'COLIN_MGR_TST' # this is tst, not really recommend to use dev, since the COLIN-dev is not fully functional 
EVENT_ID_COLUMN = 'START_EVENT_ID' # this is for the column used event_id as fk, can be found in previous steps using the provided sql code
FILING_TYPE = 'NOCDR'  # filing type code
ROW_LIMIT = 5000 # there are a lot of rows in some tables, pick your number
RANDOM_SAMPLING = True  # True -> random sampling || False -> all rows
################################################################################################
## Configures for finding columns in tables not directly related to, by EVENT_ID or their fks ##
NON_DIRECT_MODE = False # True -> check non-direct tables || False -> disable this feature, useful when initially trying to figure out columns in directly related tables
COLUMN_NAME_MAIN = 'MAILING_ADDR_ID'  # the column contains key that has been used in the connected table as fk
CONNECTED_TABLE_NAME = 'ADDRESS'
COLUMN_NAME_CONNECTED = 'ADDR_ID'
################################################################################################


def get_connection_string() -> str:
    """Creates connection string from environment variables."""
    load_dotenv()  # Load environment variables from .env file
    
    user = os.getenv('DB_USER')
    password = os.getenv('DB_PASS')
    host = os.getenv('DB_HOST')
    port = os.getenv('DB_PORT')
    service = os.getenv('DB_SERVICE')
    
    if not all([user, password, host, port, service]):
        raise ValueError("Missing required database configuration in .env file")
        
    return f"oracle://{user}:{password}@{host}:{port}/{service}"


def connect_to_db():
    """Create database connection"""
    print("Creating db connection")
    connection_string = get_connection_string()
    engine = create_engine(connection_string)
    print("db connected")
    print('-'*100)
    
    return engine


def read_with_progress_bar(query:str, engine, row_count:int, chunk_size:int = 5000, description:str = "Analyzing data") -> pd.DataFrame:
    """Read SQL query with a progress bar"""
    #init a progress bar
    progress_bar = tqdm(total=row_count, desc=description, unit="rows")

    # read data in chunks
    chunks = []
    for chunk in pd.read_sql(query, engine, chunksize=chunk_size):
        chunks.append(chunk)
        progress_bar.update(len(chunk))
    progress_bar.close()

    # combine all chunks
    return pd.concat(chunks, ignore_index=True)


def analyze_table_nulls(engine) -> tuple:
    """Analyzes non-NULL values in all columns of a specified Oracle table."""
    try:
        table_name = TABLE_NAME
        schema_name = SCHEMA_NAME
        event_id_column = EVENT_ID_COLUMN
        filing_type = FILING_TYPE
        row_limit = ROW_LIMIT
        random_sampling = RANDOM_SAMPLING
        
        if not schema_name or not table_name:
            raise ValueError("Missing schema configuration or/and table name")

        if random_sampling:
            # Build the filtered query with random sampling
            filtered_query = f"""
                WITH filtered_rows AS (
                    SELECT t.*
                    FROM {schema_name}.{table_name} t
                    WHERE t.{event_id_column} IN (
                        SELECT e.EVENT_ID 
                        FROM EVENT e 
                        JOIN FILING f ON e.EVENT_ID = f.EVENT_ID 
                        WHERE f.FILING_TYP_CD = '{filing_type}'
                    )
                )
                SELECT * FROM (
                    SELECT * FROM filtered_rows
                    ORDER BY DBMS_RANDOM.VALUE
                ) WHERE ROWNUM <= {row_limit}
            """
        else:
            # full range
            filtered_query = f"""
                WITH filtered_rows AS (
                    SELECT t.*
                    FROM {schema_name}.{table_name} t
                    WHERE t.{event_id_column} IN (
                        SELECT e.EVENT_ID 
                        FROM EVENT e 
                        JOIN FILING f ON e.EVENT_ID = f.EVENT_ID 
                        WHERE f.FILING_TYP_CD = '{filing_type}'
                    )
                )
                SELECT * FROM filtered_rows
            """
        
        # Get total count of filtered rows
        count_query = f"""
            SELECT COUNT(*) as count
            FROM {schema_name}.{table_name} t
            WHERE t.{event_id_column} IN (
                SELECT e.EVENT_ID 
                FROM EVENT e 
                JOIN FILING f ON e.EVENT_ID = f.EVENT_ID 
                WHERE f.FILING_TYP_CD = '{filing_type}'
            )
        """
        
        # Get counts and data
        print(f"\nFetching entries in {table_name} related to filing type: {filing_type}......")
        total_filtered_rows = pd.read_sql(count_query, engine).iloc[0]['count']
        progress_total = total_filtered_rows
        if RANDOM_SAMPLING:
            progress_total = ROW_LIMIT
        df = read_with_progress_bar(filtered_query, engine, progress_total, progress_total//100, f"Analyzing entries in {table_name}, related to {filing_type}: ")
        
        rows_count = len(df)
        print(f"Total rows matching filter: {total_filtered_rows:,}")

        if random_sampling:
            # Get sample size
            print(f"Random sample size: {rows_count:,} rows ({(rows_count/total_filtered_rows)*100:.2f}% of filtered data)")
        else:
            print(f"Full Range Mode, taking all {rows_count} rows")

        print('-'*100)
        
        # Calculate non-NULL counts and percentages for each column
        results = []
        for column in df.columns:
            non_null_count = df[column].count()
            non_null_percentage = (non_null_count / rows_count) * 100
            
            results.append({
                'Column Name': column.upper(),
                'Non-NULL Count': non_null_count,
                'Non-NULL Percentage': f"{non_null_percentage:.2f}%",
            })
        
        # Convert results to DataFrame
        results_df = pd.DataFrame(results)
        if NON_DIRECT_MODE:
            print("Stage 1 analyzing complete")
            print('-'*100)
        return results_df, df
        
    except Exception as e:
        print(f"Error: {e}")
        raise


def analyze_non_direct_table_nulls(df: pd.DataFrame, engine) -> pd.DataFrame:
    """ Query Oracle database using values from a pandas DataFrame column."""
    print("Stage 2 started.")
    print(f"Analyzing rows in connected table:\nTable - {TABLE_NAME} ------> Table - {CONNECTED_TABLE_NAME},\
          \nThrough {TABLE_NAME} [{COLUMN_NAME_MAIN}] -----> {CONNECTED_TABLE_NAME} [{COLUMN_NAME_CONNECTED}] \n")
    # Extract unique values from the Main table, and split to chunks, if needed
    col_values_list = df[COLUMN_NAME_MAIN.lower()].unique().tolist()
    value_chunks = [col_values_list[i:i + 1000] for i in range(0, len(col_values_list), 1000)] # split a big pd list to small lists no longer than 1000 (Oracle expression limit)
    total_chunks = len(value_chunks)
    
    all_results = pd.DataFrame()
    total_rows = 0

    try: 
        for i, chunk in enumerate(value_chunks, 1):
            # Initialize progress bar on first chunk
            if i == 1:
                progress_bar = tqdm(total=total_chunks, 
                        desc="Analyzing data: ")

            formatted_values = [f"'{val}'" if isinstance(val, str) else str(val) 
                            for val in chunk]
            values_string = ','.join(formatted_values)

            # create Oracle query
            query = f"""
                SELECT *
                FROM {CONNECTED_TABLE_NAME}
                WHERE {COLUMN_NAME_CONNECTED} IN ({values_string})
            """
        
            try:
                # Execute query for this chunk
                chunk_df = pd.read_sql_query(query, engine)
                all_results = pd.concat([all_results, chunk_df], ignore_index=True)

                # Update progress bar description with current stats
                total_rows += len(chunk_df)
                progress_bar.update(1)
                progress_bar.set_postfix({
                    'Chunk Size': len(chunk_df)
                })
            except Exception as e1:
                print(f"Error processing chunk {i}: {e1}")
                raise

        rows_count = len(all_results)

        # Calculate non-NULL counts and percentages for each column
        results = []
        for column in all_results.columns:
            non_null_count = all_results[column].count()
            non_null_percentage = (non_null_count / rows_count) * 100
            
            results.append({
                'Column Name': column.upper(),
                'Non-NULL Count': non_null_count,
                'Non-NULL Percentage': f"{non_null_percentage:.2f}%",
            })
        # Convert results to DataFrame
        results_df = pd.DataFrame(results)
        return results_df
    except Exception as e:
        print(f"Error in stage 2: {e}")
        raise 



if __name__ == "__main__":
    try:  
        # Connect to db
        engine = connect_to_db()

        # Configure pandas display options
        pd.set_option('display.max_rows', None)
        pd.set_option('display.max_columns', None)
        pd.set_option('display.width', None)
        pd.set_option('display.float_format', lambda x: '%.2f' % x)
        
        # Run analysis
        direct_results, df = analyze_table_nulls(engine)
        results = direct_results
        
        if NON_DIRECT_MODE:
            non_direct_results = analyze_non_direct_table_nulls(df, engine)
            results = non_direct_results
        
        print("\nAnalysis Results:")
        print(results)
        
    except Exception as e:
        print(f"Failed to complete analysis: {str(e)}")
