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

"""Tests to ensure alterations are working."""

import copy
import json

from registry_schemas.example_data import ALTERATION_FILING_TEMPLATE, INCORPORATION_FILING_TEMPLATE

from tests import oracle_integration


@oracle_integration
def test_incorporate_bcomp(client):
    """Assert that an alteration works."""
    headers = {'content-type': 'application/json'}
    rv = client.post('/api/v1/businesses/BC')
    test_bcomp = f"{rv.json['corpNum']}"
    legal_name = f'legal name - {test_bcomp}'
    filing = copy.deepcopy(INCORPORATION_FILING_TEMPLATE)
    filing['filing']['header']['learEffectiveDate'] = \
        f'{filing["filing"]["header"]["date"]}T15:22:39.868757+00:00'
    filing['filing']['incorporationApplication']['nameRequest']['nrNumber'] = test_bcomp
    filing['filing']['incorporationApplication']['nameRequest']['legalType'] = 'BEN'
    filing['filing']['business'] = {
            'cacheId': 1,
            'foundingDate': '2007-04-08T00:00:00+00:00',
            'identifier': f'{test_bcomp}',
            'lastLedgerTimestamp': '2019-04-15T20:05:49.068272+00:00',
            'lastPreBobFilingTimestamp': '2019-04-15T20:05:49.068272+00:00',
            'legalName': legal_name,
            'legalType': 'BC'
        }

    rv = client.post(f'/api/v1/businesses/BC/{test_bcomp}/filings/incorporationApplication',
                     data=json.dumps(filing), headers=headers)
    # assert rv.json
    assert 201 == rv.status_code
    filing = rv.json['filing']
    alteration_filing = copy.deepcopy(ALTERATION_FILING_TEMPLATE)
    alteration_filing['filing']['header']['learEffectiveDate'] = \
        f'{filing["header"]["date"]}T15:22:39.868757+00:00'
    alteration_filing['filing']['alteration']['nameRequest']['nrNumber'] = 'BC' + test_bcomp
    alteration_filing['filing']['alteration']['nameRequest']['legalType'] = 'BEN'
    alteration_filing['filing']['business'] = {
            'cacheId': 1,
            'foundingDate': '2007-04-08T00:00:00+00:00',
            'identifier': f'BC{test_bcomp}',
            'lastLedgerTimestamp': '2019-04-15T20:05:49.068272+00:00',
            'lastPreBobFilingTimestamp': '2019-04-15T20:05:49.068272+00:00',
            'legalName': legal_name,
            'legalType': 'BC'
        }

    rv = client.post(f'/api/v1/businesses/BC/BC{test_bcomp}/filings/alteration',
                     data=json.dumps(alteration_filing), headers=headers)

    assert 201 == rv.status_code

    result_alteration_filing = rv.json['filing']
    assert 'alteration' in result_alteration_filing
    assert 'contactPoint' in result_alteration_filing['alteration']
    assert 'nameTranslations' in result_alteration_filing['alteration']
    assert 'shareStructure' in result_alteration_filing['alteration']
    assert 'courtOrder' in result_alteration_filing['alteration']
    assert 'fileNumber' in result_alteration_filing['alteration']['courtOrder']
    assert 'effectOfOrder' in result_alteration_filing['alteration']['courtOrder']

    rv = client.get(f'/api/v1/businesses/BC/BC{test_bcomp}/filings/alteration')

    assert 200 == rv.status_code
    result_alteration_filing = rv.json['filing']
    assert 'alteration' in result_alteration_filing
    assert 'contactPoint' in result_alteration_filing['alteration']
    assert 'nameTranslations' in result_alteration_filing['alteration']
    assert 'shareStructure' in result_alteration_filing['alteration']
    assert 'courtOrder' in result_alteration_filing['alteration']
    assert 'fileNumber' in result_alteration_filing['alteration']['courtOrder']
    assert 'effectOfOrder' in result_alteration_filing['alteration']['courtOrder']

    assert result_alteration_filing['alteration']['courtOrder']['fileNumber'] == \
        ALTERATION_FILING_TEMPLATE['filing']['alteration']['courtOrder']['fileNumber']
    assert result_alteration_filing['alteration']['courtOrder']['effectOfOrder'] == 'planOfArrangement'
