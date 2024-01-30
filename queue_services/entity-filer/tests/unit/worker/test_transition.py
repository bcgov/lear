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
"""The Test Suites to ensure that the worker is operating correctly."""
import copy
import random

from business_model import LegalEntity, Filing, EntityRole
from registry_schemas.example_data import (
    TRANSITION_FILING_TEMPLATE,
    FILING_HEADER,
    TRANSITION,
)

from entity_filer.resources.worker import process_filing
from entity_filer.resources.worker import FilingMessage
from tests.unit import create_business, create_filing


def test_transition_filing(app, session):
    """Assert we can create a business based on transition filing."""
    filing_data = copy.deepcopy(FILING_HEADER)
    filing_data["filing"]["transition"] = copy.deepcopy(TRANSITION)

    filing_data["filing"]["transition"]["parties"][0]["officer"].pop("id")
    filing_data["filing"]["transition"]["parties"][1]["officer"].pop("id")

    identifier = "BC2020202"

    filing_data["filing"]["business"]["identifier"] = identifier
    business = create_business(identifier)

    payment_id = str(random.SystemRandom().getrandbits(0x58))
    filing = create_filing(payment_id, filing_data, business.id)

    filing_msg = FilingMessage(
        filing_identifier=filing.id,
    )

    # Test
    process_filing(filing_msg)

    # Check outcome
    filing = Filing.find_by_id(filing.id)
    business = LegalEntity.find_by_internal_id(filing.legal_entity_id)

    filing_json = filing.filing_json
    assert business
    assert filing
    assert filing.status == Filing.Status.COMPLETED.value
    assert business.restriction_ind is False
    assert len(business.share_classes.all()) == len(
        filing_json["filing"]["transition"]["shareStructure"]["shareClasses"]
    )
    assert len(business.offices.all()) == len(filing_json["filing"]["transition"]["offices"])
    assert len(business.aliases.all()) == len(filing_json["filing"]["transition"]["nameTranslations"])
    assert len(business.resolutions.all()) == len(
        filing_json["filing"]["transition"]["shareStructure"]["resolutionDates"]
    )
    director_entity_roles = EntityRole.get_entity_roles(business.id, role="director")
    assert len(director_entity_roles) == 1
