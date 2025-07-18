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

    DATA_LOAD_ENV = os.getenv('DATA_LOAD_ENV', '')
    CORP_NAME_SUFFIX = os.getenv('CORP_NAME_SUFFIX', '')
    UPDATE_ENTITY = os.getenv('UPDATE_ENTITY', 'False') == 'True'
    AFFILIATE_ENTITY = os.getenv('AFFILIATE_ENTITY', 'False') == 'True'
    AFFILIATE_ENTITY_ACCOUNT_ID = os.getenv('AFFILIATE_ENTITY_ACCOUNT_ID')
    if AFFILIATE_ENTITY_ACCOUNT_ID.isnumeric():
        AFFILIATE_ENTITY_ACCOUNT_ID = int(AFFILIATE_ENTITY_ACCOUNT_ID)
    else:
        AFFILIATE_ENTITY_ACCOUNT_ID = None

    USE_CUSTOM_CONTACT_EMAIL = os.getenv('USE_CUSTOM_CONTACT_EMAIL', 'False') == 'True'
    CUSTOM_CONTACT_EMAIL = os.getenv('CUSTOM_CONTACT_EMAIL', '')

    USE_CUSTOM_PASSCODE = os.getenv('USE_CUSTOM_PASSCODE', 'False') == 'True'
    CUSTOM_PASSCODE = os.getenv('CUSTOM_PASSCODE', '')

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
    SQLALCHEMY_TRACK_MODIFICATIONS = os.getenv('SQLALCHEMY_TRACK_MODIFICATIONS', False)

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

    DATABASE_POOL_PRE_PING = os.getenv('DATABASE_POOL_PRE_PING', 'True') == 'True'
    DATABASE_POOL_SIZE = os.getenv('DATABASE_POOL_SIZE', '5')
    DATABASE_MAX_OVERFLOW = os.getenv('DATABASE_MAX_OVERFLOW', '10')

    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": DATABASE_POOL_PRE_PING,
        "pool_size": int(DATABASE_POOL_SIZE),
        "max_overflow": int(DATABASE_MAX_OVERFLOW)
    }

    # POSTGRESQL AUTH DB
    DB_USER_AUTH = os.getenv('DATABASE_USERNAME_AUTH', '')
    DB_PASSWORD_AUTH = os.getenv('DATABASE_PASSWORD_AUTH', '')
    DB_NAME_AUTH = os.getenv('DATABASE_NAME_AUTH', '')
    DB_HOST_AUTH = os.getenv('DATABASE_HOST_AUTH', '')
    DB_PORT_AUTH = os.getenv('DATABASE_PORT_AUTH', '5432')
    SQLALCHEMY_DATABASE_URI_AUTH = 'postgresql://{user}:{password}@{host}:{port}/{name}'.format(
        user=DB_USER_AUTH,
        password=DB_PASSWORD_AUTH,
        host=DB_HOST_AUTH,
        port=int(DB_PORT_AUTH),
        name=DB_NAME_AUTH,
    )

    # service accounts
    AUTH_SVC_URL = os.getenv('AUTH_SVC_URL', 'https://')
    ACCOUNT_SVC_AUTH_URL = os.getenv('ACCOUNT_SVC_AUTH_URL')
    ACCOUNT_SVC_ENTITY_URL = os.getenv('ACCOUNT_SVC_ENTITY_URL')
    ACCOUNT_SVC_AFFILIATE_URL = os.getenv('ACCOUNT_SVC_AFFILIATE_URL')
    ACCOUNT_SVC_CLIENT_ID = os.getenv('ACCOUNT_SVC_CLIENT_ID')
    ACCOUNT_SVC_CLIENT_SECRET = os.getenv('ACCOUNT_SVC_CLIENT_SECRET')
    ACCOUNT_SVC_TIMEOUT = os.getenv('ACCOUNT_SVC_TIMEOUT')
    ACCOUNT_SVC_TIMEOUT = int(ACCOUNT_SVC_TIMEOUT) if ACCOUNT_SVC_TIMEOUT.isnumeric() else None

    # batch delete flow
    DELETE_BATCHES = os.getenv('DELETE_BATCHES')
    DELETE_BATCHES = int(DELETE_BATCHES) if DELETE_BATCHES.isnumeric() else 0
    DELETE_BATCH_SIZE = os.getenv('DELETE_BATCH_SIZE')
    DELETE_BATCH_SIZE = int(DELETE_BATCH_SIZE) if DELETE_BATCH_SIZE.isnumeric() else 0

    DELETE_AUTH_RECORDS = os.getenv('DELETE_AUTH_RECORDS').lower() == 'true'
    DELETE_CORP_PROCESSING_RECORDS = os.getenv('DELETE_CORP_PROCESSING_RECORDS').lower() == 'true'

    # tombstone flow
    TOMBSTONE_BATCHES = os.getenv('TOMBSTONE_BATCHES')
    TOMBSTONE_BATCHES = int(TOMBSTONE_BATCHES) if TOMBSTONE_BATCHES.isnumeric() else 0
    TOMBSTONE_BATCH_SIZE = os.getenv('TOMBSTONE_BATCH_SIZE')
    TOMBSTONE_BATCH_SIZE = int(TOMBSTONE_BATCH_SIZE) if TOMBSTONE_BATCH_SIZE.isnumeric() else 0

    # verify flow
    VERIFY_BATCH_SIZE = os.getenv('VERIFY_BATCH_SIZE')
    VERIFY_BATCH_SIZE = int(VERIFY_BATCH_SIZE) if VERIFY_BATCH_SIZE.isnumeric() else 0
    VERIFY_SUMMARY_PATH = os.getenv('VERIFY_SUMMARY_PATH')

    # freeze flow
    FREEZE_BATCHES = os.getenv('FREEZE_BATCHES')
    FREEZE_BATCHES = int(FREEZE_BATCHES) if FREEZE_BATCHES.isnumeric() else 0
    FREEZE_BATCH_SIZE = os.getenv('FREEZE_BATCH_SIZE')
    FREEZE_BATCH_SIZE = int(FREEZE_BATCH_SIZE) if FREEZE_BATCH_SIZE.isnumeric() else 0
    # ORACLE COLIN DB
    DB_USER_COLIN_ORACLE = os.getenv('DATABASE_USERNAME_COLIN_ORACLE', '')
    DB_PASSWORD_COLIN_ORACLE = os.getenv('DATABASE_PASSWORD_COLIN_ORACLE', '')
    DB_NAME_COLIN_ORACLE = os.getenv('DATABASE_NAME_COLIN_ORACLE', '')
    DB_HOST_COLIN_ORACLE = os.getenv('DATABASE_HOST_COLIN_ORACLE', '')
    DB_PORT_COLIN_ORACLE = os.getenv('DATABASE_PORT_COLIN_ORACLE', '1521')
    SQLALCHEMY_DATABASE_URI_COLIN_ORACLE = 'oracle+oracledb://{user}:{password}@{host}:{port}/{name}'.format(
        user=DB_USER_COLIN_ORACLE,
        password=DB_PASSWORD_COLIN_ORACLE,
        host=DB_HOST_COLIN_ORACLE,
        port=int(DB_PORT_COLIN_ORACLE),
        name=DB_NAME_COLIN_ORACLE,
    )
    FREEZE_COLIN_CORPS = os.getenv('FREEZE_COLIN_CORPS', 'False') == 'True'
    FREEZE_ADD_EARLY_ADOPTER = os.getenv('FREEZE_ADD_EARLY_ADOPTER', 'False') == 'True'

    USE_MIGRATION_FILTER = os.getenv('USE_MIGRATION_FILTER', 'False') == 'True'
    MIG_GROUP_IDS = os.getenv('MIG_GROUP_IDS')
    MIG_BATCH_IDS = os.getenv('MIG_BATCH_IDS')

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
