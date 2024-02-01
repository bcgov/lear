# Copyright © 2022 Province of British Columbia
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
"""The Unit Tests for the Conversion filing."""
import copy
import random
from datetime import datetime
from unittest.mock import patch

import pytest
from business_model import Address, EntityRole, Filing, LegalEntity
from registry_schemas.example_data import CONVERSION_FILING_TEMPLATE, COURT_ORDER, FIRMS_CONVERSION, REGISTRATION

# from legal_api.services import NaicsService
from entity_filer.filing_processors.filing_components.legal_entity_info import NaicsService
from entity_filer.resources.worker import FilingMessage, process_filing
from tests.unit import create_entity, create_entity_person, create_entity_role, create_filing

CONTACT_POINT = {"email": "no_one@never.get", "phone": "123-456-7890"}

naics_response = {
    "code": REGISTRATION["business"]["naics"]["naicsCode"],
    "naicsKey": "a4667c26-d639-42fa-8af3-7ec73e392569",
}

GP_CONVERSION = copy.deepcopy(CONVERSION_FILING_TEMPLATE)
GP_CONVERSION["filing"]["conversion"] = copy.deepcopy(FIRMS_CONVERSION)
GP_CONVERSION["filing"]["business"]["legalType"] = "GP"
GP_CONVERSION["filing"]["conversion"]["nameRequest"]["legalType"] = "GP"

SP_CONVERSION = copy.deepcopy(CONVERSION_FILING_TEMPLATE)
SP_CONVERSION["filing"]["conversion"] = copy.deepcopy(FIRMS_CONVERSION)
SP_CONVERSION["filing"]["business"]["legalType"] = "SP"
SP_CONVERSION["filing"]["conversion"]["nameRequest"]["legalType"] = "SP"
del SP_CONVERSION["filing"]["conversion"]["parties"][1]
SP_CONVERSION["filing"]["conversion"]["parties"][0]["roles"] = [
    {"roleType": "Completing Party", "appointmentDate": "2022-01-01"},
    {"roleType": "Proprietor", "appointmentDate": "2022-01-01"},
]


@pytest.mark.parametrize(
    "test_name, legal_name, new_legal_name,legal_type, filing_template",
    [
        ("conversion_gp", "Test Firm", "New Name", "GP", GP_CONVERSION),
        ("conversion_sp", "Test Firm", "New Name", "SP", SP_CONVERSION),
    ],
)
def test_conversion(
    app,
    session,
    mocker,
    test_name,
    legal_name,
    new_legal_name,
    legal_type,
    filing_template,
):
    """Assert the worker process conversion  filing correctly."""

    identifier = "FM1234567"
    business = create_entity(identifier, legal_type, legal_name)
    business.save()
    business_id = business.id
    filing = copy.deepcopy(filing_template)
    filing["filing"]["business"]["legalType"] = legal_type
    # Name Change
    filing["filing"]["conversion"]["nameRequest"]["legalName"] = new_legal_name
    # del filing["filing"]["conversion"]["parties"][0]["officer"]["id"]

    payment_id = str(random.SystemRandom().getrandbits(0x58))

    filing_id = (create_filing(payment_id, filing, business_id=business_id)).id
    filing_msg = FilingMessage(filing_identifier=filing_id)

    # mock out the email sender and event publishing
    # mocker.patch('entity_filer.worker.publish_email_message', return_value=None)
    # mocker.patch('entity_filer.worker.publish_event', return_value=None)
    # mocker.patch('entity_filer.filing_processors.filing_components.name_request.consume_nr', return_value=None)
    # mocker.patch('entity_filer.filing_processors.filing_components.business_profile.update_business_profile',
    #              return_value=None)
    # mocker.patch('legal_api.services.bootstrap.AccountService.update_entity', return_value=None)

    # Test
    process_filing(filing_msg)

    # Check outcome
    final_filing = Filing.find_by_id(filing_id)
    business = LegalEntity.find_by_internal_id(business_id)

    # Name Change
    assert business.legal_name == new_legal_name

    # Parties
    if legal_type == "SP":
        assert len(final_filing.filing_entity_roles.all()) == 1
        assert len(business.entity_roles.all()) == 1
    if legal_type == "GP":
        assert len(final_filing.filing_entity_roles.all()) == 1
        assert len(business.entity_roles.all()) == 2

    # Offices
    assert len(business.offices.all()) == 1
    assert business.offices.first().office_type == "businessOffice"

    assert (
        business.naics_description == filing_template["filing"]["conversion"]["business"]["naics"]["naicsDescription"]
    )


def test_worker_proprietor_new_address(app, session, mocker):
    """Assert the worker process the party new address correctly."""

    party = create_entity_person(SP_CONVERSION["filing"]["conversion"]["parties"][0])
    party_id = party.id
    party.entity_delivery_address = None
    party.entity_mailing_address = None
    party.save()
    assert party.entity_delivery_address is None
    assert party.entity_mailing_address is None

    create_entity_role(party, None, ["proprietor"], datetime.utcnow())

    filing = copy.deepcopy(SP_CONVERSION)
    filing["filing"]["conversion"]["contactPoint"] = CONTACT_POINT
    filing["filing"]["conversion"]["parties"][0]["officer"]["id"] = party_id
    filing["filing"]["conversion"]["parties"][0]["mailingAddress"]["streetAddress"] = "New Name"
    filing["filing"]["conversion"]["parties"][0]["deliveryAddress"]["streetAddress"] = "New Name"

    del filing["filing"]["conversion"]["nameRequest"]

    payment_id = str(random.SystemRandom().getrandbits(0x58))
    filing_id = (create_filing(payment_id, filing, business_id=party.id)).id

    filing_msg = FilingMessage(filing_identifier=filing_id)

    # mock out the email sender and event publishing
    # mocker.patch('entity_filer.worker.publish_email_message', return_value=None)
    # mocker.patch('entity_filer.worker.publish_event', return_value=None)
    # mocker.patch('entity_filer.filing_processors.filing_components.name_request.consume_nr', return_value=None)
    # mocker.patch('entity_filer.filing_processors.filing_components.business_profile.update_business_profile',
    #              return_value=None)
    # mocker.patch('legal_api.services.bootstrap.AccountService.update_entity', return_value=None)

    # Test
    with patch.object(NaicsService, "find_by_code", return_value=naics_response):
        process_filing(filing_msg)

    # Check outcome
    party = LegalEntity.find_by_internal_id(party_id)
    assert party.entity_roles.all()[0].role_type == EntityRole.RoleTypes.proprietor
    assert (
        party.entity_delivery_address.street
        == filing["filing"]["conversion"]["parties"][0]["deliveryAddress"]["streetAddress"]
    )
    assert (
        party.entity_mailing_address.street
        == filing["filing"]["conversion"]["parties"][0]["mailingAddress"]["streetAddress"]
    )
