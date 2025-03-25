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
)

from business_model.models import Jurisdiction

from tests.models import factory_business, factory_completed_filing


def test_jurisdiction_save(session):
    """Assert that the jurisdiction was saved."""
    business = factory_business('BC1234567')
    filing_dict = {
        'filing': {
            'header': {
                'name': 'continuationIn',
                'date': '2019-04-08',
                'certifiedBy': 'full name',
                'email': 'no_one@never.get',
            }
        }
    }

    filing_dict['filing']['continuationIn'] = copy.deepcopy(CONTINUATION_IN)
    filing = factory_completed_filing(business, filing_dict)

    jurisdiction = Jurisdiction()
    jurisdiction.country = 'CA'
    jurisdiction.region = 'AB'
    jurisdiction.identifier = 'AB1234567'
    jurisdiction.legal_name = 'new legal name'
    jurisdiction.incorporation_date = '2024-05-24'
    jurisdiction.business_id = business.id
    jurisdiction.filing_id = filing.id
    business.jurisdictions.append(jurisdiction)
    business.save()

    assert jurisdiction.id

    jurisdiction = Jurisdiction.get_continuation_in_jurisdiction(business.id)
    assert jurisdiction
