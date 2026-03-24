# Copyright © 2019 Province of British Columbia.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Tests to assure the configuration objects.

Test-Suite to ensure that the Configuration Classes are working as expected.
"""
from importlib import reload
from secrets import token_hex

import pytest

from legal_api import config

# testdata pattern is ({str: environment}, {expected return value})
TEST_ENVIRONMENT_DATA = [
    ("valid", "development", config.DevConfig),
    ("valid", "testing", config.TestConfig),
    ("valid", "default", config.ProdConfig),
    ("valid", "staging", config.ProdConfig),
    ("valid", "production", config.ProdConfig),
    ("error", None, KeyError)
]

CUSTOM_JWKS_CACHE_TIMEOUT = 500
DEFAULT_JWKS_CACHE_TIMEOUT = 300


@pytest.mark.parametrize("test_type,environment,expected", TEST_ENVIRONMENT_DATA)
def test_get_named_config(test_type, environment, expected):
    """Assert that the named configurations can be loaded.

    Or that a KeyError is returned for missing config types.
    """
    if test_type == "valid":
        assert isinstance(config.get_named_config(environment), expected)
    else:
        with pytest.raises(KeyError):
            config.get_named_config(environment)


def test_prod_config_secret_key(monkeypatch):  # pylint: disable=missing-docstring
    """Assert that the ProductionConfig is correct.

    The object either uses the SECRET_KEY from the environment,
    or creates the SECRET_KEY on the fly.
    """
    key = "SECRET_KEY"

    # Assert that secret key will default to some value
    # even if missed in the environment setup
    monkeypatch.delenv(key, raising=False)
    reload(config)
    assert config.ProdConfig().SECRET_KEY is not None

    # Assert that the secret_key is set to the assigned environment value
    monkeypatch.setenv(key, "SECRET_KEY")
    reload(config)
    assert config.ProdConfig().SECRET_KEY == "SECRET_KEY"


def test_prod_config_jwks_cache(monkeypatch):  # pylint: disable=missing-docstring
    """Assert that the Config is correct.

    The object either uses the JWT_OIDC_JWKS_CACHE_TIMEOUT from the environment,
    or creates the JWT_OIDC_JWKS_CACHE_TIMEOUT defaults to 300
    """
    key = "JWT_OIDC_JWKS_CACHE_TIMEOUT"

    # Assert that secret key will default to some value
    # even if missed in the environment setup
    monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv(key, None)
    reload(config)
    assert config.ProdConfig().JWT_OIDC_JWKS_CACHE_TIMEOUT is not None

    # Assert that the secret_key is set to the assigned environment value
    monkeypatch.setenv(key, str(CUSTOM_JWKS_CACHE_TIMEOUT))
    reload(config)
    assert config.ProdConfig().JWT_OIDC_JWKS_CACHE_TIMEOUT == CUSTOM_JWKS_CACHE_TIMEOUT

    # Assert that the secret_key is set to the assigned environment value
    monkeypatch.setenv(key, "ack")
    reload(config)
    assert config.ProdConfig().JWT_OIDC_JWKS_CACHE_TIMEOUT == DEFAULT_JWKS_CACHE_TIMEOUT


def _reload_prod_config(monkeypatch, **env):
    keys_to_reset = (
        "CLOUDSQL_INSTANCE_CONNECTION_NAME",
        "DATABASE_UNIX_SOCKET",
        "DATABASE_USERNAME",
        "DATABASE_PASSWORD",
        "DATABASE_NAME",
        "DATABASE_HOST",
        "DATABASE_PORT",
    )

    for key in keys_to_reset:
        monkeypatch.delenv(key, raising=False)

    for key, value in env.items():
        monkeypatch.setenv(key, value)

    reload(config)
    return config.ProdConfig()


def test_prod_config_prefers_cloudsql_iam(monkeypatch):
    prod_config = _reload_prod_config(
        monkeypatch,
        CLOUDSQL_INSTANCE_CONNECTION_NAME="project:region:instance",
        DATABASE_USERNAME="iam-user",
        DATABASE_NAME="legal",
        DATABASE_PORT="5432",
    )

    assert prod_config.SQLALCHEMY_DATABASE_URI == "postgresql+pg8000://"
    assert callable(prod_config.SQLALCHEMY_ENGINE_OPTIONS["creator"])


def test_prod_config_falls_back_to_unix_socket(monkeypatch):
    db_password = token_hex(8)
    prod_config = _reload_prod_config(
        monkeypatch,
        DATABASE_USERNAME="user",
        DATABASE_PASSWORD=db_password,
        DATABASE_NAME="legal",
        DATABASE_UNIX_SOCKET="/cloudsql/project:region:instance",
    )
    expected_uri = f"postgresql+psycopg2://user:{db_password}@/legal?host=/cloudsql/project:region:instance"

    assert expected_uri == prod_config.SQLALCHEMY_DATABASE_URI
    assert not hasattr(prod_config, "SQLALCHEMY_ENGINE_OPTIONS")


def test_prod_config_falls_back_to_host_connection(monkeypatch):
    db_password = token_hex(8)
    prod_config = _reload_prod_config(
        monkeypatch,
        DATABASE_USERNAME="user",
        DATABASE_PASSWORD=db_password,
        DATABASE_NAME="legal",
        DATABASE_HOST="db.example",
        DATABASE_PORT="6543",
    )
    expected_uri = f"postgresql://user:{db_password}@db.example:6543/legal"

    assert expected_uri == prod_config.SQLALCHEMY_DATABASE_URI
    assert not hasattr(prod_config, "SQLALCHEMY_ENGINE_OPTIONS")
