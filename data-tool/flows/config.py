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


def _get_strict_int(name: str, default: int = 0) -> int:
    """Parse an integer env var, raising when a non-blank value is invalid."""
    val = os.getenv(name)
    if val is None or val.strip() == '':
        return default
    try:
        return int(val)
    except ValueError as exc:
        raise ValueError(f'{name} must be a valid integer') from exc


def _get_bool(name: str, default: bool = False) -> bool:
    """Safe bool env parsing (case-insensitive)."""
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in ('true', '1')


def _parse_int_csv(raw_value: str) -> list[int]:
    """Parse a comma-separated list into ints, ignoring blanks and non-numeric tokens."""
    return [
        int(x.strip()) for x in (raw_value or '').split(',')
        if x and x.strip().isdigit()
    ]


def _normalized_csv(values: list[int]):
    """Return a normalized comma-separated string for integer values."""
    return ','.join(str(x) for x in values) if values else None


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
    TARGET_CONNECTION = os.getenv('TARGET_CONNECTION', 'ctst_pg')
    CORP_NAME_SUFFIX = os.getenv('CORP_NAME_SUFFIX', '')
    UPDATE_ENTITY = os.getenv('UPDATE_ENTITY', 'False') == 'True'
    AFFILIATE_ENTITY = os.getenv('AFFILIATE_ENTITY', 'False') == 'True'
    AFFILIATE_ENTITY_ACCOUNT_ID = os.getenv('AFFILIATE_ENTITY_ACCOUNT_ID', '')
    # Normalized parsed list of ints (preferred for program logic)
    AFFILIATE_ENTITY_ACCOUNT_IDS = _parse_int_csv(AFFILIATE_ENTITY_ACCOUNT_ID)
    # Normalized CSV string (useful when passing into SQL as a single value)
    AFFILIATE_ENTITY_ACCOUNT_IDS_CSV = _normalized_csv(AFFILIATE_ENTITY_ACCOUNT_IDS)

    USE_CUSTOM_CONTACT_EMAIL = _get_bool('USE_CUSTOM_CONTACT_EMAIL', False)
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
    # When enabled, use source ODS values to flip eligible tombstone filings to paper_only=False.
    # Default False preserves legacy tombstone behavior (paper_only=True for all migrated filings).
    TOMBSTONE_USE_SOURCE_PAPER_ONLY = _get_bool('TOMBSTONE_USE_SOURCE_PAPER_ONLY', False)

    # reservation (reserve_for_flow) query statement timeout (Postgres statement_timeout, in ms).
    # Default to 5 minutes so reservation queries fail fast instead of tying up a worker indefinitely.
    RESERVE_STATEMENT_TIMEOUT_MS = _get_strict_int('RESERVE_STATEMENT_TIMEOUT_MS', 300000)

    # verify flow
    VERIFY_BATCHES = _get_int('VERIFY_BATCHES', 0)
    VERIFY_BATCH_SIZE = _get_int('VERIFY_BATCH_SIZE', 0)
    VERIFY_SUMMARY_PATH = os.getenv('VERIFY_SUMMARY_PATH')

    # verify COLIN updates flow
    VERIFY_COLIN_UPDATES_BATCHES = _get_strict_int('VERIFY_COLIN_UPDATES_BATCHES', 0)
    VERIFY_COLIN_UPDATES_BATCH_SIZE = _get_strict_int('VERIFY_COLIN_UPDATES_BATCH_SIZE', 0)
    VERIFY_COLIN_UPDATES_CHECK_FREEZE = _get_bool('VERIFY_COLIN_UPDATES_CHECK_FREEZE', True)
    VERIFY_COLIN_UPDATES_CHECK_EARLY_ADOPTER = _get_bool('VERIFY_COLIN_UPDATES_CHECK_EARLY_ADOPTER', True)
    VERIFY_COLIN_UPDATES_CHECK_AR_IND_IS_NO = _get_bool('VERIFY_COLIN_UPDATES_CHECK_AR_IND_IS_NO', False)
    VERIFY_COLIN_UPDATES_DETAIL_PATH = os.getenv('VERIFY_COLIN_UPDATES_DETAIL_PATH')
    VERIFY_COLIN_UPDATES_SUMMARY_PATH = os.getenv('VERIFY_COLIN_UPDATES_SUMMARY_PATH')

    # freeze flow
    FREEZE_BATCHES = _get_int('FREEZE_BATCHES', 0)
    FREEZE_BATCH_SIZE = _get_int('FREEZE_BATCH_SIZE', 0)
    FREEZE_ORACLE_CHUNK_SIZE = _get_strict_int('FREEZE_ORACLE_CHUNK_SIZE', 1000)

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
    AUTH_MIG_GROUP_IDS = os.getenv('AUTH_MIG_GROUP_IDS')
    AUTH_MIG_BATCH_IDS = os.getenv('AUTH_MIG_BATCH_IDS')
    AUTH_REPEATABLE_CYCLE_KEY = os.getenv('AUTH_REPEATABLE_CYCLE_KEY', '')
    AUTH_REPEATABLE_CAMPAIGN_SCOPE = os.getenv('AUTH_REPEATABLE_CAMPAIGN_SCOPE', '')

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

    # Auth-only affiliation fallback accounts. Separate Auth flows intentionally do not
    # alias/fallback from tombstone AFFILIATE_ENTITY_ACCOUNT_ID(S).
    AUTH_AFFILIATION_ACCOUNT_IDS_RAW = os.getenv('AUTH_AFFILIATION_ACCOUNT_IDS', '')
    AUTH_AFFILIATION_ACCOUNT_IDS = _parse_int_csv(AUTH_AFFILIATION_ACCOUNT_IDS_RAW)
    AUTH_AFFILIATION_ACCOUNT_IDS_CSV = _normalized_csv(AUTH_AFFILIATION_ACCOUNT_IDS)

    # Delete plan
    AUTH_DELETE_AFFILIATIONS = _get_bool('AUTH_DELETE_AFFILIATIONS', False)
    AUTH_DELETE_ENTITY = _get_bool('AUTH_DELETE_ENTITY', False)
    AUTH_DELETE_TRACKING_CLEANUP_MODE = os.getenv('AUTH_DELETE_TRACKING_CLEANUP_MODE', 'OFF')

    # Tracking
    AUTH_LOG_COMPONENT_OPERATIONS = _get_bool('AUTH_LOG_COMPONENT_OPERATIONS', False)

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
