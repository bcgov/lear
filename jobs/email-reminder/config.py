# Copyright © 2021 Province of British Columbia
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
"""All of the configuration for the service is captured here."""

import os
import sys

from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv())

CONFIGURATION = {
    "development": "config.DevConfig",
    "testing": "config.TestConfig",
    "production": "config.ProdConfig",
    "default": "config.ProdConfig",
}


class _Config:  # pylint: disable=too-few-public-methods
    """Base class configuration."""

    PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))

    SEND_OUTSTANDING_BCOMPS = os.getenv("SEND_OUTSTANDING_BCOMPS", None)
    SENTRY_DSN = os.getenv("SENTRY_DSN", "")
    LD_SDK_KEY = os.getenv("LD_SDK_KEY", None)

    ACCOUNT_SVC_AUTH_URL = os.getenv("ACCOUNT_SVC_AUTH_URL", None)
    ACCOUNT_SVC_CLIENT_ID = os.getenv("ACCOUNT_SVC_CLIENT_ID", None)
    ACCOUNT_SVC_CLIENT_SECRET = os.getenv("ACCOUNT_SVC_CLIENT_SECRET", None)

    PAYMENT_SVC_FEES_URL = os.getenv("PAYMENT_SVC_FEES_URL", None)

    SECRET_KEY = "a secret"

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    ALEMBIC_INI = "migrations/alembic.ini"

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

    ENVIRONMENT = os.getenv("ENVIRONMENT", "prod")

    GCP_AUTH_KEY = os.getenv("GCP_AUTH_KEY", None)
    ENTITY_MAILER_TOPIC = os.getenv("ENTITY_MAILER_TOPIC", "mailer")
    AUDIENCE = os.getenv("AUDIENCE", "https://pubsub.googleapis.com/google.pubsub.v1.Subscriber")
    PUBLISHER_AUDIENCE = os.getenv("PUBLISHER_AUDIENCE", "https://pubsub.googleapis.com/google.pubsub.v1.Publisher")

    TESTING = False
    DEBUG = False


class DevConfig(_Config):  # pylint: disable=too-few-public-methods
    """Development environment configuration."""

    TESTING = False
    DEBUG = True


class TestConfig(_Config):  # pylint: disable=too-few-public-methods
    """In support of testing only used by the py.test suite."""

    DEBUG = True
    TESTING = True

    # POSTGRESQL
    DB_USER = os.getenv("DATABASE_TEST_USERNAME", "")
    DB_PASSWORD = os.getenv("DATABASE_TEST_PASSWORD", "")
    DB_NAME = os.getenv("DATABASE_TEST_NAME", "")
    DB_HOST = os.getenv("DATABASE_TEST_HOST", "")
    DB_PORT = os.getenv("DATABASE_TEST_PORT", "5432")
    SQLALCHEMY_DATABASE_URI = f"postgresql+pg8000://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{int(DB_PORT)}/{DB_NAME}"


class ProdConfig(_Config):  # pylint: disable=too-few-public-methods
    """Production environment configuration."""

    SECRET_KEY = os.getenv("SECRET_KEY", None)

    if not SECRET_KEY:
        SECRET_KEY = os.urandom(24)
        print("WARNING: SECRET_KEY being set as a one-shot", file=sys.stderr)

    TESTING = False
    DEBUG = False
