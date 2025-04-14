# Copyright © 2023 Province of British Columbia
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
"""The Unit Tests for the agm extension filing."""
import copy
import random

import pytest
from business_model.models import Filing
from registry_schemas.example_data import AGM_EXTENSION, FILING_HEADER

from business_filer.worker import process_filing
from tests.unit import create_business, create_filing


@pytest.mark.parametrize(
        'test_name',
        [
            ('general'), ('first_agm_year'), ('more_extension'), ('final_extension')
        ]
)
async def test_worker_agm_extension(app, session, mocker, test_name):
    """Assert that the agm extension object is correctly populated to model objects."""
    identifier = 'BC1234567'
    business = create_business(identifier, legal_type='BC')

    filing_json = copy.deepcopy(FILING_HEADER)
    filing_json['filing']['business']['identifier'] = identifier
    filing_json['filing']['agmExtension'] = copy.deepcopy(AGM_EXTENSION)

    if test_name == 'first_agm_year':
        del filing_json['filing']['agmExtension']['prevAgmRefDate']

    if test_name != 'more_extension':
        del filing_json['filing']['agmExtension']['expireDateCurrExt']

    if test_name == 'final_extension':
        filing_json['filing']['agmExtension']['totalApprovedExt'] = 12
    else:
        filing_json['filing']['agmExtension']['totalApprovedExt'] = 6

    payment_id = str(random.SystemRandom().getrandbits(0x58))
    filing = create_filing(payment_id, filing_json, business_id=business.id)

    filing_msg = {'filing': {'id': filing.id}}

    # mock out the email sender and event publishing
    mocker.patch('entity_filer.worker.publish_email_message', return_value=None)
    mocker.patch('entity_filer.worker.publish_event', return_value=None)

    # test
    await process_filing(filing_msg, app)

    # check outcome
    final_filing = Filing.find_by_id(filing.id)
    assert final_filing.id
    assert final_filing.meta_data

    agm_extension = final_filing.meta_data.get('agmExtension')
    assert agm_extension
    assert filing_json['filing']['agmExtension']['year'] == agm_extension.get('year')
    assert filing_json['filing']['agmExtension']['isFirstAgm'] == agm_extension.get('isFirstAgm')
    assert filing_json['filing']['agmExtension']['extReqForAgmYear'] == agm_extension.get('extReqForAgmYear')
    assert filing_json['filing']['agmExtension']['totalApprovedExt'] == agm_extension.get('totalApprovedExt')
    assert filing_json['filing']['agmExtension']['extensionDuration'] == agm_extension.get('extensionDuration')

    if test_name == 'first_agm_year':
        assert agm_extension.get('prevAgmRefDate') is None
    else:
        assert filing_json['filing']['agmExtension']['prevAgmRefDate'] == agm_extension.get('prevAgmRefDate')

    if test_name == 'more_extension':
        assert filing_json['filing']['agmExtension']['expireDateCurrExt'] == agm_extension.get('expireDateCurrExt')
    else:
        assert agm_extension.get('expireDateCurrExt') is None

    if test_name == 'final_extension':
        assert agm_extension.get('isFinalExtension') is True
    else:
        assert agm_extension.get('isFinalExtension') is False
