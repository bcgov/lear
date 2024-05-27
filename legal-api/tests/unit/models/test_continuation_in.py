# Copyright © 2024 Province of British Columbia
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

"""Tests to assure the ContinuationIn Model.

Test-Suite to ensure that the ContinuationIn Model is working as expected.
"""
import copy
from registry_schemas.example_data import (
    CONTINUATION_IN,
    FILING_HEADER,
)

from legal_api.models.continuation_in import ContinuationIn

from tests.unit.models import factory_business, factory_completed_filing


def test_continuation_in_save(session):
    """Assert that the continuation_in was saved."""
    business = factory_business('BC1234567')
    filing_dict = copy.deepcopy(FILING_HEADER)
    filing_dict['filing']['continuationIn'] = copy.deepcopy(CONTINUATION_IN)
    filing = factory_completed_filing(business, filing_dict)

    continuation_in = ContinuationIn()
    continuation_in.jurisdiction = 'CA'
    continuation_in.jurisdiction_region = 'AB'
    continuation_in.identifier = 'AB1234567'
    continuation_in.legal_name = 'new legal name'
    continuation_in.incorporation_date = '2024-05-24'
    continuation_in.business_id = business.id
    continuation_in.filing_id = filing.id
    business.continuation_in.append(continuation_in)
    business.save()

    assert continuation_in.id
