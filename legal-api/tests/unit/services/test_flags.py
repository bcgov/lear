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
"""Tests to assure the Flag Services.

Test-Suite to ensure that the Flag Service is working as expected.
"""
import pytest
from flask import Flask

from legal_api.models import User
from legal_api.services import Flags


def test_flags_init():
    """Ensure that extension can be initialized."""
    app = Flask(__name__)

    with app.app_context():
        flags = Flags()

    assert flags
    assert 'featureflags' not in app.extensions


def test_flags_init_app(ld):
    """Ensure that extension can be initialized."""
    app = Flask(__name__)

    with app.app_context():
        flags = Flags()
        flags.init_app(app, ld)
    assert app.extensions['featureflags']


def test_flags_init_app_no_key_prod():
    """Assert that prod with no key initializes, but does not setup the extension."""
    app = Flask(__name__)
    app.config['LD_SDK_KEY'] = None

    with app.app_context():
        flags = Flags()
        flags.init_app(app)
        with pytest.raises(KeyError):
            client = app.extensions['featureflags']
            assert not client


def test_flags_bool_no_key_prod():
    """Assert that prod with no key initializes, but does not setup the extension."""
    app = Flask(__name__)
    app.config['LD_SDK_KEY'] = None

    with app.app_context():
        flags = Flags()
        flags.init_app(app)
        on = flags.is_on('bool-flag')

    assert not on


def test_flags_bool(ld):
    """Assert that a boolean (True) is returned, when using the local Flag.json file."""
    app = Flask(__name__)
    app.config['LD_SDK_KEY'] = 'https://no.flag/avail'

    with app.app_context():
        flags = Flags()
        flags.init_app(app, ld)
        flag_on = flags.is_on('bool-flag')

        assert flag_on


def test_flags_bool_missing_flag(app):
    """Assert that a boolean (False) is returned when flag doesn't exist, when using the local Flag.json file."""
    from legal_api import flags
    app_env = app.env
    try:
        with app.app_context():
            flag_on = flags.is_on('no flag here')

        assert not flag_on
    except:  # pylint: disable=bare-except; # noqa: B901, E722
        # for tests we don't care
        assert False
    finally:
        app.env = app_env


@pytest.mark.parametrize('test_name,flag_name,expected', [
    ('boolean flag', 'bool-flag', True),
    ('string flag', 'string-flag', 'a string value'),
    ('integer flag', 'integer-flag', 10),
])
def test_flags_bool_value(app, test_name, flag_name, expected):
    """Assert that a boolean (True) is returned, when using the local Flag.json file."""
    from legal_api import flags

    with app.app_context():
        val = flags.value(flag_name)

    assert val == expected


def test_flag_bool_unique_user(ld):
    """Assert that a unique user can retrieve a flag, when using the local Flag.json file."""
    app = Flask(__name__)
    app.config['LD_SDK_KEY'] = 'https://no.flag/avail'

    user = User(username='username', firstname='firstname', lastname='lastname', sub='sub', iss='iss', idp_userid='123', login_source='IDIR')

    app_env = app.env
    try:
        with app.app_context():
            flags = Flags()
            flags.init_app(app, ld)
            val = flags.value('bool-flag', user)
            flag_on = flags.is_on('bool-flag', user)

        assert val
        assert flag_on
    except:  # pylint: disable=bare-except; # noqa: B901, E722
        # for tests we don't care
        assert False
    finally:
        app.env = app_env


def test_flags_is_on_client_none():
    """Assert that is_on returns False when client is None."""
    app = Flask(__name__)

    with app.app_context():
        flags = Flags()
        # Don't init_app, so client is None
        result = flags.is_on('test-flag')
        assert result is False


def test_flags_value_client_none():
    """Assert that value returns None when client is None."""
    app = Flask(__name__)

    with app.app_context():
        flags = Flags()
        # Don't init_app, so client is None
        result = flags.value('test-flag')
        assert result is None


def test_flags_is_on_client_not_initialized(ld):
    """Assert that is_on returns False when client is not initialized."""
    from unittest.mock import patch

    app = Flask(__name__)

    with app.app_context():
        flags = Flags()
        flags.init_app(app, ld)
        # Mock client.is_initialized to return False
        with patch.object(app.extensions['featureflags'], 'is_initialized', return_value=False):
            result = flags.is_on('test-flag')
            assert result is False


def test_flags_value_client_not_initialized(ld):
    """Assert that value returns None when client is not initialized."""
    from unittest.mock import patch

    app = Flask(__name__)

    with app.app_context():
        flags = Flags()
        flags.init_app(app, ld)
        # Mock client.is_initialized to return False
        with patch.object(app.extensions['featureflags'], 'is_initialized', return_value=False):
            result = flags.value('test-flag')
            assert result is None


def test_flags_value_error_returns_none(ld):
    """Assert that value returns None on exception, not False."""
    from unittest.mock import patch

    app = Flask(__name__)

    with app.app_context():
        flags = Flags()
        flags.init_app(app, ld)
        # Mock client.variation to raise an exception
        with patch.object(app.extensions['featureflags'], 'variation', side_effect=Exception('test error')):
            result = flags.value('test-flag')
            assert result is None
