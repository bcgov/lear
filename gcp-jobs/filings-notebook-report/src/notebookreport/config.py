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

    # POSTGRESQL
    PG_USER = os.getenv("PG_USER", "")
    PG_PASSWORD = os.getenv("PG_PASSWORD", "")
    PG_NAME = os.getenv("PG_DB_NAME", "")
    PG_HOST = os.getenv("PG_HOST", "")
    PG_PORT = os.getenv("PG_PORT", "5432")
    SQLALCHEMY_DATABASE_URI = f"postgresql://{PG_USER}:{PG_PASSWORD}@{PG_HOST}:{int(PG_PORT)}/{PG_NAME}"


