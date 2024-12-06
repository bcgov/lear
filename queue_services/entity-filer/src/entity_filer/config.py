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

    SERVICE_NAME = 'filer'
    PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))

    PAYMENT_SVC_URL = os.getenv('PAYMENT_SVC_URL', '')

    SENTRY_DSN = os.getenv('SENTRY_DSN') or ''
    SENTRY_DSN = '' if SENTRY_DSN.lower() == 'null' else SENTRY_DSN

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    REPORT_TEMPLATE_PATH = os.getenv('REPORT_PATH', 'report-templates')

    FONTS_PATH = os.getenv('FONTS_PATH', 'fonts')

    LD_SDK_KEY = os.getenv('LD_SDK_KEY', None)

    # POSTGRESQL
    DB_USER = os.getenv('DATABASE_USERNAME', '')
    DB_PASSWORD = os.getenv('DATABASE_PASSWORD', '')
    DB_NAME = os.getenv('DATABASE_NAME', '')
    DB_HOST = os.getenv('DATABASE_HOST', '')
    DB_PORT = os.getenv('DATABASE_PORT', '5432')
    SQLALCHEMY_DATABASE_URI = f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'

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
        'subject': os.getenv('NATS_FILER_SUBJECT', 'error'),
        'queue': os.getenv('NATS_QUEUE', 'error'),
        'durable_name': os.getenv('NATS_QUEUE', 'error') + '_durable',
    }

    ENTITY_EVENT_PUBLISH_OPTIONS = {
        'subject': os.getenv('NATS_ENTITY_EVENT_SUBJECT', 'entity.events'),
    }

    EMAIL_PUBLISH_OPTIONS = {
        'subject': os.getenv('NATS_EMAILER_SUBJECT', 'entity.email'),
    }

    COLIN_API = os.getenv('COLIN_API', '')

    # service accounts
    AUTH_SVC_URL = os.getenv('AUTH_SVC_URL', 'https://')
    ACCOUNT_SVC_AUTH_URL = os.getenv('ACCOUNT_SVC_AUTH_URL')
    ACCOUNT_SVC_CLIENT_ID = os.getenv('ACCOUNT_SVC_CLIENT_ID')
    ACCOUNT_SVC_CLIENT_SECRET = os.getenv('ACCOUNT_SVC_CLIENT_SECRET')
    ACCOUNT_SVC_TIMEOUT = os.getenv('ACCOUNT_SVC_TIMEOUT')

    # BCRegistry Services
    ACCOUNT_SVC_ENTITY_URL = os.getenv('ACCOUNT_SVC_ENTITY_URL')
    ACCOUNT_SVC_AFFILIATE_URL = os.getenv('ACCOUNT_SVC_AFFILIATE_URL')
    LEGAL_API_URL = os.getenv('LEGAL_API_URL')
    NAMEX_API = os.getenv('NAMEX_API')

    # legislative timezone for future effective dating
    LEGISLATIVE_TIMEZONE = os.getenv('LEGISLATIVE_TIMEZONE', 'America/Vancouver')

    # Minio configuration values
    MINIO_ENDPOINT = os.getenv('MINIO_ENDPOINT')
    MINIO_ACCESS_KEY = os.getenv('MINIO_ACCESS_KEY')
    MINIO_ACCESS_SECRET = os.getenv('MINIO_ACCESS_SECRET')
    MINIO_BUCKET_BUSINESSES = os.getenv('MINIO_BUCKET_BUSINESSES', 'businesses')
    MINIO_SECURE = True

    NAICS_API_URL = os.getenv('NAICS_API_URL', 'https://NAICS_API_URL/api/v2/naics')

    # GCP Queue Configs
    GCP_AUTH_KEY = os.getenv('BUSINESS_GCP_AUTH_KEY', None)
    BUSINESS_EVENTS_TOPIC = os.getenv('BUSINESS_EVENTS_TOPIC', 'business-event-dev')
    BUSINESS_PAY_TOPIC = os.getenv('BUSINESS_PAY_TOPIC', 'business-pay-dev')
    NAMEX_PAY_TOPIC = os.getenv('NAMEX_PAY_TOPIC', 'namex-pay-dev')

    AUDIENCE = os.getenv(
        'AUDIENCE', 'https://pubsub.googleapis.com/google.pubsub.v1.Subscriber'
    )
    PUBLISHER_AUDIENCE = os.getenv(
        'PUBLISHER_AUDIENCE', 'https://pubsub.googleapis.com/google.pubsub.v1.Publisher'
    )


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

    # Minio variables
    MINIO_ENDPOINT = 'localhost:9000'
    MINIO_ACCESS_KEY = 'minio'
    MINIO_ACCESS_SECRET = 'minio123'
    MINIO_BUCKET_BUSINESSES = 'businesses'
    MINIO_SECURE = False

    NAICS_API_URL = 'https://NAICS_API_URL/api/v2/naics'


class ProdConfig(_Config):  # pylint: disable=too-few-public-methods
    """Production environment configuration."""

    TESTING = False
    DEBUG = False
