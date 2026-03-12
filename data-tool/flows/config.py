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


def _get_int(name: str, default: int = 0) -> int:
    """Safe int env parsing that avoids None.isnumeric() crashes."""
    val = os.getenv(name)
    return int(val) if (val and val.isnumeric()) else default


def _get_bool(name: str, default: bool = False) -> bool:
    """Safe bool env parsing (case-insensitive)."""
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() == 'true'


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
    AFFILIATE_ENTITY_ACCOUNT_ID = os.getenv('AFFILIATE_ENTITY_ACCOUNT_ID', '')
    # Normalized parsed list of ints (preferred for program logic)
    AFFILIATE_ENTITY_ACCOUNT_IDS = [
        int(x.strip()) for x in AFFILIATE_ENTITY_ACCOUNT_ID.split(',')
        if x and x.strip().isdigit()
    ]
    # Normalized CSV string (useful when passing into SQL as a single value)
    AFFILIATE_ENTITY_ACCOUNT_IDS_CSV = (
        ','.join(str(x) for x in AFFILIATE_ENTITY_ACCOUNT_IDS)
        if AFFILIATE_ENTITY_ACCOUNT_IDS else None
    )

    USE_CUSTOM_CONTACT_EMAIL = os.getenv('USE_CUSTOM_CONTACT_EMAIL', 'False') == 'True'
    CUSTOM_CONTACT_EMAIL = os.getenv('CUSTOM_CONTACT_EMAIL', '')
    SEND_UNAFFILIATED_EMAIL = os.getenv('SEND_UNAFFILIATED_EMAIL', 'False') == 'True'

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
    ACCOUNT_SVC_TIMEOUT = _get_int('ACCOUNT_SVC_TIMEOUT', 0)
    ACCOUNT_SVC_TIMEOUT = int(ACCOUNT_SVC_TIMEOUT) if ACCOUNT_SVC_TIMEOUT > 0 else None

    # batch delete flow
    DELETE_BATCHES = _get_int('DELETE_BATCHES', 0)
    DELETE_BATCH_SIZE = _get_int('DELETE_BATCH_SIZE', 0)

    # Fix footgun: env vars may be unset
    DELETE_AUTH_RECORDS = _get_bool('DELETE_AUTH_RECORDS', False)
    DELETE_CORP_PROCESSING_RECORDS = _get_bool('DELETE_CORP_PROCESSING_RECORDS', False)

    # tombstone flow
    TOMBSTONE_BATCHES = _get_int('TOMBSTONE_BATCHES', 0)
    TOMBSTONE_BATCH_SIZE = _get_int('TOMBSTONE_BATCH_SIZE', 0)

    # reservation (reserve_for_flow) query statement timeout (Postgres statement_timeout, in ms).
    # When set, long-running reservation queries fail fast instead of tying up a worker indefinitely.
    RESERVE_STATEMENT_TIMEOUT_MS = os.getenv('RESERVE_STATEMENT_TIMEOUT_MS', '')
    RESERVE_STATEMENT_TIMEOUT_MS = int(RESERVE_STATEMENT_TIMEOUT_MS) if RESERVE_STATEMENT_TIMEOUT_MS.isnumeric() else None

    # verify flow
    VERIFY_BATCHES = _get_int('VERIFY_BATCHES', 0)
    VERIFY_BATCH_SIZE = _get_int('VERIFY_BATCH_SIZE', 0)
    VERIFY_SUMMARY_PATH = os.getenv('VERIFY_SUMMARY_PATH')

    # freeze flow
    FREEZE_BATCHES = _get_int('FREEZE_BATCHES', 0)
    FREEZE_BATCH_SIZE = _get_int('FREEZE_BATCH_SIZE', 0)

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

    # ------------------------------------------------------------------------------------------
    # Auth-only flows (auth_processing tracking)
    # ------------------------------------------------------------------------------------------
    # Selection
    AUTH_SELECTION_MODE = os.getenv('AUTH_SELECTION_MODE', 'MIGRATION_FILTER')
    AUTH_CORP_NUMS = os.getenv('AUTH_CORP_NUMS', '')
    AUTH_SOURCE_FLOW_NAME = os.getenv('AUTH_SOURCE_FLOW_NAME', 'tombstone-flow')

    # Throughput
    AUTH_BATCHES = _get_int('AUTH_BATCHES', 0)
    AUTH_BATCH_SIZE = _get_int('AUTH_BATCH_SIZE', 0)
    AUTH_MAX_WORKERS = _get_int('AUTH_MAX_WORKERS', 50) or 50

    # Create plan
    AUTH_CREATE_ENTITY = _get_bool('AUTH_CREATE_ENTITY', True)
    AUTH_UPSERT_CONTACT = _get_bool('AUTH_UPSERT_CONTACT', False)
    AUTH_CREATE_AFFILIATIONS = _get_bool('AUTH_CREATE_AFFILIATIONS', False)
    AUTH_SEND_UNAFFILIATED_EMAIL = _get_bool('AUTH_SEND_UNAFFILIATED_EMAIL', False)
    AUTH_FAIL_IF_MISSING_EMAIL = _get_bool('AUTH_FAIL_IF_MISSING_EMAIL', False)
    AUTH_DRY_RUN = _get_bool('AUTH_DRY_RUN', False)

    # Delete plan
    AUTH_DELETE_AFFILIATIONS = _get_bool('AUTH_DELETE_AFFILIATIONS', False)
    AUTH_DELETE_ENTITY = _get_bool('AUTH_DELETE_ENTITY', False)
    AUTH_DELETE_INVITES = _get_bool('AUTH_DELETE_INVITES', False)  # unsupported unless API confirmed
    AUTH_REQUIRE_CONFIRMATION = _get_bool('AUTH_REQUIRE_CONFIRMATION', False)
    AUTH_CONFIRMATION_TOKEN = os.getenv('AUTH_CONFIRMATION_TOKEN', '')

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
