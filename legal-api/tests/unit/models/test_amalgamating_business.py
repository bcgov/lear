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

from legal_api.models import AmalgamatingBusiness
from legal_api.models import Business
from legal_api.models import Amalgamation


def test_valid_alternate_name_save(session):
    """Assert that a valid alias can be saved."""
    identifier = 1234567
    # legal_entity = factory_legal_entity(identifier)
    
    amalgamating_business_1 = AmalgamatingBusiness(
        id = identifier,
        role = AmalgamatingBusiness.Role.AMALGAMATING,
        foreign_jurisdiction = "Alberta",
        foreign_name = "Testing123",
        foreign_corp_num = "123456789",
        business_id = Business.id,
        amalgamation_id = Amalgamation.id
    )
    amalgamating_business_1.save()
    
    amalgamating_business_2 = AmalgamatingBusiness(
        id = identifier,
        role = AmalgamatingBusiness.Role.HOLDING,
        foreign_jurisdiction = "Alberta",
        foreign_name = "Testing123",
        foreign_corp_num = "123456789",
        business_id = Business.id,
        amalgamation_id = Amalgamation.id
    )
    amalgamating_business_2.save()
    
    # verify
    assert amalgamating_business_1.id
    assert amalgamating_business_2.id
    amalgamating_business_roles = AmalgamatingBusiness.Role.all()
    assert len(amalgamating_business_roles) == 2
    assert any(AmalgamatingBusiness.Role.HOLDING for role_type in amalgamating_business_roles)
    assert any(AmalgamatingBusiness.Role.AMALGAMATING for role_type in amalgamating_business_roles)
    
    