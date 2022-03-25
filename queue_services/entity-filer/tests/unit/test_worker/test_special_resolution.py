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
"""The Unit Tests for the Special Resolution filing."""


import copy
import random

import pytest
from legal_api.models import Business, Filing
from registry_schemas.example_data import SPECIAL_RESOLUTION

from entity_filer.worker import process_filing
from tests.unit import create_entity, create_filing


CP_SPECIAL_RESOLUTION_TEMPLATE = {
    'filing': {
        'header': {
            'name': 'specialResolution',
            'availableOnPaperOnly': False,
            'certifiedBy': 'full name',
            'email': 'no_one@never.get',
            'date': '2020-02-18',
            'routingSlipNumber': '123456789',
            'waiveFees': False,
            'priority': True
        },
        'business': {
            'cacheId': 1,
            'foundingDate': '2007-04-08T00:00:00+00:00',
            'identifier': 'CP1234567',
            'lastLedgerTimestamp': '2019-04-15T20:05:49.068272+00:00',
            'lastPreBobFilingTimestamp': '2019-01-01T20:05:49.068272+00:00',
            'legalName': 'legal name - CP1234567',
            'legalType': 'CP'
        },
        'changeOfName': {
            'nameRequest': {
                'nrNumber': 'NR 8798956',
                'legalName': 'New Name',
                'legalType': 'CP'
            }
        },
        'specialResolution': SPECIAL_RESOLUTION
    }
}


@pytest.mark.parametrize(
    'test_name, legal_name, new_legal_name,legal_type, filing_template',
    [
        ('name_change', 'Test Resolution', 'New Name', 'CP', CP_SPECIAL_RESOLUTION_TEMPLATE),
        ('no_change', 'Test Resolution', None, 'CP', CP_SPECIAL_RESOLUTION_TEMPLATE)
    ]
)
async def test_special_resolution(app, session, mocker, test_name, legal_name, new_legal_name,
                                  legal_type, filing_template):
    """Assert the worker process calls the legal name change correctly."""
    identifier = 'CP1234567'
    business = create_entity(identifier, legal_type, legal_name)
    business_id = business.id
    filing = copy.deepcopy(filing_template)
    if test_name == 'name_change':
        filing['filing']['changeOfName']['nameRequest']['legalName'] = new_legal_name
    else:
        del filing['filing']['changeOfName']

    payment_id = str(random.SystemRandom().getrandbits(0x58))

    filing_id = (create_filing(payment_id, filing, business_id=business_id)).id
    filing_msg = {'filing': {'id': filing_id}}

    # mock out the email sender and event publishing
    mocker.patch('entity_filer.worker.publish_email_message', return_value=None)
    mocker.patch('entity_filer.worker.publish_event', return_value=None)
    mocker.patch('entity_filer.filing_processors.filing_components.name_request.consume_nr', return_value=None)

    # Test
    await process_filing(filing_msg, app)

    # Check outcome
    final_filing = Filing.find_by_id(filing_id)
    change_of_name = final_filing.meta_data.get('changeOfName', {})
    business = Business.find_by_internal_id(business_id)

    assert len(business.resolutions.all()) == 1
    resolution = business.resolutions.first()
    assert resolution.id
    assert resolution.resolution_type == 'SPECIAL'
    assert resolution.resolution_sub_type == 'specialResolution'

    if new_legal_name:
        assert business.legal_name == new_legal_name
        assert change_of_name.get('toLegalName') == new_legal_name
        assert change_of_name.get('fromLegalName') == legal_name
    else:
        assert business.legal_name == legal_name
        assert change_of_name == {}
