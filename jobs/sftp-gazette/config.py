import os
from dotenv import load_dotenv, find_dotenv

# this will load all the envars from a .env file located in the project root (api)
load_dotenv(find_dotenv())

CONFIGURATION = {
    'development': 'config.DevConfig',
    'testing': 'config.TestConfig',
    'production': 'config.ProdConfig',
    'default': 'config.ProdConfig'
}


class Config(object):
    PROJECT_ROOT = os.getcwd()
    SENDER_EMAIL = os.getenv('SENDER_EMAIL', '')
    ERROR_EMAIL_RECIPIENTS = os.getenv('ERROR_EMAIL_RECIPIENTS', '')
    SFTP_GAZETTE_RECIPIENTS = os.getenv('SFTP_GAZETTE_RECIPIENTS', '')
    EMAIL_SMTP = os.getenv('EMAIL_SMTP', '')
    ENVIRONMENT = os.getenv('ENVIRONMENT', '')
    SFTP_ARCHIVE_DIRECTORY = os.getenv('SFTP_ARCHIVE_DIRECTORY', '/opt/app-root/archive/')
    TEMPLATE_PATH = os.getenv('TEMPLATE_PATH', None)
   
    # POSTGRESQL
    PG_USER = os.getenv('PG_USER', '')
    PG_PASSWORD = os.getenv('PG_PASSWORD', '')
    PG_NAME = os.getenv('PG_DB_NAME', '')
    PG_HOST = os.getenv('PG_HOST', '')
    PG_PORT = os.getenv('PG_PORT', '5432')
    SFTP_HOST = os.getenv('SFTP_HOST', 'drive.kp.gov.bc.ca')
    SFTP_PORT = os.getenv('SFTP_PORT', 22)
    SFTP_VERIFY_HOST = os.getenv('SFTP_VERIFY_HOST')
    SFTP_HOST_KEY = os.getenv('SFTP_HOST_KEY', '')
    SFTP_ARCHIVE_DIRECTORY = os.getenv('SFTP_ARCHIVE_DIRECTORY', '/opt/app-root/archieve/')
    BCREG_FTP_PRIVATE_KEY = os.getenv('BCREG_FTP_PRIVATE_KEY', '')
    SFTP_USERNAME = os.getenv('SFTP_USERNAME', 'foo')
    BCREG_FTP_PRIVATE_KEY_PASSPHRASE = os.getenv('BCREG_FTP_PRIVATE_KEY_PASSPHRASE', '')
    SQLALCHEMY_DATABASE_URI = 'postgresql://{user}:{password}@{host}:{port}/{name}'.format(
        user=PG_USER,
        password=PG_PASSWORD,
        host=PG_HOST,
        port=int(PG_PORT),
        name=PG_NAME,
    )
