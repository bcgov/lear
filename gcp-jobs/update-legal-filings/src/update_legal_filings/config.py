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


class _Config:  # pylint: disable=too-few-public-methods
    """Base class configuration."""

    PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))

    ENABLE_BN_UPDATES = os.getenv("ENABLE_BN_UPDATES", "True") == "True"

    COLIN_SVC_URL = os.getenv("COLIN_API_URL", "") + os.getenv("COLIN_API_VERSION", "")
    COLIN_SVC_TIMEOUT = int(os.getenv("COLIN_SVC_TIMEOUT", "20"))
    LEAR_SVC_URL = os.getenv("BUSINESS_API_URL", "") + os.getenv("BUSINESS_API_VERSION_2", "")
    LEAR_SVC_TIMEOUT = int(os.getenv("LEGAL_SVC_TIMEOUT", "20"))

    # Pub/Sub
    GCP_AUTH_KEY = os.getenv("BUSINESS_GCP_AUTH_KEY", None)
    AUDIENCE = os.getenv("AUDIENCE", "https://pubsub.googleapis.com/google.pubsub.v1.Subscriber")
    PUBLISHER_AUDIENCE = os.getenv("PUBLISHER_AUDIENCE", "https://pubsub.googleapis.com/google.pubsub.v1.Publisher")
    BUSINESS_EVENTS_TOPIC = os.getenv("BUSINESS_EVENTS_TOPIC", "business-bn")
    BUSINESS_EMAILER_TOPIC = os.getenv("BUSINESS_EMAILER_TOPIC", None)

    ACCOUNT_SVC_AUTH_URL = os.getenv("ACCOUNT_SVC_AUTH_URL", None)
    ACCOUNT_SVC_CLIENT_ID = os.getenv("ACCOUNT_SVC_CLIENT_ID", None)
    ACCOUNT_SVC_CLIENT_SECRET = os.getenv("ACCOUNT_SVC_CLIENT_SECRET", None)
    ACCOUNT_SVC_TIMEOUT = os.getenv("ACCOUNT_SVC_TIMEOUT", "20")

    SECRET_KEY = "a secret"

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

    COLIN_SVC_URL = os.getenv("COLIN_URL_TEST", "https://fake-colin-url.com")
    LEAR_SVC_URL = os.getenv("LEGAL_API_URL_TEST", "https://fake-legal-api-url.com")

    BUSINESS_EMAILER_TOPIC = "fake-emailer-topic"
    BUSINESS_EVENTS_TOPIC = "fake-events-topic"


class ProdConfig(_Config):  # pylint: disable=too-few-public-methods
    """Production environment configuration."""

    SECRET_KEY = os.getenv("SECRET_KEY", None)

    if not SECRET_KEY:
        SECRET_KEY = os.urandom(24)
        print("WARNING: SECRET_KEY being set as a one-shot", file=sys.stderr)

    TESTING = False
    DEBUG = False
