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
"""The Unit Tests for the Incorporation filing."""
import copy
import random
from datetime import datetime

import pytest
from legal_api.models import Business, Filing
from registry_schemas.example_data import ALTERATION_FILING_TEMPLATE, FILING_HEADER

from entity_filer.filing_processors import alteration
from entity_filer.worker import process_filing
from tests.unit import create_business, create_filing


@pytest.mark.parametrize(
    'orig_legal_type, new_legal_type',
    [
        (Business.LegalTypes.COMP.value, Business.LegalTypes.BCOMP.value),
        (Business.LegalTypes.BCOMP.value, Business.LegalTypes.COMP.value)
    ]
)
def test_alteration_process(app, session, orig_legal_type, new_legal_type):
    """Assert that the business legal type is altered."""
    # setup
    identifier = 'BC1234567'
    business = create_business(identifier)
    business.legal_type = orig_legal_type

    alteration_filing = copy.deepcopy(ALTERATION_FILING_TEMPLATE)
    alteration_filing['filing']['alteration']['nameTranslations'] = [{'name': 'A5 Ltd.'}]
    alteration_filing['filing']['business']['legalType'] = orig_legal_type
    alteration_filing['filing']['alteration']['business']['legalType'] = new_legal_type
    payment_id = str(random.SystemRandom().getrandbits(0x58))
    filing_submission = create_filing(payment_id, alteration_filing, business_id=business.id)

    # test
    alteration.process(business=business,
                       filing_submission=filing_submission,
                       filing=alteration_filing['filing'])

    # validate
    assert business.legal_type == new_legal_type


@pytest.mark.parametrize(
    'orig_legal_type, new_legal_type',
    [
        (Business.LegalTypes.COMP.value, Business.LegalTypes.BCOMP.value),
        (Business.LegalTypes.BCOMP.value, Business.LegalTypes.COMP.value)
    ]
)
async def test_worker_alteration(app, session, orig_legal_type, new_legal_type):
    """Assert the worker process calls the alteration correctly."""
    identifier = 'BC1234567'
    business = create_business(identifier, legal_type=orig_legal_type)
    filing = copy.deepcopy(ALTERATION_FILING_TEMPLATE)
    filing['filing']['business']['legalType'] = orig_legal_type
    filing['filing']['alteration']['business']['legalType'] = new_legal_type
    filing['filing']['alteration']['nameTranslations'] = [{'name': 'A5 Ltd.'}]

    payment_id = str(random.SystemRandom().getrandbits(0x58))
    filing_id = (create_filing(payment_id, filing, business_id=business.id)).id

    filing_msg = {'filing': {'id': filing_id}}

    # Test
    await process_filing(filing_msg, app)

    # Check outcome
    business = Business.find_by_internal_id(business.id)
    assert business.legal_type == new_legal_type

async def test_worker_alteration_court_order(app, session):
    """Assert the worker process calls the alteration correctly."""
    identifier = 'BC1234567'
    business = create_business(identifier, legal_type='BC')

    file_number: Final  = '#1234-5678/90'
    order_date: Final = '2021-01-30T09:56:01+08:00'
    effect_of_order: Final  = 'hasPlan'

    filing = copy.deepcopy(FILING_HEADER)
    filing['filing']['alteration'] = {'courtOrder':
                                   {
                                       'fileNumber': file_number,
                                       'orderDate': order_date,
                                       'effectOfOrder': effect_of_order
                                    }
    }
 
    payment_id = str(random.SystemRandom().getrandbits(0x58))
    filing_id = (create_filing(payment_id, filing, business_id=business.id)).id

    filing_msg = {'filing': {'id': filing_id}}

    # Test
    await process_filing(filing_msg, app)

    # Check outcome
    final_filing = Filing.find_by_id(filing_id)
    assert file_number == final_filing.court_order_file_number
    assert datetime.fromisoformat(order_date) == final_filing.court_order_date
    assert effect_of_order == final_filing.court_order_effect_of_order