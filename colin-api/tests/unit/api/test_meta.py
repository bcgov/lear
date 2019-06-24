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

"""Tests to assure the meta end-point.

Test-Suite to ensure that the /meta endpoint is working as expected.
"""
from tests import skip_in_pod


@skip_in_pod
def test_meta_no_commit_hash(client):
    """Assert that the endpoint returns just the services __version__."""
    from colin_api.version import __version__

    rv = client.get('/api/v1/meta/info')

    assert rv.status_code == 200
    assert rv.json == {'API': f'colin_api/{__version__}'}


def test_meta_with_commit_hash(monkeypatch, client):
    """Assert that the endpoint return __version__ and the last git hash used to build the services image."""
    from colin_api.version import __version__

    commit_hash = 'deadbeef_ha'
    monkeypatch.setenv('OPENSHIFT_BUILD_COMMIT', commit_hash)

    rv = client.get('/api/v1/meta/info')
    assert rv.status_code == 200
    assert rv.json == {'API': f'colin_api/{__version__}-{commit_hash}'}
