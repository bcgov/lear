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

from dotenv import find_dotenv, load_dotenv

# this will load all the envars from a .env file located in the project root (api)
load_dotenv(find_dotenv())


class _Config:  # pylint: disable=too-few-public-methods
    """Base class configuration that should set reasonable defaults.

    Used as the base for all the other configurations.
    """

    SERVICE_NAME = "filer"
    PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    LD_SDK_KEY = os.getenv("LD_SDK_KEY", None)

    # POSTGRESQL
    DB_USER = os.getenv("DATABASE_USERNAME", "")
    DB_PASSWORD = os.getenv("DATABASE_PASSWORD", "")
    DB_NAME = os.getenv("DATABASE_NAME", "")
    DB_HOST = os.getenv("DATABASE_HOST", "")
    DB_PORT = os.getenv("DATABASE_PORT", "5432")
    if DB_UNIX_SOCKET := os.getenv("DATABASE_UNIX_SOCKET", None):
        SQLALCHEMY_DATABASE_URI = (
            f"postgresql+pg8000://{DB_USER}:{DB_PASSWORD}@/{DB_NAME}?unix_sock={DB_UNIX_SOCKET}/.s.PGSQL.5432"
        )
    else:
        SQLALCHEMY_DATABASE_URI = f"postgresql+pg8000://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

    COLIN_API = os.getenv("COLIN_API_URL", "") + os.getenv("COLIN_API_VERSION", "")

    # service accounts
    ACCOUNT_SVC_AUTH_URL = os.getenv("ACCOUNT_SVC_AUTH_URL")
    ACCOUNT_SVC_CLIENT_ID = os.getenv("ACCOUNT_SVC_CLIENT_ID")
    ACCOUNT_SVC_CLIENT_SECRET = os.getenv("ACCOUNT_SVC_CLIENT_SECRET")
    ACCOUNT_SVC_TIMEOUT = os.getenv("ACCOUNT_SVC_TIMEOUT")

    # API URLs
    AUTH_SVC_URL = os.getenv("AUTH_API_URL", "") + os.getenv("AUTH_API_VERSION", "")
    PAYMENT_SVC_URL = os.getenv("PAY_API_URL", "") + os.getenv("PAY_API_VERSION", "")
    NAMEX_API = os.getenv("NAMEX_API_URL", "") + os.getenv("NAMEX_API_VERSION", "")
    LEGAL_API_URL = os.getenv("BUSINESS_API_URL", "") + os.getenv("BUSINESS_API_VERSION_2", "")
    NAICS_API_URL = os.getenv("NAICS_API_URL", "") + os.getenv("NAICS_API_VERSION", "")

    ACCOUNT_SVC_ENTITY_URL = os.getenv("ACCOUNT_SVC_ENTITY_URL")
    ACCOUNT_SVC_AFFILIATE_URL = os.getenv("ACCOUNT_SVC_AFFILIATE_URL")

    # legislative timezone for future effective dating
    LEGISLATIVE_TIMEZONE = os.getenv("LEGISLATIVE_TIMEZONE", "America/Vancouver")

    # GCP Queue Configs
    GCP_AUTH_KEY = os.getenv("BUSINESS_GCP_AUTH_KEY", None)
    BUSINESS_EVENTS_TOPIC = os.getenv("BUSINESS_EVENTS_TOPIC", "business-event-dev")
    BUSINESS_MAILER_TOPIC = os.getenv("BUSINESS_MAILER_TOPIC", "business-mailer-dev")
    BUSINESS_MRAS_TOPIC = os.getenv("BUSINESS_MRAS_TOPIC", "business-mras-dev")
    BUSINESS_PAY_TOPIC = os.getenv("BUSINESS_PAY_TOPIC", "business-pay-dev")
    NAMEX_PAY_TOPIC = os.getenv("NAMEX_PAY_TOPIC", "namex-pay-dev")
    SUB_AUDIENCE = os.getenv("SUB_AUDIENCE", "")
    SUB_SERVICE_ACCOUNT = os.getenv("SUB_SERVICE_ACCOUNT", "")

    AUDIENCE = os.getenv("AUDIENCE", "https://pubsub.googleapis.com/google.pubsub.v1.Subscriber")
    PUBLISHER_AUDIENCE = os.getenv("PUBLISHER_AUDIENCE", "https://pubsub.googleapis.com/google.pubsub.v1.Publisher")


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
    DB_USER = os.getenv("DATABASE_TEST_USERNAME", "")
    DB_PASSWORD = os.getenv("DATABASE_TEST_PASSWORD", "")
    DB_NAME = os.getenv("DATABASE_TEST_NAME", "")
    DB_HOST = os.getenv("DATABASE_TEST_HOST", "")
    DB_PORT = os.getenv("DATABASE_TEST_PORT", "5432")
    SQLALCHEMY_DATABASE_URI = f"postgresql+pg8000://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

    # Minio variables
    MINIO_ENDPOINT = "localhost:9000"
    MINIO_ACCESS_KEY = "minio"
    MINIO_ACCESS_SECRET = "minio123"
    MINIO_BUCKET_BUSINESSES = "businesses"
    MINIO_SECURE = False

    NAICS_API_URL = "https://NAICS_API_URL/api/v2/naics"

    SUB_AUDIENCE = os.getenv("SUB_AUDIENCE", "test@test.test")
    SUB_SERVICE_ACCOUNT = os.getenv("SUB_SERVICE_ACCOUNT", "test@test.test")


class ProdConfig(_Config):  # pylint: disable=too-few-public-methods
    """Production environment configuration."""

    TESTING = False
    DEBUG = False
