import contextlib
import os
import sys

import sqlalchemy
import sqlalchemy.exc

from legal_api.config import ProdConfig

DB_ADMIN_PASSWORD = os.getenv("DB_ADMIN_PASSWORD", None)
DB_ADMIN_USERNAME = os.getenv("DB_ADMIN_USERNAME", "postgres")

if not hasattr(ProdConfig, "DB_NAME") or not DB_ADMIN_PASSWORD:
    print("Unable to create database.", sys.stdout)
    sys.exit(-1)

DATABASE_URI = "postgresql://{name}:{password}@{host}:{port}/{name}".format(
    password=DB_ADMIN_PASSWORD,
    host=ProdConfig.DB_HOST,
    port=int(ProdConfig.DB_PORT),
    name=DB_ADMIN_USERNAME,
)

with contextlib.suppress(sqlalchemy.exc.ProgrammingError):
    with sqlalchemy.create_engine(DATABASE_URI, isolation_level="AUTOCOMMIT").connect() as connection:
        database = ProdConfig.DB_NAME
        connection.execute(f"CREATE DATABASE {database}")
