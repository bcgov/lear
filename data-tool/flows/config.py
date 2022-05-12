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
import sys

from dotenv import find_dotenv, load_dotenv


# this will load all the envars from a .env file located in the project root (api)
load_dotenv(find_dotenv())


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

    # POSTGRESQL COLIN MIGRATION DB
    DB_USER_COLIN_MIGR = os.getenv('DATABASE_USERNAME_COLIN_MIGR', '')
    DB_PASSWORD_COLIN_MIGR = os.getenv('DATABASE_PASSWORD_COLIN_MIGR', '')
    DB_NAME_COLIN_MIGR = os.getenv('DATABASE_NAME_COLIN_MIGR', '')
    DB_HOST_COLIN_MIGR = os.getenv('DATABASE_HOST_COLIN_MIGR', '')
    DB_PORT_COLIN_MIGR = os.getenv('DATABASE_PORT_COLIN_MIGR', '5432')
    SQLALCHEMY_DATABASE_URI_COLIN_MIGR = 'postgresql://{user}:{password}@{host}:{port}/{name}'.format(
        user=DB_USER_COLIN_MIGR,
        password=DB_PASSWORD_COLIN_MIGR,
        host=DB_HOST_COLIN_MIGR,
        port=int(DB_PORT_COLIN_MIGR),
        name=DB_NAME_COLIN_MIGR,
    )

    # POSTGRESQL LEAR DB
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

    # service accounts
    ACCOUNT_SVC_AUTH_URL = os.getenv('ACCOUNT_SVC_AUTH_URL')
    ACCOUNT_SVC_ENTITY_URL = os.getenv('ACCOUNT_SVC_ENTITY_URL')
    ACCOUNT_SVC_AFFILIATE_URL = os.getenv('ACCOUNT_SVC_AFFILIATE_URL')
    ACCOUNT_SVC_CLIENT_ID = os.getenv('ACCOUNT_SVC_CLIENT_ID')
    ACCOUNT_SVC_CLIENT_SECRET = os.getenv('ACCOUNT_SVC_CLIENT_SECRET')
    ACCOUNT_SVC_TIMEOUT = os.getenv('ACCOUNT_SVC_TIMEOUT')

    TESTING = False
    DEBUG = False


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



class ProdConfig(_Config):  # pylint: disable=too-few-public-methods
    """Production environment configuration."""

    TESTING = False
    DEBUG = False
