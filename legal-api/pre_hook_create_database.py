import contextlib
import os
import sys

import sqlalchemy
import sqlalchemy.exc

from legal_api.config import ProdConfig

DB_ADMIN_PASSWORD = os.getenv("DB_ADMIN_PASSWORD", None)
DB_ADMIN_USERNAME = os.getenv("DB_ADMIN_USERNAME", "postgres")

if not hasattr(ProdConfig, "DB_NAME") or not DB_ADMIN_PASSWORD:
    print("Unable to create database.", sys.stdout)  # noqa: T201
    sys.exit(-1)

DATABASE_URI = f"postgresql://{DB_ADMIN_USERNAME}:{DB_ADMIN_PASSWORD}@{ProdConfig.DB_HOST}:{int(ProdConfig.DB_PORT)}/{DB_ADMIN_USERNAME}"

with contextlib.suppress(sqlalchemy.exc.ProgrammingError), sqlalchemy.create_engine(
    DATABASE_URI,
    isolation_level="AUTOCOMMIT"
).connect() as connection:
    database = ProdConfig.DB_NAME
    connection.execute(f"CREATE DATABASE {database}")
