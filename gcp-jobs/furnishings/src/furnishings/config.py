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
    SERVICE_NAME = "furnishings-job"
    PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))

    LD_SDK_KEY = os.getenv("LEAR_LD_SDK_KEY", None)

    AUTH_SVC_URL = os.getenv("AUTH_API_URL", "") + os.getenv("AUTH_API_VERSION", "")
    ACCOUNT_SVC_AUTH_URL = os.getenv("ACCOUNT_SVC_AUTH_URL", None)
    ACCOUNT_SVC_CLIENT_ID = os.getenv("ACCOUNT_SVC_CLIENT_ID", None)
    ACCOUNT_SVC_CLIENT_SECRET = os.getenv("ACCOUNT_SVC_CLIENT_SECRET", None)

    SECRET_KEY = "a secret"

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    ALEMBIC_INI = "migrations/alembic.ini"

    # POSTGRESQL
    DB_USER = os.getenv("DATABASE_USERNAME", "")
    DB_PASSWORD = os.getenv("DATABASE_PASSWORD", "")
    DB_NAME = os.getenv("DATABASE_NAME", "")
    DB_HOST = os.getenv("DATABASE_HOST", "")
    DB_PORT = os.getenv("DATABASE_PORT", "5432")
    SQLALCHEMY_DATABASE_URI = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{int(DB_PORT)}/{DB_NAME}"

    # Used to setup IapDbConnection when set. Will override ^ SQLALCHEMY_DATABASE_URI
    DB_CONNECTION_NAME = os.getenv("DATABASE_CONNECTION_NAME")  # project:region:instance-name

    # Pub/Sub
    GCP_AUTH_KEY = os.getenv("BUSINESS_GCP_AUTH_KEY", None)
    AUDIENCE = os.getenv(
        "AUDIENCE", "https://pubsub.googleapis.com/google.pubsub.v1.Subscriber"
    )
    PUBLISHER_AUDIENCE = os.getenv(
        "PUBLISHER_AUDIENCE", "https://pubsub.googleapis.com/google.pubsub.v1.Publisher"
    )
    BUSINESS_EMAILER_TOPIC = os.getenv("BUSINESS_EMAILER_TOPIC")

    # BCLaws SFTP
    BCLAWS_SFTP_STORAGE_DIRECTORY = os.getenv("BCLAWS_SFTP_STORAGE_DIRECTORY", None)
    BCLAWS_SFTP_HOST = os.getenv("BCLAWS_SFTP_HOST", None)
    BCLAWS_SFTP_PORT = os.getenv("BCLAWS_SFTP_PORT", None)
    BCLAWS_SFTP_USERNAME = os.getenv("BCLAWS_SFTP_USERNAME", None)
    BCLAWS_SFTP_PRIVATE_KEY_ALGORITHM = os.getenv("BCLAWS_SFTP_PRIVATE_KEY_ALGORITHM", "ED25519")
    BCLAWS_SFTP_PRIVATE_KEY_PASSPHRASE = os.getenv("BCLAWS_SFTP_PRIVATE_KEY_PASSPHRASE", None)
    BCLAWS_SFTP_PRIVATE_KEY = os.getenv("BCLAWS_SFTP_PRIVATE_KEY", None)

    # BCMail+ SFTP
    BCMAIL_SFTP_STORAGE_DIRECTORY = os.getenv("BCMAIL_SFTP_STORAGE_DIRECTORY", None)
    BCMAIL_SFTP_HOST = os.getenv("BCMAIL_SFTP_HOST", None)
    BCMAIL_SFTP_PORT = os.getenv("BCMAIL_SFTP_PORT", None)
    BCMAIL_SFTP_USERNAME = os.getenv("BCMAIL_SFTP_USERNAME", None)
    BCMAIL_SFTP_PRIVATE_KEY_ALGORITHM = os.getenv("BCMAIL_SFTP_PRIVATE_KEY_ALGORITHM", "RSA")
    BCMAIL_SFTP_PRIVATE_KEY_PASSPHRASE = os.getenv("BCMAIL_SFTP_PRIVATE_KEY_PASSPHRASE", None)
    BCMAIL_SFTP_PRIVATE_KEY = os.getenv("BCMAIL_SFTP_PRIVATE_KEY", None)

    TESTING = False
    DEBUG = False

    SECOND_NOTICE_DELAY = int(os.getenv("SECOND_NOTICE_DELAY", "5"))
    LEGISLATIVE_TIMEZONE = os.getenv("LEGISLATIVE_TIMEZONE", "America/Vancouver")
    XML_TEMPLATE_PATH = os.getenv("XML_TEMPLATE_PATH", "furnishings-templates")

    # Letter - GCP Gotenberg report service
    REPORT_API_GOTENBERG_AUDIENCE = os.getenv("REPORT_API_GOTENBERG_AUDIENCE", "")
    REPORT_API_GOTENBERG_URL = os.getenv("REPORT_API_GOTENBERG_URL", "https://")
    REPORT_TEMPLATE_PATH = os.getenv("REPORT_PATH", "report-templates")
    # Letter - MRAS
    MRAS_SVC_URL = os.getenv("MRAS_SVC_URL")
    MRAS_SVC_API_KEY = os.getenv("MRAS_SVC_API_KEY")


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
    DB_CONNECTION_NAME = os.getenv("LEAR_DB_CONNECTION_TEST_NAME")
    SQLALCHEMY_DATABASE_URI = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{int(DB_PORT)}/{DB_NAME}"

    # BCLaws SFTP
    BCLAWS_SFTP_STORAGE_DIRECTORY = "bclaws"
    BCLAWS_SFTP_PRIVATE_KEY = ""
    BCLAWS_SFTP_HOST = None

    # BCMail+ SFTP
    BCMAIL_SFTP_STORAGE_DIRECTORY = "bcmail"
    BCMAIL_SFTP_PRIVATE_KEY = ""
    BCMAIL_SFTP_HOST = None

    # Mocked urls
    AUTH_SVC_URL = "http://test-AUTH_URL.fake"
    ACCOUNT_SVC_AUTH_URL = "http://test-ACCOUNT_SVC_AUTH_URL.fake"
    REPORT_API_GOTENBERG_URL = "http://test-REPORT_API_GOTENBERG_URL.fake"
    MRAS_SVC_URL = "http://test-MRAS_SVC_URL.fake"


class ProductionConfig(_Config):
    """Production environment configuration."""

    SECRET_KEY = os.getenv("SECRET_KEY", None)

    if not SECRET_KEY:
        SECRET_KEY = os.urandom(24)
        print("WARNING: SECRET_KEY being set as a one-shot", file=sys.stderr)  # noqa: T201

    TESTING = False
    DEBUG = False
