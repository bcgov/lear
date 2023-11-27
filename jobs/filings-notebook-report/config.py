import os
from dotenv import load_dotenv, find_dotenv

# this will load all the envars from a .env file located in the project root (api)
load_dotenv(find_dotenv())


class Config(object):
    PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
    SENDER_EMAIL = os.getenv('SENDER_EMAIL', '')
    ERROR_EMAIL_RECIPIENTS = os.getenv('ERROR_EMAIL_RECIPIENTS', '')
    INCORPORATION_FILINGS_DAILY_REPORT_RECIPIENTS = os.getenv(
        'INCORPORATION_FILINGS_DAILY_REPORT_RECIPIENTS', '')
    COOP_FILINGS_MONTHLY_REPORT_RECIPIENTS = os.getenv(
        'COOP_FILINGS_MONTHLY_REPORT_RECIPIENTS', '')
    COOPERATIVE_MONTHLY_REPORT_RECIPIENTS = os.getenv(
        'COOPERATIVE_MONTHLY_REPORT_RECIPIENTS', '')
    BC_STATS_MONTHLY_REPORT_RECIPIENTS = os.getenv(
        'BC_STATS_MONTHLY_REPORT_RECIPIENTS', '')
    EMAIL_SMTP = os.getenv('EMAIL_SMTP', '')
    ENVIRONMENT = os.getenv('ENVIRONMENT', '')
    MONTH_REPORT_DATES = os.getenv('MONTH_REPORT_DATES', '')

    # POSTGRESQL
    DATABASE_USERNAME = os.getenv('DATABASE_USERNAME', '')
    DATABASE_PASSWORD = os.getenv('DATABASE_PASSWORD', '')
    DATABASE_NAME = os.getenv('DATABASE_NAME', '')
    DATABASE_HOST = os.getenv('DATABASE_HOST', '')
    DATABASE_PORT = os.getenv('DATABASE_PORT', '5432')

    if DB_UNIX_SOCKET := os.getenv("DATABASE_UNIX_SOCKET", None):
        SQLALCHEMY_DATABASE_URI = f"postgresql+pg8000://{DATABASE_USERNAME}:{DATABASE_PASSWORD}@/{DATABASE_NAME}?unix_sock={DB_UNIX_SOCKET}/.s.PGSQL.5432"
    else:
        SQLALCHEMY_DATABASE_URI = f"postgresql+pg8000://{DATABASE_USERNAME}:{DATABASE_PASSWORD}@{DATABASE_HOST}:{DATABASE_PORT}/{DATABASE_NAME}"
