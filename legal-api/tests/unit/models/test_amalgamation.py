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

"""Tests to assure the AlternateName Model.
Test-Suite to ensure that the AlternateName Model is working as expected.
"""
from datetime import datetime

from legal_api.models import amalgamation



def test_valid_amalgamation_save(session):
    """Assert that a valid alias can be saved."""
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
Tests to assure the Amalgamation Model.
Test-Suite to ensure that the Amalgamation Model is working as expected.

"""
from datetime import datetime

from legal_api.models import amalgamation


def test_valid_amalgamation_save(session):
    """Assert that a valid alias can be saved."""
    identifier = 1234567
    
    amalgamation_1 = amalgamation(
        identifier = identifier,
        amalgamation_type = amalgamation.Amalgamation.AmalgamationTypes.horizontal,
        business_id = 1234,
        filing_id = 1234,
        amalgamation_date = datetime.utcnow,
        court_approval = True
    )
    
    amalgamation_1.save()
    
    amalgamation_2 = amalgamation(
        identifier = identifier,
        amalgamation_type = amalgamation.Amalgamation.AmalgamationTypes.vertical,
        business_id = 1234,
        filing_id = 1234,
        amalgamation_date = datetime.utcnow,
        court_approval = True
    )
    
    amalgamation_2.save()
    
    amalgamation_3 = amalgamation(
        identifier = identifier,
        amalgamation_type = amalgamation.Amalgamation.AmalgamationTypes.regular,
        business_id = 1234,
        filing_id = 1234,
        amalgamation_date = datetime.utcnow,
        court_approval = True
    )
    
    amalgamation_3.save()
    
    # verify
    assert amalgamation_1.id
    assert amalgamation_2.id
    assert amalgamation_3.id
    amalgamating_business_roles = amalgamation.Amalgamation.AmalgamationTypes.all()
    