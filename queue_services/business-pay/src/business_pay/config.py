# Copyright © 2024 Province of British Columbia
#
# Licensed under the BSD 3 Clause License, (the "License");
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
import random

from dotenv import find_dotenv, load_dotenv

# this will load all the envars from a .env file located in the project root (api)
load_dotenv(find_dotenv())

CONFIGURATION = {
    "development": "business_pay.config.DevConfig",
    "testing": "business_pay.config.TestConfig",
    "production": "business_pay.config.ProdConfig",
    "default": "business_pay.config.ProdConfig",
}


def get_named_config(config_name: str = "production"):
    """Return the configuration object based on the name.

    :raise: KeyError: if an unknown configuration is requested
    """
    if config_name in ["production", "staging", "default"]:
        app_config = ProdConfig()
    elif config_name == "testing":
        app_config = TestConfig()
    elif config_name == "development":
        app_config = DevConfig()
    else:
        raise KeyError(f"Unknown configuration: {config_name}")
    return app_config


class Config:  # pylint: disable=too-few-public-methods
    """Base class configuration that should set reasonable defaults.

    Used as the base for all the other configurations.
    """

    PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))

    SENTRY_DSN = os.getenv("SENTRY_DSN") or ""
    SENTRY_DSN = "" if SENTRY_DSN.lower() == "null" else SENTRY_DSN
    
    DEPLOYMENT_PLATFORM = os.getenv("DEPLOYMENT_PLATFORM", "OCP")

    LD_SDK_KEY = os.getenv("LD_SDK_KEY", None)

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # POSTGRESQL
    DB_USER = os.getenv("DATABASE_USERNAME", "")
    DB_PASSWORD = os.getenv("DATABASE_PASSWORD", "")
    DB_NAME = os.getenv("DATABASE_NAME", "")
    DB_HOST = os.getenv("DATABASE_HOST", "")
    DB_PORT = os.getenv("DATABASE_PORT", "5432")
    # POSTGRESQL
    if DB_UNIX_SOCKET := os.getenv("DATABASE_UNIX_SOCKET", None):
        SQLALCHEMY_DATABASE_URI = f"postgresql+pg8000://{DB_USER}:{DB_PASSWORD}@/{DB_NAME}?unix_sock={DB_UNIX_SOCKET}/.s.PGSQL.5432"
    else:
        SQLALCHEMY_DATABASE_URI = (
            f"postgresql+pg8000://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
        )

    NATS_SERVERS = os.getenv("NATS_SERVERS", "nats://127.0.0.1:4222,").split(",")
    NATS_CLIENT_NAME = os.getenv("NATS_CLIENT_NAME", "entity.filing.worker")
    NATS_CLUSTER_ID = os.getenv("NATS_CLUSTER_ID", "test-cluster")
    NATS_QUEUE = os.getenv("NATS_QUEUE", "filing-worker")
    NATS_FILER_SUBJECT = os.getenv("NATS_FILER_SUBJECT", "entity.filing.filer")
    NATS_EMAILER_SUBJECT = os.getenv("NATS_EMAILER_SUBJECT", "entity.email")

    NATS_CONNECTION_OPTIONS = {
        "servers": os.getenv("NATS_SERVERS", "nats://127.0.0.1:4222").split(","),
        "name": os.getenv("NATS_CLIENT_NAME", "entity.filing.worker"),
    }
    STAN_CONNECTION_OPTIONS = {
        "cluster_id": os.getenv("NATS_CLUSTER_ID", "test-cluster"),
        "client_id": str(random.SystemRandom().getrandbits(0x58)),
        "ping_interval": 1,
        "ping_max_out": 5,
    }

    SUBSCRIPTION_OPTIONS = {
        "subject": os.getenv("NATS_SUBJECT", "entity.filings"),
        "queue": os.getenv("NATS_QUEUE", "filing-worker"),
        "durable_name": os.getenv("NATS_QUEUE", "filing-worker") + "_durable",
    }

    FILER_PUBLISH_OPTIONS = {
        "subject": os.getenv("NATS_FILER_SUBJECT", "entity.filing.filer"),
    }

    EMAIL_PUBLISH_OPTIONS = {
        "subject": os.getenv("NATS_EMAILER_SUBJECT", "entity.email"),
    }

    ENVIRONMENT = os.getenv("DEPLOYMENT_ENV", "production")

    # Pub/Sub
    GCP_AUTH_KEY = os.getenv("GCP_AUTH_KEY", None)
    AUDIENCE = os.getenv(
        "AUDIENCE", "https://pubsub.googleapis.com/google.pubsub.v1.Subscriber"
    )
    PUBLISHER_AUDIENCE = os.getenv(
        "PUBLISHER_AUDIENCE", "https://pubsub.googleapis.com/google.pubsub.v1.Publisher"
    )
    SUB_AUDIENCE = os.getenv("SUB_AUDIENCE", "")
    SUB_SERVICE_ACCOUNT = os.getenv("SUB_SERVICE_ACCOUNT", "")
    SBC_CONNECT_GCP_QUEUE_DEBUG = os.getenv("SBC_CONNECT_GCP_QUEUE_DEBUG", "")
    BUSINESS_FILER_TOPIC = os.getenv("BUSINESS_FILER_TOPIC", "business-filer")

    NATS_CONNECT_ERROR_COUNT_MAX = os.getenv("NATS_CONNECT_ERROR_COUNT_MAX", 10)


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
    DATABASE_TEST_NAME = os.getenv("DATABASE_TEST_NAME", "")
    DB_USER = os.getenv("DATABASE_TEST_USERNAME", "")
    DB_PASSWORD = os.getenv("DATABASE_TEST_PASSWORD", "")
    DB_NAME = os.getenv("DATABASE_TEST_NAME", "")
    DB_HOST = os.getenv("DATABASE_TEST_HOST", "")
    DB_PORT = os.getenv("DATABASE_TEST_PORT", "5432")
    # POSTGRESQL
    if DB_UNIX_SOCKET := os.getenv("DATABASE_UNIX_SOCKET", None):
        SQLALCHEMY_DATABASE_URI = f"postgresql+pg8000://{DB_USER}:{DB_PASSWORD}@/{DB_NAME}?unix_sock={DB_UNIX_SOCKET}/.s.PGSQL.5432"
    else:
        SQLALCHEMY_DATABASE_URI = (
            f"postgresql+pg8000://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
        )


class ProdConfig(Config):  # pylint: disable=too-few-public-methods
    """Production environment configuration."""

    TESTING = False
    DEBUG = False
