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

import pytest

from entity_filer import config


# testdata pattern is ({str: environment}, {expected return value})
TEST_ENVIRONMENT_DATA = [
    ('valid', 'development', config.DevConfig),
    ('valid', 'testing', config.TestConfig),
    ('valid', 'default', config.ProdConfig),
    ('valid', 'staging', config.ProdConfig),
    ('valid', 'production', config.ProdConfig),
    ('error', None, KeyError)
]


@pytest.mark.parametrize('test_type,environment,expected', TEST_ENVIRONMENT_DATA)
def test_get_named_config(test_type, environment, expected):
    """Assert that the named configurations can be loaded.

    Or that a KeyError is returned for missing config types.
    """
    if test_type == 'valid':
        assert isinstance(config.get_named_config(environment), expected)
    else:
        with pytest.raises(KeyError):
            config.get_named_config(environment)


def test_config_dsn_key():
    """Assert that the ProductionConfig is correct.

    The object either uses the SENTRY_DSN from the environment
    and initializes Sentry, or it doesn't.
    """
    from flask import Flask
    from entity_filer.config import get_named_config
    config._Config.SENTRY_DSN = None  # pylint: disable=protected-access; for whitebox testing
    app = Flask(__name__)
    app.config.from_object(get_named_config('production'))
    assert app.config.get('SENTRY_DSN') is None

    # Assert that the SENTRY_DSN is set to the assigned environment value
    dsn = 'http://secret_key@localhost:9000/project_id'
    config._Config.SENTRY_DSN = dsn  # pylint: disable=protected-access; for whitebox testing
    reload(config)
    app = Flask(__name__)
    app.config.from_object(get_named_config('production'))
    assert app.config.get('SENTRY_DSN') is not None
