# Copyright © 2025 Province of British Columbia
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
"""The Unit Tests for the Intent to Liquidate filing."""

import copy
import random
from datetime import datetime, timedelta

import pytest
from legal_api.models import Business, Filing
from registry_schemas.example_data import INTENT_TO_LIQUIDATE, FILING_TEMPLATE

from entity_filer.worker import process_filing
from tests.unit import create_business, create_filing


@pytest.mark.parametrize(
    'test_name, legal_type',
    [
        ('bc_company', 'BC'),
        ('c_company', 'C'),
        ('ben_company', 'BEN'),
        ('cben_company', 'CBEN'),
        ('ulc_company', 'ULC'),
        ('cul_company', 'CUL'),
        ('cc_company', 'CC'),
        ('ccc_company', 'CCC'),
    ]
)
async def test_intent_to_liquidate_filing_process(app, session, mocker, test_name, legal_type):
    """Assert that the intent to liquidate object is correctly populated to model objects."""
    # Setup
    identifier = 'BC1234567'
    business = create_business(identifier, legal_type=legal_type)
    business.in_liquidation = False
    business.save()

    # Create filing
    filing_json = copy.deepcopy(FILING_TEMPLATE)
    filing_json['filing']['header']['name'] = 'intentToLiquidate'
    filing_json['filing']['business']['identifier'] = identifier
    filing_json['filing']['intentToLiquidate'] = copy.deepcopy(INTENT_TO_LIQUIDATE)
    # Override liquidation date to be after founding date
    future_date = (datetime.utcnow() + timedelta(days=30)).strftime('%Y-%m-%d')
    filing_json['filing']['intentToLiquidate']['dateOfCommencementOfLiquidation'] = future_date

    payment_id = str(random.SystemRandom().getrandbits(0x58))
    filing = create_filing(payment_id, filing_json, business_id=business.id)
    filing_msg = {'filing': {'id': filing.id}}

    # mock out the email sender and event publishing
    mocker.patch('entity_filer.worker.publish_email_message', return_value=None)
    mocker.patch('entity_filer.worker.publish_event', return_value=None)
    mocker.patch('entity_filer.filing_processors.filing_components.name_request.consume_nr', return_value=None)
    mocker.patch('entity_filer.filing_processors.filing_components.business_profile.update_business_profile',
                 return_value=None)
    mocker.patch('legal_api.services.bootstrap.AccountService.update_entity', return_value=None)

    # Test
    await process_filing(filing_msg, app)

    # Assertions
    filing = Filing.find_by_id(filing.id)
    business = Business.find_by_internal_id(business.id)
    
    assert filing.status == Filing.Status.COMPLETED.value
    assert business.in_liquidation is True
    assert len(filing.comments.all()) == 1
    
    # Check filing metadata
    filing_meta = filing.meta_data.get('intentToLiquidate', {})
    assert filing_meta['dateOfCommencementOfLiquidation'] == future_date
    assert filing_meta['liquidationOfficer'] is not None
    assert filing_meta['liquidationOffice'] is not None
    
    # Check comment was added
    comment = filing.comments.all()[0]
    assert f'Liquidation is scheduled to commence on {future_date}' in comment.comment
    assert comment.staff_id == filing.submitter_id
