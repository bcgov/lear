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
from datetime import date

from entity_filer.filing_processors import voluntary_dissolution
from tests.unit import create_business


def test_change_of_name_process(app, session):
    """Assert that the voluntary dissolution date is set."""
    # setup
    dissolution_date = '2020-07-01'
    has_liabilities = False
    identifier = 'CP1234567'
    con = {'voluntaryDissolution': {'dissolutionDate': dissolution_date,
                                    'hasLiabilities': has_liabilities}
           }

    business = create_business(identifier)
    business.dissolution_date = None

    # test
    voluntary_dissolution.process(business, con)

    # validate
    assert business.dissolution_date == date.fromisoformat(dissolution_date)
