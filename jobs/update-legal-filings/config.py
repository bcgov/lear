# Copyright © 2019 Province of British Columbia
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

    SECRET_KEY = "a secret"

    SENTRY_DSN = os.getenv("SENTRY_DSN", "")

    # API Endpoints
    BUSINESS_API_URL = os.getenv("BUSINESS_API_URL", "")
    BUSINESS_API_VERSION_2 = os.getenv("BUSINESS_API_VERSION2", "")
    COLIN_API_URL = os.getenv("COLIN_API_URL", "")
    COLIN_API_VERSION = os.getenv("COLIN_API_VERSION", "")

    COLIN_API = f"{COLIN_API_URL + COLIN_API_VERSION}"
    LEGAL_URL = f"{BUSINESS_API_URL + BUSINESS_API_VERSION_2}"

    # service accounts
    ACCOUNT_SVC_AUTH_URL = os.getenv("KEYCLOAK_AUTH_TOKEN_URL")
    ACCOUNT_SVC_CLIENT_ID = os.getenv("KEYCLOAK_CLIENT_ID")
    ACCOUNT_SVC_CLIENT_SECRET = os.getenv("KEYCLOAK_CLIENT_ID")
    ACCOUNT_SVC_TIMEOUT = os.getenv("KEYCLOAK_TIMEOUT")

    # GCP QUEUE
    GCP_AUTH_KEY = os.getenv("GCP_AUTH_KEY", None)
    ENTITY_MAILER_TOPIC = os.getenv("ENTITY_MAILER_TOPIC", "mailer")
    ENTITY_EVENTS_TOPIC = os.getenv("ENTITY_EVENTS_TOPIC", "events")
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

    COLIN_URL = os.getenv("COLIN_URL_TEST", "")
    LEGAL_URL = os.getenv("LEGAL_URL_TEST", "")


class ProdConfig(_Config):  # pylint: disable=too-few-public-methods
    """Production environment configuration."""

    SECRET_KEY = os.getenv("SECRET_KEY", None)

    if not SECRET_KEY:
        SECRET_KEY = os.urandom(24)
        print("WARNING: SECRET_KEY being set as a one-shot", file=sys.stderr)

    TESTING = False
    DEBUG = False
