import os
from dotenv import load_dotenv, find_dotenv

# this will load all the envars from a .env file located in the project root (api)
load_dotenv(find_dotenv())

class Config(object):
    PROJECT_ROOT = os.getcwd()
    SENDER_EMAIL = os.getenv('SENDER_EMAIL', '')
    ERROR_EMAIL_RECIPIENTS = os.getenv('ERROR_EMAIL_RECIPIENTS', '')
    SFTP_GAZETTE_RECIPIENTS = os.getenv('SFTP_GAZETTE_RECIPIENTS', '')
    EMAIL_SMTP = os.getenv('EMAIL_SMTP', '')
    ENVIRONMENT = os.getenv('ENVIRONMENT', '')
    SFTP_ARCHIVE_DIRECTORY = os.getenv('SFTP_ARCHIVE_DIRECTORY', '/opt/app-root/archive/')
    TEMPLATE_PATH = os.getenv('TEMPLATE_PATH', None)
   
    SFTP_HOST = os.getenv('SFTP_HOST', 'drive.kp.gov.bc.ca')
    SFTP_PORT = os.getenv('SFTP_PORT', 22)
    SFTP_VERIFY_HOST = os.getenv('SFTP_VERIFY_HOST')
    SFTP_HOST_KEY = os.getenv('SFTP_HOST_KEY', '')
    BCREG_FTP_PRIVATE_KEY = os.getenv('BCREG_FTP_PRIVATE_KEY', '')
    SFTP_USERNAME = os.getenv('SFTP_USERNAME', 'foo')
    BCREG_FTP_PRIVATE_KEY_PASSPHRASE = os.getenv('BCREG_FTP_PRIVATE_KEY_PASSPHRASE', '')

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