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


class _Config:
    """Base class configuration."""

    # used to identify versioning flag
    SERVICE_NAME = "emailer-reminder-job"

    SEND_OUTSTANDING_BCOMPS = os.getenv("SEND_OUTSTANDING_BCOMPS", None)
    LD_SDK_KEY = os.getenv("LEAR_LD_SDK_KEY", None)

    # service account
    ACCOUNT_SVC_AUTH_URL = os.getenv("ACCOUNT_SVC_AUTH_URL", None)
    ACCOUNT_SVC_CLIENT_ID = os.getenv("ACCOUNT_SVC_CLIENT_ID", None)
    ACCOUNT_SVC_CLIENT_SECRET = os.getenv("ACCOUNT_SVC_CLIENT_SECRET", None)
    ACCOUNT_SVC_TIMEOUT = os.getenv("ACCOUNT_SVC_TIMEOUT", "20")

    PAY_API_URL = os.getenv("PAY_API_URL", "")
    PAY_API_VERSION = os.getenv("PAY_API_VERSION", "")
    PAYMENT_SVC_FEES_URL = PAY_API_URL + PAY_API_VERSION + "/fees"

    # Pub/Sub
    GCP_AUTH_KEY = os.getenv("BUSINESS_GCP_AUTH_KEY", None)
    AUDIENCE = os.getenv("AUDIENCE", "https://pubsub.googleapis.com/google.pubsub.v1.Subscriber")
    PUBLISHER_AUDIENCE = os.getenv("PUBLISHER_AUDIENCE", "https://pubsub.googleapis.com/google.pubsub.v1.Publisher")
    BUSINESS_EMAILER_TOPIC = os.getenv("BUSINESS_EMAILER_TOPIC")

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
        SQLALCHEMY_DATABASE_URI = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@/{DB_NAME}?host={DB_UNIX_SOCKET}"
    else:
        SQLALCHEMY_DATABASE_URI = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

    TESTING = False
    DEBUG = False


class DevelopmentConfig(_Config):
    """Development environment configuration."""

    TESTING = False
    DEBUG = True


class UnitTestingConfig(_Config):
    """In support of testing only used by the py.test suite."""

    DEBUG = True
    TESTING = True

    # POSTGRESQL
    DB_USER = os.getenv("DATABASE_TEST_USERNAME", "")
    DB_PASSWORD = os.getenv("DATABASE_TEST_PASSWORD", "")
    DB_NAME = os.getenv("DATABASE_TEST_NAME", "")
    DB_HOST = os.getenv("DATABASE_TEST_HOST", "")
    DB_PORT = os.getenv("DATABASE_TEST_PORT", "5432")
    SQLALCHEMY_DATABASE_URI = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{int(DB_PORT)}/{DB_NAME}"

    PAYMENT_SVC_FEES_URL = "http://test.PAY_API_URL.fake/fees"
    GCP_AUTH_KEY = None


class ProductionConfig(_Config):
    """Production environment configuration."""

    SECRET_KEY = os.getenv("SECRET_KEY", None)

    if not SECRET_KEY:
        SECRET_KEY = os.urandom(24)
        print("WARNING: SECRET_KEY being set as a one-shot", file=sys.stderr)

    TESTING = False
    DEBUG = False
