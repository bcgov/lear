# Copyright © 2020 Province of British Columbia
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

"""Tests for the share structure end-point."""
from registry_schemas import validate

from tests import oracle_integration


@oracle_integration
def test_get_shares(client):
    """Assert the shares for a company can be retrieved."""
    rv2 = client.get('/api/v1/businesses/BC/0870156/sharestructure')

    assert 200 == rv2.status_code
    assert rv2.json
    is_valid, errors = validate(rv2.json, 'share_class')

    print(errors)

    assert is_valid
    assert list(filter(lambda x: len(x['series']) == 0, rv2.json['shareClasses']))
