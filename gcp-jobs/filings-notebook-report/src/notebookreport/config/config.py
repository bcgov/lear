import os

from dotenv import find_dotenv, load_dotenv

# this will load all the envars from a .env file located in the project root (api)
load_dotenv(find_dotenv())


class Config:
    PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
    APP_FILE = os.getenv("APP_FILE", "")
    SENDER_EMAIL = os.getenv("SENDER_EMAIL", "")
    ERROR_EMAIL_RECIPIENTS = os.getenv("ERROR_EMAIL_RECIPIENTS", "")
    REPORT_RECIPIENTS = os.getenv("REPORT_RECIPIENTS", "")
    EMAIL_SMTP = os.getenv("EMAIL_SMTP", "")
    ENVIRONMENT = os.getenv("ENVIRONMENT", "")
    MONTH_REPORT_DATES = os.getenv("MONTH_REPORT_DATES", "")

    ACCOUNT_SVC_AUTH_URL = os.getenv("ACCOUNT_SVC_AUTH_URL")
    ACCOUNT_SVC_CLIENT_ID = os.getenv("ACCOUNT_SVC_CLIENT_ID")
    ACCOUNT_SVC_CLIENT_SECRET = os.getenv("ACCOUNT_SVC_CLIENT_SECRET")

    # Cloud SQL Connector / Postgres
    CLOUDSQL_INSTANCE_CONNECTION_NAME = os.getenv("CLOUDSQL_INSTANCE_CONNECTION_NAME")
    DATABASE_NAME = os.getenv("DATABASE_NAME") or os.getenv("PG_DB_NAME")
    DATABASE_USERNAME = os.getenv("DATABASE_USERNAME") or os.getenv("PG_USER") or os.getenv("JOB_DATABASE_USERNAME")
    DATABASE_PASSWORD = os.getenv("DATABASE_PASSWORD", "")
    DATABASE_HOST = os.getenv("DATABASE_HOST", "")
    DATABASE_PORT = os.getenv("DATABASE_PORT", "5432")
    IP_TYPE = os.getenv("IP_TYPE", "private")

    if CLOUDSQL_INSTANCE_CONNECTION_NAME and DATABASE_NAME and DATABASE_USERNAME:
        SQLALCHEMY_DATABASE_URI = "postgresql+pg8000://"
    else:
        DATABASE_TEST_USERNAME = os.getenv("DATABASE_TEST_USERNAME")
        DATABASE_TEST_PASSWORD = os.getenv("DATABASE_TEST_PASSWORD")
        DATABASE_TEST_NAME = os.getenv("DATABASE_TEST_NAME")
        DATABASE_TEST_HOST = os.getenv("DATABASE_TEST_HOST")
        DATABASE_TEST_PORT = os.getenv("DATABASE_TEST_PORT")
        SQLALCHEMY_DATABASE_URI = f"postgresql://{DATABASE_TEST_USERNAME}:{DATABASE_TEST_PASSWORD}@{DATABASE_TEST_HOST}:{DATABASE_TEST_PORT}/{DATABASE_TEST_NAME}"


# Helper for SQLAlchemy engine with cloud-sql-connector
def get_sqlalchemy_engine():
    """
    Returns a SQLAlchemy engine using cloud-sql-connector if configured, else standard connection string.
    """
    from sqlalchemy import create_engine
    if Config.CLOUDSQL_INSTANCE_CONNECTION_NAME and Config.DATABASE_NAME and Config.DATABASE_USERNAME:
        from cloud_sql_connector import DBConfig, getconn
        config = DBConfig(
            instance_name=Config.CLOUDSQL_INSTANCE_CONNECTION_NAME,
            database=Config.DATABASE_NAME,
            user=Config.DATABASE_USERNAME,
            ip_type=Config.IP_TYPE,
            schema="public"
        )
        return create_engine(
            Config.SQLALCHEMY_DATABASE_URI,
            creator=lambda: getconn(config)
        )
    else:
        return create_engine(Config.SQLALCHEMY_DATABASE_URI)
