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
import json
import random

from business_model import Filing, LegalEntity, PartyRole
from registry_schemas.example_data import (
    ANNUAL_REPORT,
    FILING_HEADER,
    SPECIAL_RESOLUTION,
)

from entity_filer.resources.worker import FilingMessage, process_filing
from tests.unit import create_business, create_filing


def test_technical_correction_ar(app, session):
    """Assert we can replace the filing with a technical_filing.

    We do an unlikely replacement and put in a technical change that
    uses pretty much a no-op filing
    and does not set the ar_dates which would've been done
    had the AR been processed.
    """
    filing_data = copy.deepcopy(ANNUAL_REPORT)

    identifier = "BC1010101"

    filing_data["filing"]["business"]["identifier"] = identifier

    business = create_business(identifier, legal_type="BC")

    payment_id = str(random.SystemRandom().getrandbits(0x58))
    filing = create_filing(payment_id, filing_data, business.id)
    filing_id = filing.id

    filing_msg = FilingMessage(
        filing_identifier=filing.id,
    )

    # sanity check
    # that it is an AR, and it is based on the ANNUAL_REPORT template
    assert filing.json["filing"]["annualReport"]
    assert (
        filing.json["filing"]["annualReport"]["annualGeneralMeetingDate"]
        == ANNUAL_REPORT["filing"]["annualReport"]["annualGeneralMeetingDate"]
    )
    # and the businesses last AR date is null
    assert not business.last_ar_date

    # subvert the filing
    technical_correction_filing = copy.deepcopy(FILING_HEADER)
    technical_correction_filing["filing"]["specialResolution"] = copy.deepcopy(SPECIAL_RESOLUTION)
    filing.tech_correction_json = technical_correction_filing
    # over ride the state and skip state setting listeners for this test
    filing.skip_status_listener = True
    filing._status = "PENDING"
    filing.save()

    # Test
    process_filing(filing_msg)

    # Check outcome
    business = LegalEntity.find_by_identifier(identifier)
    filing = Filing.find_by_id(filing_id)
    # If the AR had been processed, the last_ar_date would be set
    # But we instead technically replace and processed a SpecialResolution
    # THIS IS A BIG SIDE EFFECT
    assert not business.last_ar_date
    assert filing.filing_type == "annualReport"
    meta_data_str = json.dumps(filing.meta_data)
    assert "annualReport" not in meta_data_str
    assert "specialResolution" in meta_data_str
