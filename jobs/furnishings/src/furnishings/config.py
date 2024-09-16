# Copyright © 2021 Province of British Columbia
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""All of the configuration for the service is captured here."""

import os
import sys

from dotenv import find_dotenv, load_dotenv


load_dotenv(find_dotenv())

CONFIGURATION = {
    'development': 'config.DevConfig',
    'testing': 'config.TestConfig',
    'production': 'config.ProdConfig',
    'default': 'config.ProdConfig'
}


def get_named_config(config_name: str = 'production'):
    """Return the configuration object based on the name."""
    if config_name in ['production', 'staging', 'default']:
        config = ProdConfig()
    elif config_name == 'testing':
        config = TestConfig()
    elif config_name == 'development':
        config = DevConfig()
    else:
        raise KeyError(f"Unknown configuration '{config_name}'")
    return config


class _Config:  # pylint: disable=too-few-public-methods
    """Base class configuration."""

    PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))

    SENTRY_DSN = os.getenv('SENTRY_DSN') or ''
    SENTRY_DSN = '' if SENTRY_DSN.lower() == 'null' else SENTRY_DSN
    LD_SDK_KEY = os.getenv('LD_SDK_KEY', None)

    AUTH_URL = os.getenv('AUTH_URL', None)
    ACCOUNT_SVC_AUTH_URL = os.getenv('ACCOUNT_SVC_AUTH_URL', None)
    ACCOUNT_SVC_CLIENT_ID = os.getenv('ACCOUNT_SVC_CLIENT_ID', None)
    ACCOUNT_SVC_CLIENT_SECRET = os.getenv('ACCOUNT_SVC_CLIENT_SECRET', None)

    NATS_SERVERS = os.getenv('NATS_SERVERS', None)
    NATS_CLUSTER_ID = os.getenv('NATS_CLUSTER_ID', None)
    NATS_CLIENT_NAME = os.getenv('NATS_CLIENT_NAME', None)
    NATS_ENTITY_EVENTS_SUBJECT = os.getenv('NATS_ENTITY_EVENTS_SUBJECT', 'entity.events')
    NATS_EMAILER_SUBJECT = os.getenv('NATS_EMAILER_SUBJECT', 'entity.email')

    SECRET_KEY = 'a secret'

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    ALEMBIC_INI = 'migrations/alembic.ini'

    # POSTGRESQL
    DB_USER = os.getenv('DATABASE_USERNAME', '')
    DB_PASSWORD = os.getenv('DATABASE_PASSWORD', '')
    DB_NAME = os.getenv('DATABASE_NAME', '')
    DB_HOST = os.getenv('DATABASE_HOST', '')
    DB_PORT = os.getenv('DATABASE_PORT', '5432')
    SQLALCHEMY_DATABASE_URI = 'postgresql://{user}:{password}@{host}:{port}/{name}'.format(
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=int(DB_PORT),
        name=DB_NAME,
    )

    # BCLaws SFTP
    BCLAWS_SFTP_STORAGE_DIRECTORY = os.getenv('BCLAWS_SFTP_STORAGE_DIRECTORY', None)
    BCLAWS_SFTP_HOST = os.getenv('BCLAWS_SFTP_HOST', None)
    BCLAWS_SFTP_PORT = os.getenv('BCLAWS_SFTP_PORT', None)
    BCLAWS_SFTP_USERNAME = os.getenv('BCLAWS_SFTP_USERNAME', None)
    BCLAWS_SFTP_PRIVATE_KEY_ALGORITHM = os.getenv('BCLAWS_SFTP_PRIVATE_KEY_ALGORITHM', 'ED25519')
    BCLAWS_SFTP_PRIVATE_KEY_PASSPHRASE = os.getenv('BCLAWS_SFTP_PRIVATE_KEY_PASSPHRASE', None)
    BCLAWS_SFTP_PRIVATE_KEY = os.getenv('BCLAWS_SFTP_PRIVATE_KEY', None)

    # BCMail+ SFTP
    BCMAIL_SFTP_STORAGE_DIRECTORY = os.getenv('BCMAIL_SFTP_STORAGE_DIRECTORY', None)
    BCMAIL_SFTP_HOST = os.getenv('BCMAIL_SFTP_HOST', None)
    BCMAIL_SFTP_PORT = os.getenv('BCMAIL_SFTP_PORT', None)
    BCMAIL_SFTP_USERNAME = os.getenv('BCMAIL_SFTP_USERNAME', None)
    BCMAIL_SFTP_PRIVATE_KEY_ALGORITHM = os.getenv('BCMAIL_SFTP_PRIVATE_KEY_ALGORITHM', 'ED25519')
    BCMAIL_SFTP_PRIVATE_KEY_PASSPHRASE = os.getenv('BCMAIL_SFTP_PRIVATE_KEY_PASSPHRASE', None)
    BCMAIL_SFTP_PRIVATE_KEY = os.getenv('BCMAIL_SFTP_PRIVATE_KEY', None)

    TESTING = False
    DEBUG = False

    SECOND_NOTICE_DELAY = int(os.getenv('SECOND_NOTICE_DELAY', '5'))
    LEGISLATIVE_TIMEZONE = os.getenv('LEGISLATIVE_TIMEZONE', 'America/Vancouver')
    XML_TEMPLATE_PATH = os.getenv('XML_TEMPLATE_PATH', 'furnishings-templates')

    # Letter - GCP Gotenberg report service
    REPORT_API_GOTENBERG_AUDIENCE = os.getenv('REPORT_API_GOTENBERG_AUDIENCE', '')
    REPORT_API_GOTENBERG_URL = os.getenv('REPORT_API_GOTENBERG_URL', 'https://')
    REPORT_TEMPLATE_PATH = os.getenv('REPORT_PATH', 'report-templates')
    # Letter - MRAS
    MRAS_SVC_URL = os.getenv('MRAS_SVC_URL')
    MRAS_SVC_API_KEY = os.getenv('MRAS_SVC_API_KEY')


class DevConfig(_Config):  # pylint: disable=too-few-public-methods
    """Development environment configuration."""

    TESTING = False
    DEBUG = True


class TestConfig(_Config):  # pylint: disable=too-few-public-methods
    """In support of testing only used by the py.test suite."""

    DEBUG = True
    TESTING = True

    # POSTGRESQL
    DB_USER = os.getenv('DATABASE_TEST_USERNAME', '')
    DB_PASSWORD = os.getenv('DATABASE_TEST_PASSWORD', '')
    DB_NAME = os.getenv('DATABASE_TEST_NAME', '')
    DB_HOST = os.getenv('DATABASE_TEST_HOST', '')
    DB_PORT = os.getenv('DATABASE_TEST_PORT', '5432')
    SQLALCHEMY_DATABASE_URI = 'postgresql://{user}:{password}@{host}:{port}/{name}'.format(
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=int(DB_PORT),
        name=DB_NAME,
    )

    # BCLaws SFTP
    BCLAWS_SFTP_STORAGE_DIRECTORY = 'bclaws'

    # BCMail+ SFTP
    BCMAIL_SFTP_STORAGE_DIRECTORY = 'bcmail'


class ProdConfig(_Config):  # pylint: disable=too-few-public-methods
    """Production environment configuration."""

    SECRET_KEY = os.getenv('SECRET_KEY', None)

    if not SECRET_KEY:
        SECRET_KEY = os.urandom(24)
        print('WARNING: SECRET_KEY being set as a one-shot', file=sys.stderr)

    TESTING = False
    DEBUG = False
