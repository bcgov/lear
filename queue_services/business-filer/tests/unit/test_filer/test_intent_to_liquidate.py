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
from business_model.models import Business, Filing
from registry_schemas.example_data import INTENT_TO_LIQUIDATE, FILING_TEMPLATE

from business_filer.common.filing_message import FilingMessage
from business_filer.services.filer import process_filing
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
def test_intent_to_liquidate_filing_process(app, session, mocker, test_name, legal_type):
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
    filing_msg = FilingMessage(filing_identifier=filing.id)

    # mock out the email sender and event publishing
    mocker.patch('business_filer.services.publish_event.PublishEvent.publish_email_message', return_value=None)
    mocker.patch('business_filer.services.publish_event.PublishEvent.publish_event', return_value=None)
    mocker.patch('business_filer.filing_processors.filing_components.name_request.consume_nr', return_value=None)
    mocker.patch('business_filer.filing_processors.filing_components.business_profile.update_business_profile',
                 return_value=None)
    mocker.patch('business_filer.services.AccountService.update_entity', return_value=None)

    # Test
    process_filing(filing_msg)

    # Assertions
    filing = Filing.find_by_id(filing.id)
    business = Business.find_by_internal_id(filing.business_id)

    assert filing.status == Filing.Status.COMPLETED.value
    assert business.in_liquidation is True
    assert len(filing.comments.all()) == 1

    # Check filing metadata
    filing_meta = filing.meta_data.get('intentToLiquidate', {})
    assert filing_meta['dateOfCommencementOfLiquidation'] == future_date

    # Check comment was added
    comment = filing.comments.all()[0]
    assert f'Liquidation is scheduled to commence on {future_date}' in comment.comment
    assert comment.staff_id == filing.submitter_id
