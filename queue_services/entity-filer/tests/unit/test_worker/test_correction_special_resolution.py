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
import io
import random

import pytest
from dateutil.parser import parse
from legal_api.models import Business, Filing
from registry_schemas.example_data import ANNUAL_REPORT, CORRECTION_AR, CORRECTION_CP_SPECIAL_RESOLUTION,\
                                        CP_SPECIAL_RESOLUTION_TEMPLATE, FILING_HEADER

from entity_filer.worker import process_filing
from tests.unit import create_entity, create_filing


@pytest.mark.asyncio
async def test_special_resolution_correction(app, session, mocker):
    """Test the special resolution correction functionality."""
    class MockFileResponse:
        """Mock the MinioService."""

        def __init__(self, file_content):
            self.data = io.BytesIO(file_content.encode('utf-8'))

    # Mock the MinioService's get_file method to return a dictionary with 'data' pointing to an instance of MockFileResponse
    mocker.patch('legal_api.services.minio.MinioService.get_file', return_value=MockFileResponse('fake file content'))
    mocker.patch('entity_filer.worker.publish_email_message', return_value=None)
    mocker.patch('entity_filer.worker.publish_event', return_value=None)
    mocker.patch('entity_filer.filing_processors.filing_components.name_request.consume_nr', return_value=None)
    mocker.patch('entity_filer.filing_processors.filing_components.business_profile.update_business_profile',
                 return_value=None)
    mocker.patch('legal_api.services.bootstrap.AccountService.update_entity', return_value=None)

    # Create business
    identifier = 'CP1234567'
    business = create_entity(identifier, 'CP', 'COOP INC.')
    business_id = business.id
    business.save()

    # Create an initial special resolution filing
    sr_filing = copy.deepcopy(CP_SPECIAL_RESOLUTION_TEMPLATE)
    sr_payment_id = str(random.SystemRandom().getrandbits(0x58))
    sr_filing_id = (create_filing(sr_payment_id, sr_filing, business_id=business_id)).id

    # Mock the filing message
    sr_filing_msg = {'filing': {'id': sr_filing_id}}
    # Call the process_filing method for the original special resolution
    await process_filing(sr_filing_msg, app)

    # Simulate a correction filing
    correction_data = copy.deepcopy(FILING_HEADER)
    correction_data['filing']['correction'] = copy.deepcopy(CORRECTION_CP_SPECIAL_RESOLUTION)
    correction_data['filing']['header']['name'] = 'correction'
    correction_data['filing']['business'] = {'identifier': identifier}
    correction_data['filing']['correction']['correctedFilingType'] = 'specialResolution'
    correction_data['filing']['correction']['resolution'] = '<p>xxxx</p>'
    correction_data['filing']['correction']['signatory'] = {
        'givenName': 'Joey',
        'familyName': 'Doe',
        'additionalName': ''
    }
    # Update correction data to point to the original special resolution filing
    if 'correction' not in correction_data['filing']:
        correction_data['filing']['correction'] = {}
    correction_data['filing']['correction']['correctedFilingId'] = sr_filing_id
    correction_payment_id = str(random.SystemRandom().getrandbits(0x58))
    correction_filing_id = (create_filing(correction_payment_id, correction_data, business_id=business_id)).id

    # Mock the correction filing message
    correction_filing_msg = {'filing': {'id': correction_filing_id}}

    # Call the process_filing method for the correction
    await process_filing(correction_filing_msg, app)

    # Assertions
    business = Business.find_by_internal_id(business_id)
    assert len(business.resolutions.all()) == 1
    resolution = business.resolutions.first()
    assert resolution is not None, 'Resolution should exist'
    assert resolution.resolution == '<p>xxxx</p>', 'Resolution text should be corrected'

    # # # Check if the signatory was updated
    party = resolution.party
    assert party is not None, 'Party should exist'
    assert party.first_name == 'JOEY', 'First name should be corrected'
    assert party.last_name == 'DOE', 'Last name should be corrected'

    # Simulate another correction filing on previous correction
    resolution_date = '2023-06-16'
    correction_data_2 = copy.deepcopy(FILING_HEADER)
    correction_data_2['filing']['correction'] = copy.deepcopy(CORRECTION_CP_SPECIAL_RESOLUTION)
    correction_data_2['filing']['header']['name'] = 'correction'
    correction_data_2['filing']['business'] = {'identifier': identifier}
    correction_data_2['filing']['correction']['correctedFilingType'] = 'correction'
    correction_data_2['filing']['correction']['resolution'] = '<p>yyyy</p>'
    correction_data_2['filing']['correction']['resolutionDate'] = resolution_date
    correction_data_2['filing']['correction']['signatory'] = {
        'givenName': 'Sarah',
        'familyName': 'Doe',
        'additionalName': ''
    }
    # Update correction data to point to the original special resolution filing
    if 'correction' not in correction_data_2['filing']:
        correction_data_2['filing']['correction'] = {}
    correction_data_2['filing']['correction']['correctedFilingId'] = correction_filing_id
    correction_payment_id_2 = str(random.SystemRandom().getrandbits(0x58))
    correction_filing_id_2 = (create_filing(correction_payment_id_2, correction_data_2, business_id=business_id)).id

    # Mock the correction filing message
    correction_filing_msg_2 = {'filing': {'id': correction_filing_id_2}}

    # Call the process_filing method for the correction
    await process_filing(correction_filing_msg_2, app)

    # Assertions
    business = Business.find_by_internal_id(business_id)
    resolution = business.resolutions.first()
    assert resolution is not None, 'Resolution should exist'
    assert resolution.resolution == '<p>yyyy</p>', 'Resolution text should be corrected'
    assert resolution.resolution_date == parse(resolution_date).date()

    # # # Check if the signatory was updated
    party = resolution.party
    assert party is not None, 'Party should exist'
    assert party.first_name == 'SARAH', 'First name should be corrected'
    assert party.last_name == 'DOE', 'Last name should be corrected'


async def test_non_special_resolution_correction_filing(app, session):
    """Assert we can't process a cp but not SR correction filing."""
    # Create business
    payment_id = str(random.SystemRandom().getrandbits(0x58))
    identifier = 'CP1234567'
    business = create_entity(identifier, 'CP', 'COOP INC.')
    business_id = business.id
    business.save()
    original_filing_id = create_filing(payment_id, copy.deepcopy(ANNUAL_REPORT), business_id).id

    # setup - create correction filing
    filing = copy.deepcopy(CORRECTION_AR)
    filing['filing']['header']['identifier'] = identifier
    filing['filing']['correction']['comment'] = 'test cp correction'
    filing['filing']['correction']['correctedFilingId'] = original_filing_id
    correction_filing = create_filing(payment_id, filing, business_id)
    correction_filing.save()

    correction_filing_id = correction_filing.id
    filing_msg = {'filing': {'id': correction_filing_id}}

    # TEST
    await process_filing(filing_msg, app)

    # Assertions
    origin_filing = Filing.find_by_id(original_filing_id)
    assert origin_filing.status == 'PENDING'
