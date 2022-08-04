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

All items are loaded, or have Constants defined here that
are loaded into the Flask configuration.
All modules and lookups get their configuration from the
Flask config, rather than reading environment variables directly
or by accessing this configuration directly.
"""

import os
import sys

from dotenv import find_dotenv, load_dotenv


# this will load all the envars from a .env file located in the project root (api)
load_dotenv(find_dotenv())

CONFIGURATION = {
    'development': 'colin_api.config.DevConfig',
    'testing': 'colin_api.config.TestConfig',
    'production': 'colin_api.config.ProdConfig',
    'default': 'colin_api.config.ProdConfig'
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
        raise KeyError(f"Unknown configuration '{config_name}'")
    return config


class _Config:  # pylint: disable=too-few-public-methods
    """Base class configuration that should set reasonable defaults for all the other configurations."""

    PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))

    SECRET_KEY = 'a secret'

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    SENTRY_ENABLE = os.getenv('SENTRY_ENABLE', 'False')

    SENTRY_DSN = os.getenv('SENTRY_DSN', '')

    # ORACLE - CDEV/CTST/CPRD
    ORACLE_USER = os.getenv('ORACLE_USER', '')
    ORACLE_PASSWORD = os.getenv('ORACLE_PASSWORD', '')
    ORACLE_DB_NAME = os.getenv('ORACLE_DB_NAME', '')
    ORACLE_HOST = os.getenv('ORACLE_HOST', '')
    ORACLE_PORT = int(os.getenv('ORACLE_PORT', '1521'))
    ORACLE_BNI_DB_LINK = os.getenv('ORACLE_BNI_DB_LINK', '')

    TESTING = False
    DEBUG = False


class DevConfig(_Config):  # pylint: disable=too-few-public-methods
    """Creates the Development Config object."""

    TESTING = False
    DEBUG = True


class TestConfig(_Config):  # pylint: disable=too-few-public-methods
    """In support of testing only used by the py.test suite."""

    DEBUG = True
    TESTING = True

    # TEST ORACLE
    ORACLE_USER = os.getenv('TEST_ORACLE_USER', '')
    ORACLE_SCHEMA = os.getenv('TEST_ORACLE_SCHEMA', None)
    ORACLE_PASSWORD = os.getenv('TEST_ORACLE_PASSWORD', '')
    ORACLE_DB_NAME = os.getenv('TEST_ORACLE_DB_NAME', '')
    ORACLE_HOST = os.getenv('TEST_ORACLE_HOST', '')
    ORACLE_PORT = int(os.getenv('TEST_ORACLE_PORT', '1521'))


class ProdConfig(_Config):  # pylint: disable=too-few-public-methods
    """Production environment configuration."""

    SECRET_KEY = os.getenv('SECRET_KEY', None)

    if not SECRET_KEY:
        SECRET_KEY = os.urandom(24)
        print('WARNING: SECRET_KEY being set as a one-shot', file=sys.stderr)

    TESTING = False
    DEBUG = False
