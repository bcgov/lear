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
        flags = Flags(app)

    assert flags
    assert app.extensions['featureflags']


def test_flags_init_app():
    """Ensure that extension can be initialized."""
    app = Flask(__name__)
    app.config['LD_SDK_KEY'] = 'https://no.flag/avail'

    with app.app_context():
        flags = Flags()
        flags.init_app(app)
    assert app.extensions['featureflags']


def test_flags_init_app_production():
    """Ensure that extension can be initialized."""
    app = Flask(__name__)
    app.env = 'production'
    app.config['LD_SDK_KEY'] = 'https://no.flag/avail'

    with app.app_context():
        flags = Flags()
        flags.init_app(app)
    assert app.extensions['featureflags']


def test_flags_init_app_no_key_dev():
    """Assert that the extension is setup with a KEY, but in non-production mode."""
    app = Flask(__name__)
    app.config['LD_SDK_KEY'] = None
    app.env = 'development'

    with app.app_context():
        flags = Flags()
        flags.init_app(app)
    assert app.extensions['featureflags']


def test_flags_init_app_no_key_prod():
    """Assert that prod with no key initializes, but does not setup the extension."""
    app = Flask(__name__)
    app.config['LD_SDK_KEY'] = None
    app.env = 'production'

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
    app.env = 'production'

    with app.app_context():
        flags = Flags()
        flags.init_app(app)
        on = flags.is_on('bool-flag')

    assert not on


def test_flags_bool(app):
    """Assert that a boolean (True) is returned."""
    from legal_api import flags

    with app.app_context():
        on = flags.is_on('bool-flag')

    assert on


def test_flags_bool_missing_flag(app):
    """Assert that a boolean (True) is returned."""
    from legal_api import flags

    with app.app_context():
        on = flags.is_on('no flag here')

    assert not on


def test_flags_bool_using_current_app():
    """Assert that a boolean (True) is returned."""
    from legal_api import flags
    app = Flask(__name__)
    app.env = 'development'

    with app.app_context():
        on = flags.is_on('bool-flag')

    assert on


@pytest.mark.parametrize('test_name,flag_name,expected', [
    ('boolean flag', 'bool-flag', True),
    ('string flag', 'string-flag', 'a string value'),
    ('integer flag', 'integer-flag', 10),
])
def test_flags_bool_value(test_name, flag_name, expected):
    """Assert that a boolean (True) is returned."""
    from legal_api import flags
    app = Flask(__name__)
    app.env = 'development'

    with app.app_context():
        val = flags.value(flag_name)

    assert val == expected


def test_flag_bool_unique_user(app):
    """Assert that a unique user can retrieve a flag."""
    from legal_api import flags
    user = User(username='username', firstname='firstname', lastname='lastname', sub='sub', iss='iss')
    with app.app_context():
        val = flags.value('bool-flag', user)
        on = flags.is_on('bool-flag', user)

    assert val
    assert on
