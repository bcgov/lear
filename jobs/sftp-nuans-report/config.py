import os

from dotenv import find_dotenv, load_dotenv

# this will load all the envars from a .env file located in the project root (api)
load_dotenv(find_dotenv())

class Config(object):
    PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
    APP_FILE = os.getenv('APP_FILE', '')
    SENDER_EMAIL = os.getenv('SENDER_EMAIL', '')
    ERROR_EMAIL_RECIPIENTS = os.getenv('ERROR_EMAIL_RECIPIENTS', '')    
    EMAIL_SMTP = os.getenv('EMAIL_SMTP', '')
    ENVIRONMENT = os.getenv('ENVIRONMENT', '')
    MONTH_REPORT_DATES = os.getenv('MONTH_REPORT_DATES', '')