# Copyright © 2025 Province of British Columbia
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

"""All of the configuration for the service is captured here.

All items are loaded, or have Constants defined here that are loaded into the Flask configuration.
All modules and lookups get their configuration from the Flask config, rather than reading environment variables
directly or by accessing this configuration directly.
"""

import os
import sys

from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv())


class _Config:  # pylint: disable=too-few-public-methods
    """Base class configuration that should set reasonable defaults for all the other configurations."""

    PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))

    LEAR_SVC_URL = os.getenv("BUSINESS_API_URL", "") + os.getenv("BUSINESS_API_VERSION_2", "")
    LEAR_SVC_TIMEOUT = int(os.getenv("LEGAL_SVC_TIMEOUT", "20"))

    ACCOUNT_SVC_AUTH_URL = os.getenv("ACCOUNT_SVC_AUTH_URL", None)
    ACCOUNT_SVC_CLIENT_ID = os.getenv("ACCOUNT_SVC_CLIENT_ID", None)
    ACCOUNT_SVC_CLIENT_SECRET = os.getenv("ACCOUNT_SVC_CLIENT_SECRET", None)
    ACCOUNT_SVC_TIMEOUT = os.getenv("ACCOUNT_SVC_TIMEOUT", "20")

    SECRET_KEY = "a secret"

    TESTING = False
    DEBUG = False


class DevConfig(_Config):  # pylint: disable=too-few-public-methods
    """Config for local development."""

    TESTING = False
    DEBUG = True


class TestConfig(_Config):  # pylint: disable=too-few-public-methods
    """In support of testing only used by the py.test suite."""

    DEBUG = True
    TESTING = True

    LEAR_SVC_URL = os.getenv("LEGAL_API_URL_TEST", "")


class ProdConfig(_Config):  # pylint: disable=too-few-public-methods
    """Production environment configuration."""

    SECRET_KEY = os.getenv("SECRET_KEY", None)

    if not SECRET_KEY:
        SECRET_KEY = os.urandom(24)
        print("WARNING: SECRET_KEY being set as a one-shot", file=sys.stderr)  # noqa: T201

    TESTING = False
    DEBUG = False
