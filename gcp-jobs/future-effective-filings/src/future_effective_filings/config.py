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

"""All of the configuration for the service is captured here.

All items are loaded, or have Constants defined here that are loaded into the Flask configuration.
All modules and lookups get their configuration from the Flask config, rather than reading environment variables
directly or by accessing this configuration directly.
"""

import os

from dotenv import find_dotenv, load_dotenv

from structured_logging import StructuredLogging

logging = StructuredLogging().get_logger()

# this will load all the envars from a .env file located in the project root (api)
load_dotenv(find_dotenv())

CONFIGURATION = {
    "development": "config.DevConfig",
    "testing": "config.TestConfig",
    "production": "config.ProdConfig",
    "default": "config.ProdConfig",
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
        raise KeyError(f"Unknown configuration '{config_name}'")
    return config


class _Config:  # pylint: disable=too-few-public-methods
    """Base class configuration that should set reasonable defaults for all the other configurations."""

    CLIENT_NAME = os.getenv("CLIENT_NAME", "entity.filing.worker")

    PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))

    LEAR_SVC_URL = os.getenv("BUSINESS_API_URL", "") + os.getenv("BUSINESS_API_VERSION_2", "")
    LEAR_SVC_TIMEOUT = int(os.getenv("LEGAL_SVC_TIMEOUT", "20"))

    ACCOUNT_SVC_AUTH_URL = os.getenv("ACCOUNT_SVC_AUTH_URL", None)
    ACCOUNT_SVC_CLIENT_ID = os.getenv("ACCOUNT_SVC_CLIENT_ID", None)
    ACCOUNT_SVC_CLIENT_SECRET = os.getenv("ACCOUNT_SVC_CLIENT_SECRET", None)
    ACCOUNT_SVC_TIMEOUT = int(os.getenv("ACCOUNT_SVC_TIMEOUT", "20"))

    # Pub/Sub
    GCP_AUTH_KEY = os.getenv("GCP_AUTH_KEY", None)
    AUDIENCE = os.getenv("AUDIENCE", "https://pubsub.googleapis.com/google.pubsub.v1.Subscriber")
    PUBLISHER_AUDIENCE = os.getenv("PUBLISHER_AUDIENCE", "https://pubsub.googleapis.com/google.pubsub.v1.Publisher")
    BUSINESS_FILER_TOPIC = os.getenv("BUSINESS_FILER_TOPIC", "")

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
    BUSINESS_FILER_TOPIC = os.getenv("BUSINESS_FILER_TOPIC_TEST", "")
    CLIENT_NAME = os.getenv("CLIENT_NAME_TEST", "entity.filing.worker.test")

    LEAR_SVC_URL = os.getenv("LEGAL_API_URL_TEST", "")
    ACCOUNT_SVC_AUTH_URL = os.getenv("KEYCLOAK_AUTH_TOKEN_TEST", "")


class ProdConfig(_Config):  # pylint: disable=too-few-public-methods
    """Production environment configuration."""

    SECRET_KEY = os.getenv("SECRET_KEY", None)

    if not SECRET_KEY:
        SECRET_KEY = os.urandom(24)
        logging.warning("SECRET_KEY being set as a one-shot")

    TESTING = False
    DEBUG = False
