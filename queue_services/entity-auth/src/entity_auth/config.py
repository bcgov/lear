# Copyright © 2023 Province of British Columbia
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

from dotenv import find_dotenv, load_dotenv


# this will load all the envars from a .env file located in the project root (api)
load_dotenv(find_dotenv())


class Config:  # pylint: disable=too-few-public-methods
    """Base class configuration that should set reasonable defaults.

    Used as the base for all the other configurations.
    """

    PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))

    ENVIRONMENT = os.getenv("APP_ENV", "prod")

    SENTRY_DSN = os.getenv("SENTRY_DSN", None)

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # POSTGRESQL
    DB_USER = os.getenv("DATABASE_USERNAME", "")
    DB_PASSWORD = os.getenv("DATABASE_PASSWORD", "")
    DB_NAME = os.getenv("DATABASE_NAME", "")
    DB_HOST = os.getenv("DATABASE_HOST", "")
    DB_PORT = os.getenv("DATABASE_PORT", "5432")

    # POSTGRESQL
    if DB_UNIX_SOCKET := os.getenv("DATABASE_UNIX_SOCKET", None):
        SQLALCHEMY_DATABASE_URI = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@/{DB_NAME}?host={DB_UNIX_SOCKET}"
    else:
        SQLALCHEMY_DATABASE_URI = (
            f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
        )

    # API Endpoints
    NAMEX_API_URL = os.getenv("NAMEX_API_URL", "")
    NAMEX_API_VERSION = os.getenv("NAMEX_API_VERSION", "")

    NAMEX_API = f"{NAMEX_API_URL + NAMEX_API_VERSION}"

    # service accounts
    ACCOUNT_SVC_AUTH_URL = os.getenv("KEYCLOAK_AUTH_TOKEN_URL")
    ACCOUNT_SVC_CLIENT_ID = os.getenv("KEYCLOAK_CLIENT_ID")
    ACCOUNT_SVC_CLIENT_SECRET = os.getenv("KEYCLOAK_CLIENT_ID")
    ACCOUNT_SVC_TIMEOUT = os.getenv("KEYCLOAK_TIMEOUT")

    # pub/sub
    GCP_AUTH_KEY = os.getenv("GCP_AUTH_KEY", None)
    AUDIENCE = os.getenv(
        "AUDIENCE", "https://pubsub.googleapis.com/google.pubsub.v1.Subscriber"
    )
    PUBLISHER_AUDIENCE = os.getenv(
        "PUBLISHER_AUDIENCE", "https://pubsub.googleapis.com/google.pubsub.v1.Publisher"
    )

    # legislative timezone for future effective dating
    LEGISLATIVE_TIMEZONE = os.getenv("LEGISLATIVE_TIMEZONE", "America/Vancouver")


class Development(Config):  # pylint: disable=too-few-public-methods
    """Creates the Development Config object."""

    TESTING = False
    DEBUG = True


class Testing(Config):  # pylint: disable=too-few-public-methods
    """In support of testing only.

    Used by the py.test suite
    """

    DEBUG = True
    TESTING = True
    # POSTGRESQL
    DB_USER = os.getenv("DATABASE_TEST_USERNAME", "")
    DB_PASSWORD = os.getenv("DATABASE_TEST_PASSWORD", "")
    DB_NAME = os.getenv("DATABASE_TEST_NAME", "")
    DB_HOST = os.getenv("DATABASE_TEST_HOST", "")
    DB_PORT = os.getenv("DATABASE_TEST_PORT", "5432")
    SQLALCHEMY_DATABASE_URI = f"postgresql+pg8000://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{int(DB_PORT)}/{DB_NAME}"


class Production(Config):  # pylint: disable=too-few-public-methods
    """Production environment configuration."""

    TESTING = False
    DEBUG = False
