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
from registry_schemas.example_data import CORRECTION_CONVERSION,\
                                        CONVERSION_FILING_TEMPLATE, FILING_HEADER

from entity_filer.worker import process_filing
from tests.unit import create_entity, create_filing


@pytest.mark.parametrize(
    'test_name, filing_template, correction_template',
    [
        ('pending_correction_status', CONVERSION_FILING_TEMPLATE, CORRECTION_CONVERSION),
    ]
)
async def test_conversion_correction(app, session, mocker, test_name, filing_template, correction_template):
    """Test the conversion correction functionality."""
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
    identifier = 'FM1104477'
    business = create_entity(identifier, 'SP', 'CONVERSION INC.')
    business_id = business.id
    business.save()

    # Create an initial conversion filing
    conversion_filing = copy.deepcopy(filing_template)
    conversion_payment_id = str(random.SystemRandom().getrandbits(0x58))
    conversion_filing_id = (create_filing(conversion_payment_id, conversion_filing, business_id=business_id)).id

    # Mock the filing message
    conversion_filing_msg = {'filing': {'id': conversion_filing_id}}
    # Call the process_filing method for the original conversion
    await process_filing(conversion_filing_msg, app)

    # Simulate a correction filing
    correction_data = copy.deepcopy(FILING_HEADER)
    correction_data['filing']['correction'] = copy.deepcopy(correction_template)
    correction_data['filing']['header']['name'] = 'correction'
    correction_data['filing']['header']['legalType'] = 'SP'
    correction_data['filing']['business'] = {'identifier': identifier}
    # Update correction data to point to the original conversion filing
    if 'correction' not in correction_data['filing']:
        correction_data['filing']['correction'] = {}
    correction_data['filing']['correction']['correctedFilingId'] = conversion_filing_id
    correction_payment_id = str(random.SystemRandom().getrandbits(0x58))
    correction_filing_id = (create_filing(correction_payment_id, correction_data, business_id=business_id)).id

    # Mock the correction filing message
    correction_filing_msg = {'filing': {'id': correction_filing_id}}

    # Call the process_filing method for the correction
    await process_filing(correction_filing_msg, app)

    # Assertions
    origin_filing = Filing.find_by_id(correction_filing_id)
    assert origin_filing.status == Filing.Status.PENDING_CORRECTION.value
