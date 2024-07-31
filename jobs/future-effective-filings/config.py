# Copyright © 2019 Province of British Columbia
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

"""All of the configuration for the service is captured here.

All items are loaded, or have Constants defined here that are loaded into the Flask configuration.
All modules and lookups get their configuration from the Flask config, rather than reading environment variables
directly or by accessing this configuration directly.
"""
import os
import random
import sys

from dotenv import find_dotenv, load_dotenv


# this will load all the envars from a .env file located in the project root (api)
load_dotenv(find_dotenv())

CONFIGURATION = {
    'development': 'config.DevConfig',
    'testing': 'config.TestConfig',
    'production': 'config.ProdConfig',
    'default': 'config.ProdConfig'
}


def get_named_config(config_name: str = 'production'):
    """Return the configuration object based on the name.

    :raise: KeyError: if an unknown configuration is requested
    """
    if config_name in['production', 'staging', 'default']:
        config = ProdConfig()
    elif config_name == 'testing':
        config = TestConfig()
    elif config_name == 'development':
        config = DevConfig()
    else:
        raise KeyError(f"Unknown configuration '{config_name}'")
    return config


class _Config(object):  # pylint: disable=too-few-public-methods
    """Base class configuration that should set reasonable defaults for all the other configurations."""

    NATS_CONNECTION_OPTIONS = {
        'servers': os.getenv('NATS_SERVERS', 'nats://127.0.0.1:4222').split(','),
        'name': os.getenv('NATS_CLIENT_NAME', 'entity.filing.worker')
    }
    STAN_CONNECTION_OPTIONS = {
        'cluster_id': os.getenv('NATS_CLUSTER_ID', 'test-cluster'),
        'client_id': str(random.SystemRandom().getrandbits(0x58)),
        'ping_interval': 1,
        'ping_max_out': 5
    }

    SUBSCRIPTION_OPTIONS = {
        'subject': os.getenv('NATS_SUBJECT', 'entity.filings'),
        'queue': os.getenv('NATS_QUEUE', 'filing-worker'),
        'durable_name': os.getenv('NATS_QUEUE', 'filing-worker') + '_durable'
    }

    FILER_PUBLISH_OPTIONS = {
        'subject': os.getenv('NATS_FILER_SUBJECT', 'entity.filing.filer')
    }

    PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))

    COLIN_URL = os.getenv('COLIN_URL', '')
    LEGAL_URL = os.getenv('LEGAL_URL', '')
    AUTH_URL = os.getenv('AUTH_URL', '')
    USERNAME = os.getenv('AUTH_USERNAME', '')
    PASSWORD = os.getenv('AUTH_PASSWORD', '')
    SENTRY_DSN = os.getenv('SENTRY_DSN') or ''
    SENTRY_DSN = '' if SENTRY_DSN.lower() == 'null' else SENTRY_DSN

    SECRET_KEY = 'a secret'

    TESTING = False
    DEBUG = False


class DevConfig(_Config):  # pylint: disable=too-few-public-methods
    """Config for local development."""

    TESTING = False
    DEBUG = True


class TestConfig(_Config):  # pylint: disable=too-few-public-methods
    """In support of testing only used by the py.test suite."""

    DEBUG = True
    TESTING = True

    NATS_CONNECTION_OPTIONS = {
        'servers': os.getenv('NATS_SERVERS_TEST', '').split(','),
        'name': os.getenv('NATS_CLIENT_NAME_TEST', '')
    }
    STAN_CONNECTION_OPTIONS = {
        'cluster_id': os.getenv('NATS_CLUSTER_ID_TEST', ''),
        'client_id': str(random.SystemRandom().getrandbits(0x58)),
        'ping_interval': 1,
        'ping_max_out': 5
    }

    SUBSCRIPTION_OPTIONS = {
        'subject': os.getenv('NATS_SUBJECT_TEST', ''),
        'queue': os.getenv('NATS_QUEUE_TEST', ''),
        'durable_name': os.getenv('NATS_QUEUE_TEST', '') + '_durable'
    }

    FILER_PUBLISH_OPTIONS = {
        'subject': os.getenv('NATS_FILER_SUBJECT_TEST', '')
    }

    COLIN_URL = os.getenv('COLIN_URL_TEST', '')
    LEGAL_URL = os.getenv('LEGAL_URL_TEST', '')
    AUTH_URL = os.getenv('AUTH_URL_TEST', '')
    USERNAME = os.getenv('AUTH_USERNAME_TEST', '')
    PASSWORD = os.getenv('AUTH_PASSWORD_TEST', '')
    SENTRY_DSN = os.getenv('SENTRY_DSN_TEST', '')


class ProdConfig(_Config):  # pylint: disable=too-few-public-methods
    """Production environment configuration."""

    SECRET_KEY = os.getenv('SECRET_KEY', None)

    if not SECRET_KEY:
        SECRET_KEY = os.urandom(24)
        print('WARNING: SECRET_KEY being set as a one-shot', file=sys.stderr)

    TESTING = False
    DEBUG = False
