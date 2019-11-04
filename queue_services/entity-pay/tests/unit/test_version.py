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

"""Tests to assure the version utilities.

Test-Suite to ensure that the version utilities are working as expected.
"""
from entity_pay import utils
from entity_pay.version import __version__


def test_get_version():
    """Assert that the version is returned correctly."""
    rv = utils.get_run_version()
    assert rv == __version__


def test_get_version_hash(monkeypatch):
    """Assert that the version also contains the git commit hash."""
    monkeypatch.setenv('OPENSHIFT_BUILD_COMMIT', 'openshift_git_hash')
    rv = utils.get_run_version()
    assert 'openshift_git_hash' in rv
    assert __version__ in rv
