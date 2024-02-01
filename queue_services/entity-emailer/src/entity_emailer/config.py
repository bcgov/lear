# Copyright © 2023 Province of British Columbia
#
# Licensed under the BSD 3 Clause License, (the 'License');
# you may not use this file except in compliance with the License.
# The template for the license can be found here
#    https://opensource.org/license/bsd-3-clause/
#
# Redistribution and use in source and binary forms,
# with or without modification, are permitted provided that the
# following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
# 3. Neither the name of the copyright holder nor the names of its contributors
#    may be used to endorse or promote products derived from this software
#    without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS “AS IS”
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
# THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
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


def get_named_config(config_name: str = "production"):
    """Return the configuration object based on the name.

    :raise: KeyError: if an unknown configuration is requested
    """
    if config_name in ["production", "staging", "default"]:
        config = Production()
    elif config_name == "testing":
        config = Testing()
    elif config_name == "development":
        config = Development()
    else:
        raise KeyError(f"Unknown configuration: {config_name}")
    return config


class Config:  # pylint: disable=too-few-public-methods
    """Base class configuration that should set reasonable defaults.

    Used as the base for all the other configurations.
    """

    PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))

    ENVIRONMENT = os.getenv("APP_ENV", "prod")

    LD_SDK_KEY = os.getenv("LD_SDK_KEY", None)

    SENTRY_DSN = os.getenv("SENTRY_DSN", None)

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # POSTGRESQL
    DB_USER = os.getenv("DATABASE_USERNAME", "")
    DB_PASSWORD = os.getenv("DATABASE_PASSWORD", "")
    DB_NAME = os.getenv("DATABASE_NAME", "")
    DB_HOST = os.getenv("DATABASE_HOST", "")
    DB_PORT = os.getenv("DATABASE_PORT", "5432")

    # POSTGRESQL
    if DB_UNIX_SOCKET := os.getenv("DATABASE_UNIX_SOCKET", None):
        SQLALCHEMY_DATABASE_URI = (
            f"postgresql+pg8000://{DB_USER}:{DB_PASSWORD}@/{DB_NAME}?unix_sock={DB_UNIX_SOCKET}/.s.PGSQL.5432"
        )
    else:
        SQLALCHEMY_DATABASE_URI = f"postgresql+pg8000://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

    # variables
    LEGISLATIVE_TIMEZONE = os.getenv("LEGISLATIVE_TIMEZONE", "America/Vancouver")
    MSG_RETRY_NUM = int(os.getenv("MSG_RETRY_NUM", "5"))
    TEMPLATE_PATH = os.getenv("TEMPLATE_PATH", None)
    DASHBOARD_URL = os.getenv("DASHBOARD_URL", None)
    LOG_LEVEL = os.getenv("LOG_LEVEL", None)

    # API Endpoints
    AUTH_API_URL = os.getenv("AUTH_API_URL", "")
    AUTH_API_VERSION = os.getenv("AUTH_API_VERSION", "")
    NOTIFY_API_URL = os.getenv("NOTIFY_API_URL", "")
    NOTIFY_API_VERSION = os.getenv("NOTIFY_API_VERSION", "")
    BUSINESS_API_URL = os.getenv("BUSINESS_API_URL", "")
    BUSINESS_API_VERSION_2 = os.getenv("BUSINESS_API_VERSION2", "")
    NAMEX_API_URL = os.getenv("NAMEX_API_URL", "")
    NAMEX_API_VERSION = os.getenv("NAMEX_API_VERSION", "")
    PAY_API_URL = os.getenv("PAY_API_URL", "")
    PAY_API_VERSION = os.getenv("PAY_API_VERSION", "")

    LEGAL_API_URL = f"{BUSINESS_API_URL + BUSINESS_API_VERSION_2}"
    NOTIFY_API_URL = f"{NOTIFY_API_URL + AUTH_API_VERSION}/notify/"
    NAMEX_SVC_URL = f"{NAMEX_API_URL + NAMEX_API_VERSION}"
    PAY_API_URL = f"{PAY_API_URL + PAY_API_VERSION}/payment-request"
    AUTH_URL = f"{AUTH_API_URL + AUTH_API_VERSION}"

    # service accounts
    ACCOUNT_SVC_AUTH_URL = os.getenv("KEYCLOAK_AUTH_TOKEN_URL")
    ACCOUNT_SVC_CLIENT_ID = os.getenv("KEYCLOAK_CLIENT_ID")
    ACCOUNT_SVC_CLIENT_SECRET = os.getenv("KEYCLOAK_CLIENT_ID")
    ACCOUNT_SVC_TIMEOUT = os.getenv("KEYCLOAK_TIMEOUT")
    NAMEX_AUTH_SVC_URL = os.getenv("KEYCLOAK_AUTH_TOKEN_URL")
    NAMEX_SERVICE_CLIENT_USERNAME = os.getenv("KEYCLOAK_CLIENT_ID")
    NAMEX_SERVICE_CLIENT_SECRET = os.getenv("KEYCLOAK_CLIENT_ID")

    GCP_AUTH_KEY = os.getenv("GCP_AUTH_KEY", None)
    AUDIENCE = os.getenv("AUDIENCE", "https://pubsub.googleapis.com/google.pubsub.v1.Subscriber")
    PUBLISHER_AUDIENCE = os.getenv("PUBLISHER_AUDIENCE", "https://pubsub.googleapis.com/google.pubsub.v1.Publisher")

    NAME_REQUEST_URL = os.getenv("NAME_REQUEST_URL", "")
    DECIDE_BUSINESS_URL = os.getenv("DECIDE_BUSINESS_URL", "")
    COLIN_URL = os.getenv("COLIN_URL", "")
    CORP_FORMS_URL = os.getenv("CORP_FORMS_URL", "")
    SOCIETIES_URL = os.getenv("SOCIETIES_URL", "")


class Development(Config):  # pylint: disable=too-few-public-methods
    """Creates the Development Config object."""

    TESTING = False
    DEBUG = True


class Testing(Config):  # pylint: disable=too-few-public-methods
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
    SQLALCHEMY_DATABASE_URI = f"postgresql+pg8000://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"


class Production(Config):  # pylint: disable=too-few-public-methods
    """Production environment configuration."""

    TESTING = False
    DEBUG = False
