
import csv
import os

import psycopg2
from dotenv import load_dotenv, find_dotenv


# sql_string = "INSERT INTO domes_hundred (name,name_slug,status) VALUES (%s,%s,%s) RETURNING id;"
# cursor.execute(sql_string, (hundred_name, hundred_slug, status))
# hundred = cursor.fetchone()[0]

# get db connection settings from environment variables
DB_USER = os.getenv('DATABASE_USERNAME', '')
DB_PASSWORD = os.getenv('DATABASE_PASSWORD', '')
DB_NAME = os.getenv('DATABASE_NAME', '')
DB_HOST = os.getenv('DATABASE_HOST', '')
DB_PORT = os.getenv('DATABASE_PORT', '5432')

conn = psycopg2.connect("host='{0}' dbname='{1}' user='{2}' password='{3}' port='{4}'".
                        format(DB_HOST, DB_NAME, DB_USER, DB_PASSWORD, DB_PORT))

conn.set_session(isolation_level='REPEATABLE READ',
                 readonly=False, deferrable=False, autocommit=False)
cursor = conn.cursor()

# remove with prejudice the existing data
print('truncating all data')
cursor.execute("TRUNCATE addresses")
cursor.execute("TRUNCATE filings")
cursor.execute("TRUNCATE businesses CASCADE")
print('done')

business_sql = 'INSERT INTO businesses (identifier,legal_name,last_ar_date,last_agm_date) VALUES (%s,%s,%s,%s) RETURNING id;'
address_sql = 'INSERT INTO addresses (business_id,address_type,street,street_additional,city,region,country,postal_code,delivery_instructions) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s);'
rowcount = 0

with open('coop_2019_test_data.csv', 'r') as csvfile:
    reader = csv.DictReader(csvfile)
    try:
        for row in reader:
            rowcount += 1
            print('loading: ', row['CORP_NUM'])

            cursor.execute(business_sql, (row['CORP_NUM'], row['CORP_NME'],
                                          row['LAST_AR_FILED_DT'], row['LAST_AGM_DATE']))
            business_id = cursor.fetchone()[0]

            cursor.execute(address_sql, (business_id, 'delivery',
                                         row['ADDR_LINE_1'], None,
                                         row['CITY'], row['PROVINCE'],
                                         'CA', row['POSTAL_CD'],
                                         row['ADDR_LINE_2']))

            cursor.execute(address_sql, (business_id, 'mailing',
                                         row['ADDR_LINE_1'], None,
                                         row['CITY'], row['PROVINCE'],
                                         'CA', row['POSTAL_CD'],
                                         row['ADDR_LINE_2']))

    except psycopg2.IntegrityError as e:
        print('error:', e)
        pg_conn.rollback()

# commit all changes
conn.commit()
cursor.close
print(f'processed: {rowcount} rows')
