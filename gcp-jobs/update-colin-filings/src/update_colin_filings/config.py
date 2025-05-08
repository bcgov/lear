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


class _Config:
    """Base class configuration."""

    PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))

    JOB_TOTAL_LIMIT = int(os.getenv("JOB_TOTAL_LIMIT", "500"))
    JOB_BATCH_LIMIT = int(os.getenv("JOB_BATCH_LIMIT", "50"))

    COLIN_SVC_URL = os.getenv("COLIN_API_URL", "") + os.getenv("COLIN_API_VERSION", "")
    COLIN_SVC_TIMEOUT = int(os.getenv("COLIN_SVC_TIMEOUT", "20"))
    LEAR_SVC_URL = os.getenv("BUSINESS_API_URL", "") + os.getenv("BUSINESS_API_VERSION_2", "")
    LEAR_SVC_TIMEOUT = int(os.getenv("LEGAL_SVC_TIMEOUT", "20"))

    ACCOUNT_SVC_AUTH_URL = os.getenv("ACCOUNT_SVC_AUTH_URL", None)
    ACCOUNT_SVC_CLIENT_ID = os.getenv("ACCOUNT_SVC_CLIENT_ID", None)
    ACCOUNT_SVC_CLIENT_SECRET = os.getenv("ACCOUNT_SVC_CLIENT_SECRET", None)
    ACCOUNT_SVC_TIMEOUT = int(os.getenv("ACCOUNT_SVC_TIMEOUT", "20"))

    SECRET_KEY = "a secret"

    TESTING = False
    DEBUG = False


class DevelopmentConfig(_Config):  # pylint: disable=too-few-public-methods
    """Development environment configuration."""

    TESTING = False
    DEBUG = True


class UnitTestingConfig(_Config):
    """In support of testing only used by the py.test suite."""

    DEBUG = True
    TESTING = True

    JOB_TOTAL_LIMIT = 1
    ACCOUNT_SVC_AUTH_URL = "http://test-token-url.com"
    COLIN_SVC_URL = "http://test-colin-url.com"
    LEAR_SVC_URL = "http://test-lear-url.com"


class ProductionConfig(_Config):
    """Production environment configuration."""

    SECRET_KEY = os.getenv("SECRET_KEY", None)

    if not SECRET_KEY:
        SECRET_KEY = os.urandom(24)
        print("WARNING: SECRET_KEY being set as a one-shot", file=sys.stderr)

    TESTING = False
    DEBUG = False
