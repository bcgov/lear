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


def get_named_config(config_name: str = "production"):
    """Return the configuration object based on the name."""
    if config_name in ["production", "staging", "default"]:
        config = ProdConfig()
    elif config_name == "testing":
        config = TestConfig()
    elif config_name == "development":
        config = DevConfig()
    else:
        raise KeyError(f"Unknown configuration '{config_name}'")
    return config


class _Config:  # pylint: disable=too-few-public-methods
    """Base class configuration."""

    PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))

    SECRET_KEY = "a secret"

    SENTRY_DSN = os.getenv("SENTRY_DSN", "")

    # API Endpoints
    BUSINESS_API_URL = os.getenv("BUSINESS_API_URL", "")
    BUSINESS_API_VERSION_2 = os.getenv("BUSINESS_API_VERSION_2", "")
    COLIN_API_URL = os.getenv("COLIN_API_URL", "")
    COLIN_API_VERSION = os.getenv("COLIN_API_VERSION", "")

    COLIN_API = f"{COLIN_API_URL + COLIN_API_VERSION}"
    LEGAL_URL = f"{BUSINESS_API_URL + BUSINESS_API_VERSION_2}"

    # service accounts
    ACCOUNT_SVC_AUTH_URL = os.getenv("ACCOUNT_SVC_AUTH_URL")
    ACCOUNT_SVC_CLIENT_ID = os.getenv("ACCOUNT_SVC_CLIENT_ID")
    ACCOUNT_SVC_CLIENT_SECRET = os.getenv("ACCOUNT_SVC_CLIENT_SECRET")
    ACCOUNT_SVC_TIMEOUT = os.getenv("KEYCLOAK_TIMEOUT")

    PAYMENT_SVC_FEES_URL = os.getenv("PAYMENT_SVC_FEES_URL", None)

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
