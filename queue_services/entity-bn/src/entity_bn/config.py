# Copyright © 2022 Province of British Columbia
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
    SERVICE_NAME = 'entity-bn'
    PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))

    SENTRY_DSN = os.getenv('SENTRY_DSN') or ''
    SENTRY_DSN = '' if SENTRY_DSN.lower() == 'null' else SENTRY_DSN
    LD_SDK_KEY = os.getenv('LD_SDK_KEY', None)
    COLIN_API = f"{os.getenv('COLIN_API_URL', '')}{os.getenv('COLIN_API_VERSION', '')}"

    SEARCH_API = \
        f"{os.getenv('REGISTRIES_SEARCH_API_INTERNAL_URL', '')}{os.getenv('REGISTRIES_SEARCH_API_VERSION', '/api/v1')}"

    # service accounts
    ACCOUNT_SVC_AUTH_URL = os.getenv('ACCOUNT_SVC_AUTH_URL')
    ACCOUNT_SVC_CLIENT_ID = os.getenv('ACCOUNT_SVC_CLIENT_ID')
    ACCOUNT_SVC_CLIENT_SECRET = os.getenv('ACCOUNT_SVC_CLIENT_SECRET')
    ACCOUNT_SVC_TIMEOUT = os.getenv('ACCOUNT_SVC_TIMEOUT')

    BN_HUB_API_URL = os.getenv('BN_HUB_API_URL', None)
    BN_HUB_CLIENT_ID = os.getenv('BN_HUB_CLIENT_ID', None)
    BN_HUB_CLIENT_SECRET = os.getenv('BN_HUB_CLIENT_SECRET', None)
    BN_HUB_MAX_RETRY = int(os.getenv('BN_HUB_MAX_RETRY', '9'))
    TEMPLATE_PATH = os.getenv('TEMPLATE_PATH', None)

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # POSTGRESQL
    DB_USER = os.getenv('ENTITY_DATABASE_USERNAME', '')
    DB_PASSWORD = os.getenv('ENTITY_DATABASE_PASSWORD', '')
    DB_NAME = os.getenv('ENTITY_DATABASE_NAME', '')
    DB_HOST = os.getenv('ENTITY_DATABASE_HOST', '')
    DB_PORT = os.getenv('ENTITY_DATABASE_PORT', '5432')
    SQLALCHEMY_DATABASE_URI = f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'

    NATS_CONNECTION_OPTIONS = {
        'servers': os.getenv('NATS_SERVERS', 'nats://127.0.0.1:4222').split(','),
        'name': os.getenv('NATS_CLIENT_NAME', 'entity.bn.worker')
    }

    STAN_CONNECTION_OPTIONS = {
        'cluster_id': os.getenv('NATS_CLUSTER_ID', 'test-cluster'),
        'client_id': str(random.SystemRandom().getrandbits(0x58)),
        'ping_interval': 1,
        'ping_max_out': 5,
    }

    SUBSCRIPTION_OPTIONS = {
        'subject': os.getenv('NATS_ENTITY_EVENT_SUBJECT', 'error'),
        'queue': os.getenv('NATS_QUEUE', 'error'),
        'durable_name': os.getenv('NATS_QUEUE', 'error') + '_durable',
    }

    EMAIL_PUBLISH_OPTIONS = {
        'subject': os.getenv('NATS_EMAILER_SUBJECT', 'entity.email'),
    }

    # legislative timezone for future effective dating
    LEGISLATIVE_TIMEZONE = os.getenv('LEGISLATIVE_TIMEZONE', 'America/Vancouver')


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
    SQLALCHEMY_DATABASE_URI = f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'


class ProdConfig(_Config):  # pylint: disable=too-few-public-methods
    """Production environment configuration."""

    TESTING = False
    DEBUG = False
