# Copyright © 2026 Province of British Columbia
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
from sqlalchemy import create_engine

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
    
    # POSTGRESQL COLIN MIGRATION DB
    DB_USER_COLIN_MIGR = os.getenv('DATABASE_USERNAME_COLIN_MIGR', '')
    DB_PASSWORD_COLIN_MIGR = os.getenv('DATABASE_PASSWORD_COLIN_MIGR', '')
    DB_NAME_COLIN_MIGR = os.getenv('DATABASE_NAME_COLIN_MIGR', '')
    DB_HOST_COLIN_MIGR = os.getenv('DATABASE_HOST_COLIN_MIGR', '')
    DB_PORT_COLIN_MIGR = os.getenv('DATABASE_PORT_COLIN_MIGR', '5432')
    CLOUDSQL_INSTANCE_CONNECTION_NAME = os.getenv('CLOUDSQL_INSTANCE_CONNECTION_NAME', '')
    TARGET_CONNECTION = os.getenv('TARGET_CONNECTION', 'ctst_pg')
    TARGET_SCHEMA = os.getenv('TARGET_SCHEMA', '')
    MIG_BATCH_IDS = os.getenv('MIG_BATCH_IDS')
    DATABASE_IP_TYPE = os.getenv('DATABASE_IP_TYPE', 'private').lower()
    if CLOUDSQL_INSTANCE_CONNECTION_NAME:
        SQLALCHEMY_DATABASE_URI_COLIN_MIGR = "postgresql+pg8000://"

    elif DB_HOST_COLIN_MIGR:
        SQLALCHEMY_DATABASE_URI_COLIN_MIGR = 'postgresql://{user}:{password}@{host}:{port}/{name}'.format(
            user=DB_USER_COLIN_MIGR,
            password=DB_PASSWORD_COLIN_MIGR,
            host=DB_HOST_COLIN_MIGR,
            port=int(DB_PORT_COLIN_MIGR),
            name=DB_NAME_COLIN_MIGR,
        )
    else:
        SQLALCHEMY_DATABASE_URI_COLIN_MIGR = ''
        SQLALCHEMY_TRACK_MODIFICATIONS = os.getenv('SQLALCHEMY_TRACK_MODIFICATIONS', False)


    DATABASE_POOL_PRE_PING = os.getenv('DATABASE_POOL_PRE_PING', 'True') == 'True'
    DATABASE_POOL_SIZE = os.getenv('DATABASE_POOL_SIZE', '5')
    DATABASE_MAX_OVERFLOW = os.getenv('DATABASE_MAX_OVERFLOW', '10')

    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": DATABASE_POOL_PRE_PING,
        "pool_size": int(DATABASE_POOL_SIZE),
        "max_overflow": int(DATABASE_MAX_OVERFLOW)
    }

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


def get_colin_mig_conn(cfg: _Config):
    from cloud_sql_connector import DBConfig, getconn
    config = DBConfig(
        instance_name=cfg.CLOUDSQL_INSTANCE_CONNECTION_NAME,
        database=cfg.DB_NAME_COLIN_MIGR,
        user=cfg.DB_USER_COLIN_MIGR,
        ip_type=cfg.DATABASE_IP_TYPE,
        schema="public"
    )
    return getconn(config)

def get_colin_mig_engine(cfg: _Config | None = None):
    cfg = cfg or get_named_config()
    if cfg.CLOUDSQL_INSTANCE_CONNECTION_NAME and cfg.DB_NAME_COLIN_MIGR and cfg.DB_USER_COLIN_MIGR:
        return create_engine("postgresql+pg8000://", creator=lambda: get_colin_mig_conn(cfg))
    else:
        return create_engine(cfg.SQLALCHEMY_DATABASE_URI_COLIN_MIGR, **cfg.SQLALCHEMY_ENGINE_OPTIONS)
