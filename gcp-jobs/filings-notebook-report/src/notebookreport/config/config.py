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

    # POSTGRESQL
    DB_USER = os.getenv("DATABASE_USERNAME", "")
    DB_PASSWORD = os.getenv("DATABASE_PASSWORD", "")
    DB_NAME = os.getenv("DATABASE_NAME", "")
    DB_HOST = os.getenv("DATABASE_HOST", "")
    DB_PORT = os.getenv("DATABASE_PORT", "5432")
    if DB_USER != "":
        if DB_UNIX_SOCKET := os.getenv("DATABASE_UNIX_SOCKET", None):
            SQLALCHEMY_DATABASE_URI = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@/{DB_NAME}?host={DB_UNIX_SOCKET}"
        else:
            SQLALCHEMY_DATABASE_URI = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    else:
        DATABASE_TEST_USERNAME = os.getenv("DATABASE_TEST_USERNAME")
        DATABASE_TEST_PASSWORD = os.getenv("DATABASE_TEST_PASSWORD")
        DATABASE_TEST_NAME = os.getenv("DATABASE_TEST_NAME")
        DATABASE_TEST_HOST = os.getenv("DATABASE_TEST_HOST")
        DATABASE_TEST_PORT = os.getenv("DATABASE_TEST_PORT")
        SQLALCHEMY_DATABASE_URI = f"postgresql://{DATABASE_TEST_USERNAME}:{DATABASE_TEST_PASSWORD}@{DATABASE_TEST_HOST}:{DATABASE_TEST_PORT}/{DATABASE_TEST_NAME}"
