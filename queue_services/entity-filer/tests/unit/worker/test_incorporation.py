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
"""The Test Suites to ensure that the worker is operating correctly."""
import asyncio
import copy
import datetime
import random
import secrets
import string
from http import HTTPStatus
from unittest.mock import call, patch

import pytest
from business_model import EntityRole, Filing
from flask import current_app
from registry_schemas.example_data import INCORPORATION_FILING_TEMPLATE

from entity_filer.resources.worker import FilingMessage, process_filing
from entity_filer.services import BusinessService
from tests.unit import create_filing


@pytest.fixture(scope="function")
def bootstrap(account):
    """Create a IA filing for processing."""
    from business_model import RegistrationBootstrap

    bootstrap = RegistrationBootstrap()
    allowed_encoded = string.ascii_letters + string.digits
    bootstrap.identifier = "T" + "".join(secrets.choice(allowed_encoded) for _ in range(9))
    bootstrap.save()

    yield bootstrap.identifier


# @colin_api_integration
# @integration_affiliation
# @integration_namex_api
def test_incorporation_filing(app, session, bootstrap, requests_mock):
    """Assert we can retrieve a new corp number from COLIN and incorporate a business."""
    filing = copy.deepcopy(INCORPORATION_FILING_TEMPLATE)
    filing["filing"]["incorporationApplication"]["nameRequest"]["nrNumber"] = "NR 0000021"
    payment_id = str(random.SystemRandom().getrandbits(0x58))
    del filing["filing"]["incorporationApplication"]["parties"][0]["officer"]["id"]
    del filing["filing"]["incorporationApplication"]["parties"][1]["officer"]["id"]

    filing_id = (create_filing(payment_id, filing, bootstrap_id=bootstrap)).id

    filing_msg = FilingMessage(filing_identifier=filing_id)

    # Test
    response = "1234567"
    with app.app_context():
        current_app.config["COLIN_API"] = "http://localhost"
        requests_mock.post(f'{current_app.config["COLIN_API"]}/BC', json={"corpNum": response})
        process_filing(filing_msg)

    # Check outcome
    filing = Filing.find_by_id(filing_id)
    business = BusinessService.fetch_business_by_filing(filing)

    filing_json = filing.filing_json
    assert business
    assert filing
    assert filing.status == Filing.Status.COMPLETED.value
    assert business.identifier == filing_json["filing"]["business"]["identifier"]
    assert business.founding_date.isoformat() == filing_json["filing"]["business"]["foundingDate"]
    assert len(business.share_classes.all()) == len(
        filing_json["filing"]["incorporationApplication"]["shareStructure"]["shareClasses"]
    )
    assert len(business.offices.all()) == len(filing_json["filing"]["incorporationApplication"]["offices"])

    assert len(EntityRole.get_parties_by_role(business.id, "director")) == 1
    assert len(EntityRole.get_parties_by_role(business.id, "incorporator")) == 1
    assert len(EntityRole.get_entity_roles_by_filing(filing.id, role="completing_party")) == 1
    incorporator = (EntityRole.get_parties_by_role(business.id, "incorporator"))[0]
    completing_party = (EntityRole.get_entity_roles_by_filing(filing.id, role="completing_party"))[0]
    assert incorporator.appointment_date
    assert completing_party.appointment_date
