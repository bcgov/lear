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

import pytest
from legal_api.models import Business
from registry_schemas.example_data import ALTERATION_FILING_TEMPLATE

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

    # test
    alteration.process(business, alteration_filing['filing'])

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
    business = create_business(identifier)
    business.legal_type = orig_legal_type
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
