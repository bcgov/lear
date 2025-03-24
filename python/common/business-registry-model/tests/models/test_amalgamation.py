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
from tests.models import (
    factory_business,
    factory_business_mailing_address,
    factory_completed_filing,
    factory_filing,
    factory_user,
)
from business_model.models import Filing
from business_model.models import Business
from business_model.models import Amalgamation
from registry_schemas.example_data import (
    ALTERATION_FILING_TEMPLATE,
    ANNUAL_REPORT,
    CHANGE_OF_DIRECTORS,
    CORRECTION_AR,
    COURT_ORDER,
    FILING_HEADER,
    SPECIAL_RESOLUTION,
)
from datetime import datetime

from business_model.models import amalgamation


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


def test_valid_amalgamation_save(session):
    """Assert that a valid alias can be saved."""

    b = factory_business('CP1234567')

    b.save()

    filing = factory_filing(b, ANNUAL_REPORT)

    filing.save()

    amalgamation_1 = Amalgamation(
        amalgamation_type=Amalgamation.AmalgamationTypes.horizontal,
        business_id=b.id,
        filing_id=filing.id,
        amalgamation_date=datetime.utcnow(),
        court_approval=True
    )

    amalgamation_1.save()

    amalgamation_2 = Amalgamation(
        amalgamation_type=Amalgamation.AmalgamationTypes.vertical,
        business_id=b.id,
        filing_id=filing.id,
        amalgamation_date=datetime.utcnow(),
        court_approval=True
    )

    amalgamation_2.save()

    amalgamation_3 = Amalgamation(
        amalgamation_type=Amalgamation.AmalgamationTypes.regular,
        business_id=b.id,
        filing_id=filing.id,
        amalgamation_date=datetime.utcnow(),
        court_approval=True
    )

    amalgamation_3.save()

    amalgamation_4 = Amalgamation(
        amalgamation_type=Amalgamation.AmalgamationTypes.unknown,
        business_id=b.id,
        filing_id=filing.id,
        amalgamation_date=datetime.utcnow(),
        court_approval=True
    )

    amalgamation_4.save()

    # verify
    assert amalgamation_1.id
    assert amalgamation_2.id
    assert amalgamation_3.id
    assert amalgamation_4.id
    for type in Amalgamation.AmalgamationTypes:
        assert type in [Amalgamation.AmalgamationTypes.horizontal,
                        Amalgamation.AmalgamationTypes.vertical,
                        Amalgamation.AmalgamationTypes.regular,
                        Amalgamation.AmalgamationTypes.unknown]
