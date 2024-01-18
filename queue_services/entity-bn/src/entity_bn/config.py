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

    # service accounts
    ACCOUNT_SVC_AUTH_URL = os.getenv("ACCOUNT_SVC_AUTH_URL")
    ACCOUNT_SVC_CLIENT_ID = os.getenv("ACCOUNT_SVC_CLIENT_ID")
    ACCOUNT_SVC_CLIENT_SECRET = os.getenv("ACCOUNT_SVC_CLIENT_SECRET")
    ACCOUNT_SVC_TIMEOUT = os.getenv("ACCOUNT_SVC_TIMEOUT")

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # POSTGRESQL
    DB_USER = os.getenv("DATABASE_USERNAME", "")
    DB_PASSWORD = os.getenv("DATABASE_PASSWORD", "")
    DB_NAME = os.getenv("DATABASE_NAME", "")
    DB_HOST = os.getenv("DATABASE_HOST", "")
    DB_PORT = os.getenv("DATABASE_PORT", "5432")

    # POSTGRESQL
    if DB_UNIX_SOCKET := os.getenv("DATABASE_UNIX_SOCKET", None):
        SQLALCHEMY_DATABASE_URI = f"postgresql+pg8000://{DB_USER}:{DB_PASSWORD}@/{DB_NAME}?unix_sock={DB_UNIX_SOCKET}/.s.PGSQL.5432"
    else:
        SQLALCHEMY_DATABASE_URI = (
            f"postgresql+pg8000://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
        )

    # legislative timezone for future effective dating
    LEGISLATIVE_TIMEZONE = os.getenv(
        "LEGISLATIVE_TIMEZONE", "America/Vancouver")
    TEMPLATE_PATH = os.getenv("TEMPLATE_PATH", None)

    # API Endpoints
    COLIN_API_URL = os.getenv("COLIN_API_URL", "")
    COLIN_API_VERSION = os.getenv("COLIN_API_VERSION", "")
    SEARCH_API_URL = os.getenv("REGISTRIES_SEARCH_API_INTERNAL_URL", "")
    SEARCH_API_VERSION = os.getenv("REGISTRIES_SEARCH_API_VERSION", "")
    COLIN_API = f"{COLIN_API_URL + COLIN_API_VERSION}"
    SEARCH_API = f"{SEARCH_API_URL + SEARCH_API_VERSION}"

    BN_HUB_API_URL = os.getenv("BN_HUB_API_URL", None)
    BN_HUB_CLIENT_ID = os.getenv("BN_HUB_CLIENT_ID", None)
    BN_HUB_CLIENT_SECRET = os.getenv("BN_HUB_CLIENT_SECRET", None)
    BN_HUB_MAX_RETRY = int(os.getenv("BN_HUB_MAX_RETRY", "9"))

    GCP_AUTH_KEY = os.getenv("GCP_AUTH_KEY", None)
    ENTITY_MAILER_TOPIC = os.getenv("ENTITY_MAILER_TOPIC", "mailer")
    ENTITY_EVENT_TOPIC = os.getenv("ENTITY_EVENT_TOPIC", "event")
    AUDIENCE = os.getenv(
        "AUDIENCE", "https://pubsub.googleapis.com/google.pubsub.v1.Subscriber"
    )
    PUBLISHER_AUDIENCE = os.getenv(
        "PUBLISHER_AUDIENCE", "https://pubsub.googleapis.com/google.pubsub.v1.Publisher"
    )


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
