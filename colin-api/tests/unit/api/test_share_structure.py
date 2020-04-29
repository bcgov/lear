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

import copy
import json

from registry_schemas import validate
from registry_schemas.example_data import INCORPORATION_FILING_TEMPLATE

from tests import oracle_integration


@oracle_integration
def test_get_shares(client):
    """Assert the shares for a company can be retrieved."""
    headers = {'content-type': 'application/json'}
    rv = client.get('/api/v1/businesses?legal_type=BC')
    test_bcomp = f"BC{rv.json['corpNum'][0]}"

    filing = copy.deepcopy(INCORPORATION_FILING_TEMPLATE)
    filing['filing']['incorporationApplication']['nameRequest']['nrNumber'] = test_bcomp
    filing['filing']['business'] = {
            'cacheId': 1,
            'foundingDate': '2007-04-08T00:00:00+00:00',
            'identifier': f'{test_bcomp}',
            'lastLedgerTimestamp': '2019-04-15T20:05:49.068272+00:00',
            'lastPreBobFilingTimestamp': '2019-04-15T20:05:49.068272+00:00',
            'legalName': 'legal name - CP1234567',
            'legalType': 'BC'
        }

    rv = client.post(f'/api/v1/businesses/{test_bcomp}/filings/incorporationApplication',
                     data=json.dumps(filing), headers=headers)

    assert 201 == rv.status_code
    assert rv.json

    rv2 = client.get(f'/api/v1/businesses/{test_bcomp}/sharestructure')

    assert 200 == rv2.status_code
    assert rv2.json
    is_valid, errors = validate(rv2.json, 'share_class')

    print(errors)

    assert is_valid
    assert list(filter(lambda x: len(x['series']) == 2, rv2.json['shareClasses']))
