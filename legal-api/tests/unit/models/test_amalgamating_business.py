# Copyright © 2023 Province of British Columbia
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

"""
Tests to assure the AlternateName Model.
Test-Suite to ensure that the AlternateName Model is working as expected.

"""
from datetime import datetime

from registry_schemas.example_data import (
    ALTERATION_FILING_TEMPLATE,
    ANNUAL_REPORT,
    CHANGE_OF_DIRECTORS,
    CORRECTION_AR,
    COURT_ORDER,
    FILING_HEADER,
    SPECIAL_RESOLUTION,
)

from legal_api.models import AmalgamatingBusiness, Business, Amalgamation
from tests.unit.models import (
    factory_business,
    factory_business_mailing_address,
    factory_completed_filing,
    factory_filing,
    factory_user,
)

def test_valid_amalgamating_business_save(session):
    """Assert that a valid alias can be saved."""
    identifier = 1234567
    
    b = factory_business('CP1234567')
    b.save()
    
    filing = factory_filing(b, ANNUAL_REPORT)
    filing.save()
    
    amalgamation = Amalgamation(
        id = identifier,
        amalgamation_type = Amalgamation.AmalgamationTypes.horizontal,
        business_id = b.id,
        filing_id = filing.id,
        amalgamation_date = datetime.utcnow(),
        court_approval = True
    )
    
    amalgamation.save()
    
    amalgamating_business_1 = AmalgamatingBusiness(
        id = identifier,
        role = AmalgamatingBusiness.Role.AMALGAMATING,
        foreign_jurisdiction = "Alberta",
        foreign_name = "Testing123",
        foreign_corp_num = "123456789",
        business_id = b.id,
        amalgamation_id = amalgamation.id
    )
    amalgamating_business_1.save()
    
    identifier = 1234568
    
    amalgamating_business_2 = AmalgamatingBusiness(
        id = identifier,
        role = AmalgamatingBusiness.Role.HOLDING,
        foreign_jurisdiction = "Alberta",
        foreign_name = "Testing123",
        foreign_corp_num = "123456789",
        business_id = b.id,
        amalgamation_id = amalgamation.id
    )
    amalgamating_business_2.save()
    
    # verify
    assert amalgamating_business_1.id
    assert amalgamating_business_2.id
    for type in AmalgamatingBusiness.Role:
        assert type in [AmalgamatingBusiness.Role.HOLDING,
                        AmalgamatingBusiness.Role.AMALGAMATING]
