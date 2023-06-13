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
"""The Test Suites to ensure that the worker is operating correctly."""
import copy
import random

from legal_api.core import Filing as FilingCore
from legal_api.models import Business, Filing, PartyRole
from registry_schemas.example_data import ANNUAL_REPORT, FILING_HEADER, SPECIAL_RESOLUTION

from entity_filer.worker import process_filing
from tests.unit import create_business, create_filing


async def test_correction_special_resolution(app, session):
    """Assert we can create a business based on transition filing."""
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
"""The Test Suites to ensure that the worker is operating correctly."""
import copy
import random
from unittest.mock import patch

from legal_api.models import Business, Filing
from registry_schemas.example_data import CORRECTION_CP_SPECIAL_RESOLUTION, CP_SPECIAL_RESOLUTION_TEMPLATE, SPECIAL_RESOLUTION

from entity_filer.worker import process_filing
from entity_filer.filing_processors import correction
from tests.unit import create_business, create_entity, create_filing, create_resolution, factory_completed_filing


# async def test_correction_special_resolution(app, session, mocker):
#     """Assert the worker process calls the special resolution correction correctly."""
#     identifier = 'CP1234567'
#     business = create_entity(identifier, 'CP', 'COOP INC.')
#     business_id = business.id
#     business.save()

#     sr_filing = copy.deepcopy(CP_SPECIAL_RESOLUTION_TEMPLATE)
#     sr_payment_id = str(random.SystemRandom().getrandbits(0x58))
#     sr_filing_id = (create_filing(sr_payment_id, sr_filing, business_id=business_id)).id
#     sr_filing_msg = {'filing': {'id': sr_filing_id}}
#     create_resolution(business, sr_filing, resolution=SPECIAL_RESOLUTION)
#     await process_filing(sr_filing_msg, app)

#     filing = copy.deepcopy(CORRECTION_CP_SPECIAL_RESOLUTION)

#     corrected_filing = factory_completed_filing(business, CORRECTION_CP_SPECIAL_RESOLUTION)
#     filing['filing']['correction']['correctedFilingId'] = corrected_filing.id

#     payment_id = str(random.SystemRandom().getrandbits(0x58))
#     correction_filing_id = (create_filing(payment_id, filing, business_id=business.id)).id
#     filing_msg = {'filing': {'id': correction_filing_id}}

#     # mock out the email sender and event publishing
#     mocker.patch('entity_filer.worker.publish_email_message', return_value=None)
#     mocker.patch('entity_filer.worker.publish_event', return_value=None)
#     mocker.patch('entity_filer.filing_processors.filing_components.name_request.consume_nr', return_value=None)
#     mocker.patch('entity_filer.filing_processors.filing_components.business_profile.update_business_profile',
#                  return_value=None)
#     mocker.patch('legal_api.services.bootstrap.AccountService.update_entity', return_value=None)

#     # Test
#     await process_filing(filing_msg, app)

#     # Check outcome
#     final_filing = Filing.find_by_id(correction_filing_id)
#     correction = final_filing.meta_data.get('correction', {})
#     business = Business.find_by_internal_id(business_id)
#     filing_comments = final_filing.comments.all()
#     assert len(filing_comments) == 1
#     assert filing_comments[0].comment == correction['comment']
#     assert len(corrected_filing.comments.all()) == 1


async def test_correction_special_resolution(app, session, mocker):
    """Assert that special resolution and signatory can be corrected."""
    identifier = 'CP1234567'
    business = create_entity(identifier, 'CP', 'COOP INC.')
    business_id = business.id
    business.save()

    sr_filing = copy.deepcopy(CP_SPECIAL_RESOLUTION_TEMPLATE)
    sr_payment_id = str(random.SystemRandom().getrandbits(0x58))
    sr_filing_id = (create_filing(sr_payment_id, sr_filing, business_id=business_id)).id
    sr_filing_msg = {'filing': {'id': sr_filing_id}}
    create_resolution(business, sr_filing, resolution=SPECIAL_RESOLUTION)
    await process_filing(sr_filing_msg, app)

    # now correct the special resolution
    correction_filing = copy.deepcopy(CORRECTION_CP_SPECIAL_RESOLUTION)
    correction_filing['filing']['header'] = FILING_HEADER
    correction_filing['filing']['header']['name'] = 'correction'
    correction_filing['filing']['business'] = {'identifier': identifier}
    correction_filing['filing']['correction']['correctedFilingType'] = 'specialResolution'
    correction_filing['filing']['correction']['resolution'] = 'New Resolution Text'
    correction_filing['filing']['correction']['signatory'] = {
        'givenName': 'Joe',
        'familyName': 'Doe',
        'additionalName': 'E'
    }

    # mock out the email sender and event publishing
    mocker.patch('entity_filer.worker.publish_email_message', return_value=None)
    mocker.patch('entity_filer.worker.publish_event', return_value=None)
    mocker.patch('entity_filer.filing_processors.filing_components.name_request.consume_nr', return_value=None)
    mocker.patch('entity_filer.filing_processors.filing_components.business_profile.update_business_profile',
                 return_value=None)
    mocker.patch('legal_api.services.bootstrap.AccountService.update_entity', return_value=None)

    # Test
    # payment_id = str(random.SystemRandom().getrandbits(0x58))
    # create_filing(payment_id, correction_filing, business_id=business_id)
    # with patch.object(correction, 'process') as mock_process:
    #     create_filing(session, correction_filing, business.id)

    # # Assert that the process method was called with the correct arguments
    # mock_process.assert_called_once_with(correction_filing)

