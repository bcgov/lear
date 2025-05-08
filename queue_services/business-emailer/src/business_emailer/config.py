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

CONFIGURATION = {
    "development": "legal_api.config.DevConfig",
    "testing": "legal_api.config.TestConfig",
    "production": "legal_api.config.ProdConfig",
    "default": "legal_api.config.ProdConfig",
}


def get_named_config(config_name: str = "production"):
    """Return the configuration object based on the name.

    :raise: KeyError: if an unknown configuration is requested
    """
    if config_name in ["production", "staging", "default"]:
        config = ProdConfig()
    elif config_name == "testing":
        config = TestConfig()
    elif config_name == "development":
        config = DevConfig()
    else:
        raise KeyError(f"Unknown configuration: {config_name}")
    return config


class Config:  # pylint: disable=too-few-public-methods
    """Base class configuration that should set reasonable defaults.

    Used as the base for all the other configurations.
    """

    # used to identify versioning flag
    SERVICE_NAME = "emailer"
    PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))

    FLASK_ENV = os.getenv("FLASK_ENV", "production")  # used for setting up flags.py

    MSG_RETRY_NUM = int(os.getenv("MSG_RETRY_NUM", "5"))

    LD_SDK_KEY = os.getenv("LD_SDK_KEY", None)

    # urls
    DASHBOARD_URL = os.getenv("DASHBOARD_URL", None)
    AUTH_WEB_URL = os.getenv("AUTH_WEB_URL", None)
    NAME_REQUEST_URL = os.getenv("NAME_REQUEST_URL", "")
    DECIDE_BUSINESS_URL = os.getenv("DECIDE_BUSINESS_URL", "")
    COLIN_URL = os.getenv("COLIN_URL", "")
    CORP_FORMS_URL = os.getenv("CORP_FORMS_URL", "")
    SOCIETIES_URL = os.getenv("SOCIETIES_URL", "")
    
    # service accounts
    ACCOUNT_SVC_AUTH_URL = os.getenv("ACCOUNT_SVC_AUTH_URL", None)
    ACCOUNT_SVC_CLIENT_ID = os.getenv("ACCOUNT_SVC_CLIENT_ID", None)
    ACCOUNT_SVC_CLIENT_SECRET = os.getenv("ACCOUNT_SVC_CLIENT_SECRET", None)
    ACCOUNT_SVC_TIMEOUT = os.getenv("ACCOUNT_SVC_TIMEOUT", "20")
    NAMEX_SVC_URL = os.getenv("ACCOUNT_SVC_AUTH_URL", None)
    NAMEX_SERVICE_CLIENT_USERNAME = os.getenv("NAMEX_SERVICE_CLIENT_USERNAME", None)
    NAMEX_SERVICE_CLIENT_SECRET = os.getenv("NAMEX_SERVICE_CLIENT_SECRET", None)

    # variables
    LEGISLATIVE_TIMEZONE = os.getenv("LEGISLATIVE_TIMEZONE", "America/Vancouver")
    TEMPLATE_PATH = os.getenv("TEMPLATE_PATH", None)

    # GCP
    SUB_AUDIENCE = os.getenv("SUB_AUDIENCE", "")
    SUB_SERVICE_ACCOUNT = os.getenv("SUB_SERVICE_ACCOUNT", "")

    # API URLs
    NAMEX_AUTH_SVC_URL = os.getenv("NAMEX_API_URL", "") + os.getenv("NAMEX_API_VERSION", "")
    NOTIFY_API_URL = os.getenv("NOTIFY_API_URL", "") + os.getenv("NOTIFY_API_VERSION", "") + "/notify/"
    LEGAL_API_URL = os.getenv("BUSINESS_API_URL", "") + os.getenv("BUSINESS_API_VERSION_2", "")
    PAY_API_URL = os.getenv("PAY_API_URL", "") + os.getenv("PAY_API_VERSION", "") + "/payment-requests"
    AUTH_URL = os.getenv("AUTH_API_URL", "") + os.getenv("AUTH_API_VERSION", "")

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


class DevConfig(Config):  # pylint: disable=too-few-public-methods
    """Creates the Development Config object."""

    TESTING = False
    DEBUG = True


class TestConfig(Config):  # pylint: disable=too-few-public-methods
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
    DEPLOYMENT_ENV = "testing"
    LEGAL_API_URL = "https://legal-api-url/"
    PAY_API_URL = "https://pay-api-url/"
    SQLALCHEMY_DATABASE_URI = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{int(DB_PORT)}/{DB_NAME}"
    TEMPLATE_PATH = os.getenv("TEMPLATE_PATH", "src/business_emailer/email_templates")
    DASHBOARD_URL = os.getenv("DASHBOARD_URL", "https://dev.bcregistry.ca/businesses/")


class ProdConfig(Config):  # pylint: disable=too-few-public-methods
    """Production environment configuration."""

    TESTING = False
    DEBUG = False
