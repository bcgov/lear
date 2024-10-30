"""Get tables with non-null foreign keys for a given COLIN filing event"""

import cx_Oracle

from config import Config
from models import EventTable


# Setup Oracle
dsn = f"{Config.ORACLE_HOST}:{Config.ORACLE_PORT}/{Config.ORACLE_DB_NAME}"
cx_Oracle.init_oracle_client(
    lib_dir=Config.ORACLE_INSTANT_CLIENT_DIR
)  # this line may not be required for some
connection = cx_Oracle.connect(
    user=Config.ORACLE_USER, password=Config.ORACLE_PASSWORD, dsn=dsn
)
cursor = connection.cursor()


# Check connection
cursor.execute(
    "SELECT filing_typ_cd, full_desc FROM filing_type WHERE filing_typ_cd=:filing_typ_cd",
    filing_typ_cd=Config.FILING_TYP_CD,
)
filing_typ_cd, full_desc = cursor.fetchone()


# Get filings with filing type code
cursor.execute(
    "SELECT event_id FROM filing WHERE filing_typ_cd=:filing_typ_cd FETCH FIRST :limit ROWS ONLY",
    filing_typ_cd=filing_typ_cd,
    limit=Config.MAX_FILINGS,
)
filing_event_ids = [event_id[0] for event_id in cursor.fetchall()]


# Get foreign keys for EVENT table
events = EventTable(filing_type_code=filing_typ_cd, event_ids=filing_event_ids)
events.build_mapping(cursor)

print(f"\n\nTable mapping for {filing_typ_cd}: {full_desc}", end="\n\n")
events.print()

# Close cursor
cursor.close()
