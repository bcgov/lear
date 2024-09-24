# Copyright © 2019 Province of British Columbia
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""All of the configuration for the service is captured here.

All items are loaded, or have Constants defined here that
are loaded into the Flask configuration.
All modules and lookups get their configuration from the
Flask config, rather than reading environment variables directly
or by accessing this configuration directly.
"""
import os
import random

from dotenv import find_dotenv, load_dotenv


# this will load all the envars from a .env file located in the project root (api)
load_dotenv(find_dotenv())

CONFIGURATION = {
    'development': 'legal_api.config.DevConfig',
    'testing': 'legal_api.config.TestConfig',
    'production': 'legal_api.config.ProdConfig',
    'default': 'legal_api.config.ProdConfig'
}


def get_named_config(config_name: str = 'production'):
    """Return the configuration object based on the name.

    :raise: KeyError: if an unknown configuration is requested
    """
    if config_name in ['production', 'staging', 'default']:
        config = ProdConfig()
    elif config_name == 'testing':
        config = TestConfig()
    elif config_name == 'development':
        config = DevConfig()
    else:
        raise KeyError(f'Unknown configuration: {config_name}')
    return config


class _Config():  # pylint: disable=too-few-public-methods
    """Base class configuration that should set reasonable defaults.

    Used as the base for all the other configurations.
    """

    PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))

    MSG_RETRY_NUM = int(os.getenv('MSG_RETRY_NUM', '5'))

    SENTRY_DSN = os.getenv('SENTRY_DSN') or ''
    SENTRY_DSN = '' if SENTRY_DSN.lower() == 'null' else SENTRY_DSN
    LD_SDK_KEY = os.getenv('LD_SDK_KEY', None)

    # urls
    DASHBOARD_URL = os.getenv('DASHBOARD_URL', None)
    AUTH_WEB_URL = os.getenv('AUTH_WEB_URL', None)
    NOTIFY_API_URL = os.getenv('NOTIFY_API_URL', None)
    LEGAL_API_URL = os.getenv('LEGAL_API_URL', None)
    PAY_API_URL = os.getenv('PAY_API_URL', None)
    AUTH_URL = os.getenv('AUTH_URL', None)
    ACCOUNT_SVC_AUTH_URL = os.getenv('ACCOUNT_SVC_AUTH_URL', None)
    AUTH_SVC_URL = os.getenv('AUTH_URL', 'https://')
    # secrets
    ACCOUNT_SVC_CLIENT_ID = os.getenv('ACCOUNT_SVC_CLIENT_ID', None)
    ACCOUNT_SVC_CLIENT_SECRET = os.getenv('ACCOUNT_SVC_CLIENT_SECRET', None)
    # variables
    LEGISLATIVE_TIMEZONE = os.getenv('LEGISLATIVE_TIMEZONE', 'America/Vancouver')
    TEMPLATE_PATH = os.getenv('TEMPLATE_PATH', None)

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    NAMEX_AUTH_SVC_URL = os.getenv('NAMEX_AUTH_SVC_URL', None)
    NAMEX_SVC_URL = os.getenv('NAMEX_SVC_URL', None)
    NAMEX_SERVICE_CLIENT_USERNAME = os.getenv('NAMEX_SERVICE_CLIENT_USERNAME', None)
    NAMEX_SERVICE_CLIENT_SECRET = os.getenv('NAMEX_SERVICE_CLIENT_SECRET', None)

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

    TRACKER_DB_USER = os.getenv('TRACKER_DATABASE_USERNAME', '')
    TRACKER_DB_PASSWORD = os.getenv('TRACKER_DATABASE_PASSWORD', '')
    TRACKER_DB_NAME = os.getenv('TRACKER_DATABASE_NAME', '')
    TRACKER_DB_HOST = os.getenv('TRACKER_DATABASE_HOST', '')
    TRACKER_DB_PORT = os.getenv('TRACKER_DATABASE_PORT', '5432')
    TRACKER_SQLALCHEMY_DATABASE_URI = 'postgresql://{user}:{password}@{host}:{port}/{name}'.format(
        user=TRACKER_DB_USER,
        password=TRACKER_DB_PASSWORD,
        host=TRACKER_DB_HOST,
        port=int(TRACKER_DB_PORT),
        name=TRACKER_DB_NAME,
    )

    SQLALCHEMY_BINDS = {
        'tracker': TRACKER_SQLALCHEMY_DATABASE_URI
    }

    NATS_CONNECTION_OPTIONS = {
        'servers': os.getenv('NATS_SERVERS', 'nats://127.0.0.1:4222').split(','),
        'name': os.getenv('NATS_CLIENT_NAME', 'entity.filing.worker')

    }
    STAN_CONNECTION_OPTIONS = {
        'cluster_id': os.getenv('NATS_CLUSTER_ID', 'test-cluster'),
        'client_id': str(random.SystemRandom().getrandbits(0x58)),
        'ping_interval': 1,
        'ping_max_out': 5,
    }

    SUBSCRIPTION_OPTIONS = {
        'subject': os.getenv('NATS_EMAILER_SUBJECT', 'error'),
        'queue': os.getenv('NATS_QUEUE', 'error'),
        'durable_name': os.getenv('NATS_QUEUE', 'error') + '_durable',
    }

    ENTITY_EVENT_PUBLISH_OPTIONS = {
        'subject': os.getenv('NATS_ENTITY_EVENT_SUBJECT', 'entity.events'),
    }

    NAME_REQUEST_URL = os.getenv('NAME_REQUEST_URL', '')
    DECIDE_BUSINESS_URL = os.getenv('DECIDE_BUSINESS_URL', '')
    COLIN_URL = os.getenv('COLIN_URL', '')
    CORP_FORMS_URL = os.getenv('CORP_FORMS_URL', '')
    SOCIETIES_URL = os.getenv('SOCIETIES_URL', '')


class DevConfig(_Config):  # pylint: disable=too-few-public-methods
    """Creates the Development Config object."""

    TESTING = False
    DEBUG = True


class TestConfig(_Config):  # pylint: disable=too-few-public-methods
    """In support of testing only.

    Used by the py.test suite
    """

    DEBUG = True
    TESTING = True
    # POSTGRESQL
    DB_USER = os.getenv('DATABASE_TEST_USERNAME', '')
    DB_PASSWORD = os.getenv('DATABASE_TEST_PASSWORD', '')
    DB_NAME = os.getenv('DATABASE_TEST_NAME', '')
    DB_HOST = os.getenv('DATABASE_TEST_HOST', '')
    DB_PORT = os.getenv('DATABASE_TEST_PORT', '5432')
    DEPLOYMENT_ENV = 'testing'
    LEGAL_API_URL = 'https://legal-api-url/'
    PAY_API_URL = 'https://pay-api-url/'
    SQLALCHEMY_DATABASE_URI = 'postgresql://{user}:{password}@{host}:{port}/{name}'.format(
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=int(DB_PORT),
        name=DB_NAME,
    )

    TRACKER_DB_USER = os.getenv('TRACKER_DATABASE_TEST_USERNAME', '')
    TRACKER_DB_PASSWORD = os.getenv('TRACKER_DATABASE_TEST_PASSWORD', '')
    TRACKER_DB_NAME = os.getenv('TRACKER_DATABASE_TEST_NAME', '')
    TRACKER_DB_HOST = os.getenv('TRACKER_DATABASE_TEST_HOST', '')
    TRACKER_DB_PORT = os.getenv('TRACKER_DATABASE_TEST_PORT', '5432')
    TRACKER_SQLALCHEMY_DATABASE_URI = 'postgresql://{user}:{password}@{host}:{port}/{name}'.format(
        user=TRACKER_DB_USER,
        password=TRACKER_DB_PASSWORD,
        host=TRACKER_DB_HOST,
        port=int(TRACKER_DB_PORT),
        name=TRACKER_DB_NAME,
    )

    SQLALCHEMY_BINDS = {
        'tracker': TRACKER_SQLALCHEMY_DATABASE_URI
    }


class ProdConfig(_Config):  # pylint: disable=too-few-public-methods
    """Production environment configuration."""

    TESTING = False
    DEBUG = False
