# Copyright © 2022 Province of British Columbia
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

"""Tests to assure the ProgramAccount end-point.

Test-Suite to ensure that the /programAccount endpoint is working as expected.
"""
from tests import oracle_integration


@oracle_integration
def test_get_program_account_no_results(client):
    """Assert that the program account info."""
    rv = client.get('/api/v1/programAccount/FM0000001/BNTZLDLBBE3')

    assert 404 == rv.status_code
    assert None is not rv.json['message']


@oracle_integration
def test_get_bn15s(client):
    """Assert that the get BN15s endpoint works."""
    # Test with no identifiers
    rv = client.post('/api/v1/programAccount/check-bn15s', json={'identifiers': []})
    assert 400 == rv.status_code
    assert 'Identifiers required' == rv.json['message']

    rv = client.post('/api/v1/programAccount/check-bn15s', json={'identifiers': ['FM0000001']})
    assert 200 == rv.status_code
    assert 'bn15s' in rv.json
    assert isinstance(rv.json['bn15s'], list)
