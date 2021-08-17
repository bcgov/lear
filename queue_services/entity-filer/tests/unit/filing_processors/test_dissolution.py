# Copyright © 2019 Province of British Columbia
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
"""The Unit Tests for the Voluntary Dissolution filing."""
import copy
from datetime import datetime

from legal_api.models import Business, Office, OfficeType
from registry_schemas.example_data import DISSOLUTION, FILING_HEADER

from entity_filer.filing_processors import dissolution
from tests.unit import create_business


def test_voluntary_dissolution(app, session):
    """Assert that the dissolution is processed.
    
    Not a very deep set of tests yet."""
    # setup
    filing_json = copy.deepcopy(FILING_HEADER)
    dissolution_date = '2021-05-06T07:01:01.000000+00:00' # this  will be 1 min after midnight
    dissolution_type = 'voluntary'
    # dissolution_date = '2019-04-15T20:05:49.068272+00:00' # this  will be 1 min after midnight
    has_liabilities = False
    identifier = 'BC1234567'
    legal_type = 'BEN'
    filing_json['filing']['business']['identifier'] = identifier
    filing_json['filing']['business']['legalType'] = legal_type

    filing_json['filing']['dissolution'] = DISSOLUTION
    filing_json['filing']['dissolution']['dissolutionDate'] = dissolution_date
    filing_json['filing']['dissolution']['dissolutionType'] = dissolution_type
    filing_json['filing']['dissolution']['hasLiabilities'] = has_liabilities

    business = create_business(identifier, legal_type=legal_type)
    business.dissolution_date = None
    business_id = business.id

    # test
    dissolution.process(business, filing_json['filing'])
    business.save()

    # validate
    assert business.dissolution_date == datetime.fromisoformat(dissolution_date)

    custodial_office = session.query(Business, Office). \
            filter(Business.id == Office.business_id). \
            filter(Business.id == business_id). \
            filter(Office.office_type == OfficeType.CUSTODIAL). \
            one_or_none()
    assert custodial_office
