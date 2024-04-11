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
"""The Unit Tests for the Change of Registration filing."""
import copy
import random
from typing import Final
from unittest.mock import patch

import pytest
from business_model import Address, AlternateName, BusinessCommon, EntityRole, Filing, LegalEntity

# from datetime import datetime
from business_model.utils.datetime import datetime
from registry_schemas.example_data import CHANGE_OF_REGISTRATION_TEMPLATE, COURT_ORDER, REGISTRATION

# from legal_api.services import NaicsService
from entity_filer.filing_processors.filing_components.legal_entity_info import NaicsService
from entity_filer.resources.worker import FilingMessage, process_filing
from tests.unit import (
    create_alternate_name,
    create_entity,
    create_entity_person,
    create_entity_role,
    create_filing,
    create_office,
    create_office_address,
)

CONTACT_POINT = {"email": "no_one@never.get", "phone": "123-456-7890"}

GP_CHANGE_OF_REGISTRATION = copy.deepcopy(CHANGE_OF_REGISTRATION_TEMPLATE)
GP_CHANGE_OF_REGISTRATION["filing"]["changeOfRegistration"]["parties"].append(REGISTRATION["parties"][1])

SP_CHANGE_OF_REGISTRATION = copy.deepcopy(CHANGE_OF_REGISTRATION_TEMPLATE)
SP_CHANGE_OF_REGISTRATION["filing"]["business"]["legalType"] = "SP"
SP_CHANGE_OF_REGISTRATION["filing"]["changeOfRegistration"]["nameRequest"]["legalType"] = "SP"
SP_CHANGE_OF_REGISTRATION["filing"]["changeOfRegistration"]["parties"][0]["roles"] = [
    {"roleType": "Completing Party", "appointmentDate": "2022-01-01"},
    {"roleType": "Proprietor", "appointmentDate": "2022-01-01"},
]

naics_response = {
    "code": REGISTRATION["business"]["naics"]["naicsCode"],
    "naicsKey": "a4667c26-d639-42fa-8af3-7ec73e392569",
}


@pytest.mark.parametrize(
    "test_name, operating_name, new_operating_name,legal_type, filing_template",
    [
        ("name_change", "Old Name", "New Name", "SP", SP_CHANGE_OF_REGISTRATION),
        ("no_change", "Old Name", None, "SP", SP_CHANGE_OF_REGISTRATION),
    ],
)
def test_change_of_registration_operating_name_sp(
    app,
    session,
    mocker,
    test_name,
    operating_name,
    new_operating_name,
    legal_type,
    filing_template,
):
    """Assert the worker process calls the legal name change correctly."""

    identifier = "FM1234567"

    filing = copy.deepcopy(filing_template)
    if test_name == "name_change":
        filing["filing"]["changeOfRegistration"]["nameRequest"]["legalName"] = new_operating_name
    else:
        del filing["filing"]["changeOfRegistration"]["nameRequest"]

    payment_id = str(random.SystemRandom().getrandbits(0x58))

    proprietor_identifier = "P1234567"
    proprietor = create_entity(proprietor_identifier, "person", "my self old")
    filing["filing"]["changeOfRegistration"]["parties"][0]["officer"]["id"] = proprietor.id

    filing["filing"]["business"]["identifier"] = identifier
    filing = create_filing(payment_id, filing)

    alternate_name = create_alternate_name(
        identifier=identifier,
        entity_type=BusinessCommon.EntityTypes.SOLE_PROP,
        name=operating_name,
        change_filing_id=filing.id,
    )
    proprietor.alternate_names.append(alternate_name)
    proprietor.save()
    proprietor_id = proprietor.id

    filing_id = filing.id
    filing.alternate_name_id = alternate_name.id
    filing.save()

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
    final_filing = Filing.find_by_id(filing_id)
    change_of_registration = final_filing.meta_data.get("changeOfRegistration", {})
    business = LegalEntity.find_by_internal_id(proprietor_id)
    alternate_name = business.alternate_names.all()[0]

    if new_operating_name:
        assert alternate_name.name == new_operating_name
        assert change_of_registration.get("toLegalName") == new_operating_name
        assert change_of_registration.get("fromLegalName") == operating_name
    else:
        assert alternate_name.name == operating_name
        assert change_of_registration.get("toLegalName") is None
        assert change_of_registration.get("fromLegalName") is None


@pytest.mark.parametrize(
    "test_name, operating_name, new_operating_name,legal_type, filing_template",
    [
        ("name_change", "Old Name", "New Name", "GP", GP_CHANGE_OF_REGISTRATION),
        ("no_change", "Old Name", None, "GP", GP_CHANGE_OF_REGISTRATION),
    ],
)
def test_change_of_registration_operating_name_gp(
    app,
    session,
    mocker,
    test_name,
    operating_name,
    new_operating_name,
    legal_type,
    filing_template,
):
    """Assert the worker process calls the operating name change correctly."""

    identifier = "FM1234567"

    filing = copy.deepcopy(filing_template)
    if test_name == "name_change":
        filing["filing"]["changeOfRegistration"]["nameRequest"]["legalName"] = new_operating_name
    else:
        del filing["filing"]["changeOfRegistration"]["nameRequest"]

    payment_id = str(random.SystemRandom().getrandbits(0x58))

    filing = create_filing(payment_id, filing)

    business = create_entity(identifier, legal_type, None)

    alternate_name = create_alternate_name(
        identifier=identifier,
        entity_type=BusinessCommon.EntityTypes.PARTNERSHIP,
        name=operating_name,
        change_filing_id=filing.id,
    )
    business.alternate_names.append(alternate_name)
    business.save()
    business_id = business.id
    filing_id = filing.id
    filing.legal_entity_id = business_id
    filing.save()

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
    final_filing = Filing.find_by_id(filing_id)
    change_of_registration = final_filing.meta_data.get("changeOfRegistration", {})
    business = LegalEntity.find_by_internal_id(business_id)

    if new_operating_name:
        assert len(business.alternate_names.all()) > 0
        assert business.alternate_names[0].name == new_operating_name
        assert change_of_registration.get("toLegalName") == new_operating_name
        assert change_of_registration.get("fromLegalName") == operating_name
    else:
        assert len(business.alternate_names.all()) > 0
        assert business.alternate_names[0].name == operating_name
        assert change_of_registration.get("toLegalName") is None
        assert change_of_registration.get("fromLegalName") is None


@pytest.mark.parametrize(
    "test_name,legal_type, legal_name, filing_template",
    [
        ("sp_address_change", "SP", "Test Firm", SP_CHANGE_OF_REGISTRATION),
        ("gp_address_change", "GP", "Test Firm", GP_CHANGE_OF_REGISTRATION),
    ],
)
def test_change_of_registration_business_address(
    app, session, mocker, test_name, legal_type, legal_name, filing_template
):
    """Assert the worker process calls the business address change correctly."""
    identifier = "FM1234567"
    proprietor_identifier = "P1234567"
    if legal_type == BusinessCommon.EntityTypes.SOLE_PROP.value:
        proprietor = create_entity(proprietor_identifier, "person", legal_name)
        business = create_alternate_name(identifier=identifier, entity_type=BusinessCommon.EntityTypes.SOLE_PROP)
        proprietor.alternate_names.append(business)
        proprietor.save()
    else:
        business = create_entity(identifier, legal_type, legal_name)
        alternate_name = create_alternate_name(
            identifier=identifier, entity_type=BusinessCommon.EntityTypes.PARTNERSHIP
        )
        business.alternate_names.append(alternate_name)
        business.save()

    business_id = business.id

    office = create_office(business, "registeredOffice")

    business_delivery_address = create_office_address(business, office, "delivery")
    business_mailing_address = create_office_address(business, office, "mailing")

    business_delivery_address_id = business_delivery_address.id
    business_mailing_address_id = business_mailing_address.id

    filing = copy.deepcopy(filing_template)

    del filing["filing"]["changeOfRegistration"]["nameRequest"]
    del filing["filing"]["changeOfRegistration"]["parties"]

    filing["filing"]["changeOfRegistration"]["offices"]["businessOffice"]["deliveryAddress"][
        "id"
    ] = business_delivery_address_id
    filing["filing"]["changeOfRegistration"]["offices"]["businessOffice"]["mailingAddress"][
        "id"
    ] = business_mailing_address_id

    payment_id = str(random.SystemRandom().getrandbits(0x58))

    filing_submission = create_filing(payment_id, filing)
    if business.is_alternate_name_entity:
        filing_submission.legal_entity_id = None
        filing_submission.alternate_name_id = business_id
    else:
        filing_submission.legal_entity_id = business_id
    filing_submission.save()
    filing_msg = FilingMessage(filing_identifier=filing_submission.id)

    # mock out the email sender and event publishing
    # mocker.patch('entity_filer.worker.publish_email_message', return_value=None)
    # mocker.patch('entity_filer.worker.publish_event', return_value=None)
    mocker.patch(
        "entity_filer.filing_processors.filing_components.name_request.consume_nr",
        return_value=None,
    )
    # mocker.patch('entity_filer.filing_processors.filing_components.business_profile.update_business_profile',
    #              return_value=None)
    # mocker.patch('legal_api.services.bootstrap.AccountService.update_entity', return_value=None)

    # Test
    with patch.object(NaicsService, "find_by_code", return_value=naics_response):
        process_filing(filing_msg)

    # Check outcome
    changed_delivery_address = Address.find_by_id(business_delivery_address_id)
    for key in ["streetAddress", "postalCode", "addressCity", "addressRegion"]:
        assert (
            changed_delivery_address.json[key]
            == filing["filing"]["changeOfRegistration"]["offices"]["businessOffice"]["deliveryAddress"][key]
        )
    changed_mailing_address = Address.find_by_id(business_mailing_address_id)
    for key in ["streetAddress", "postalCode", "addressCity", "addressRegion"]:
        assert (
            changed_mailing_address.json[key]
            == filing["filing"]["changeOfRegistration"]["offices"]["businessOffice"]["mailingAddress"][key]
        )


@pytest.mark.parametrize(
    "test_name, legal_type, legal_name, filing_template",
    [
        ("gp_court_order", "GP", "Test Firm", GP_CHANGE_OF_REGISTRATION),
        ("sp_court_order", "SP", "Test Firm", SP_CHANGE_OF_REGISTRATION),
    ],
)
def test_worker_change_of_registration_court_order(
    app, session, mocker, test_name, legal_type, legal_name, filing_template
):
    """Assert the worker process the court order correctly."""
    identifier = "FM1234567"
    proprietor_identifier = "P1234567"
    if legal_type == BusinessCommon.EntityTypes.SOLE_PROP.value:
        proprietor = create_entity(proprietor_identifier, "person", legal_name)
        business = create_alternate_name(identifier=identifier, entity_type=BusinessCommon.EntityTypes.SOLE_PROP)
        proprietor.alternate_names.append(business)
        proprietor.save()
    else:
        business = create_entity(identifier, legal_type, legal_name)
        alternate_name = create_alternate_name(
            identifier=identifier, entity_type=BusinessCommon.EntityTypes.PARTNERSHIP
        )
        business.alternate_names.append(alternate_name)
        business.save()

    business_id = business.id

    filing = copy.deepcopy(filing_template)

    file_number: Final = "#1234-5678/90"
    order_date: Final = "2021-01-30T09:56:01+08:00"
    effect_of_order: Final = "hasPlan"

    filing["filing"]["changeOfRegistration"]["contactPoint"] = CONTACT_POINT

    filing["filing"]["changeOfRegistration"]["courtOrder"] = COURT_ORDER
    filing["filing"]["changeOfRegistration"]["courtOrder"]["effectOfOrder"] = effect_of_order

    del filing["filing"]["changeOfRegistration"]["nameRequest"]
    del filing["filing"]["changeOfRegistration"]["parties"]

    payment_id = str(random.SystemRandom().getrandbits(0x58))
    filing_submission = create_filing(payment_id, filing)
    if business.is_alternate_name_entity:
        filing_submission.legal_entity_id = None
        filing_submission.alternate_name_id = business_id
    else:
        filing_submission.legal_entity_id = business_id

    filing_msg = FilingMessage(filing_identifier=filing_submission.id)

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
    final_filing = Filing.find_by_id(filing_submission.id)
    assert file_number == final_filing.court_order_file_number
    assert datetime.fromisoformat(order_date) == final_filing.court_order_date
    assert effect_of_order == final_filing.court_order_effect_of_order


def test_worker_proprietor_name_and_address_change(app, session, mocker):
    """Assert the worker process the name and address change correctly."""
    identifier = "FM1234567"
    alternate_name = create_alternate_name(identifier=identifier, entity_type=BusinessCommon.EntityTypes.SOLE_PROP)

    party = create_entity_person(SP_CHANGE_OF_REGISTRATION["filing"]["changeOfRegistration"]["parties"][0])
    party_id = party.id
    party.alternate_names.append(alternate_name)

    party.save()

    filing = copy.deepcopy(SP_CHANGE_OF_REGISTRATION)
    filing["filing"]["changeOfRegistration"]["contactPoint"] = CONTACT_POINT
    filing["filing"]["changeOfRegistration"]["parties"][0]["officer"]["id"] = party_id
    filing["filing"]["changeOfRegistration"]["parties"][0]["officer"]["firstName"] = "New First Name"
    filing["filing"]["changeOfRegistration"]["parties"][0]["officer"]["middleName"] = "New Middle Name"
    filing["filing"]["changeOfRegistration"]["parties"][0]["officer"]["lastName"] = "New Last Name"
    filing["filing"]["changeOfRegistration"]["parties"][0]["mailingAddress"]["streetAddress"] = "New Mailing Address"
    filing["filing"]["changeOfRegistration"]["parties"][0]["deliveryAddress"]["streetAddress"] = "New Delivery Address"

    del filing["filing"]["changeOfRegistration"]["nameRequest"]

    payment_id = str(random.SystemRandom().getrandbits(0x58))
    filing_submission = create_filing(payment_id, filing)
    filing_submission.alternate_name_id = alternate_name.id
    filing_submission.save()
    filing_msg = FilingMessage(filing_identifier=filing_submission.id)

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
    assert party.first_name == filing["filing"]["changeOfRegistration"]["parties"][0]["officer"]["firstName"].upper()
    assert (
        party.middle_initial == filing["filing"]["changeOfRegistration"]["parties"][0]["officer"]["middleName"].upper()
    )
    assert party.last_name == filing["filing"]["changeOfRegistration"]["parties"][0]["officer"]["lastName"].upper()
    assert (
        party.entity_delivery_address.street
        == filing["filing"]["changeOfRegistration"]["parties"][0]["deliveryAddress"]["streetAddress"]
    )
    assert (
        party.entity_mailing_address.street
        == filing["filing"]["changeOfRegistration"]["parties"][0]["mailingAddress"]["streetAddress"]
    )


@pytest.mark.parametrize(
    "test_name",
    [
        "gp_add_partner",
        "gp_edit_partner_name_and_address",
        "gp_delete_partner",
    ],
)
def test_worker_partner_name_and_address_change(app, session, mocker, test_name):
    """Assert the worker process the partner name and address change correctly."""
    identifier = "FM1234567"
    business = create_entity(identifier, "GP", "Test Entity")
    alternate_name = create_alternate_name(identifier=identifier, entity_type=BusinessCommon.EntityTypes.PARTNERSHIP)
    business.alternate_names.append(alternate_name)
    business_id = business.id

    party1 = create_entity_person(GP_CHANGE_OF_REGISTRATION["filing"]["changeOfRegistration"]["parties"][0])
    party_id_1 = party1.id
    party2 = create_entity_person(GP_CHANGE_OF_REGISTRATION["filing"]["changeOfRegistration"]["parties"][1])
    party_id_2 = party2.id

    create_entity_role(business, party1, ["partner"], datetime.utcnow())
    create_entity_role(business, party2, ["partner"], datetime.utcnow())

    business.save()

    filing = copy.deepcopy(GP_CHANGE_OF_REGISTRATION)
    filing["filing"]["changeOfRegistration"]["contactPoint"] = CONTACT_POINT
    filing["filing"]["changeOfRegistration"]["parties"][0]["officer"]["id"] = party_id_1
    filing["filing"]["changeOfRegistration"]["parties"][1]["officer"]["id"] = party_id_2

    if test_name == "gp_add_partner":
        new_party_json = GP_CHANGE_OF_REGISTRATION["filing"]["changeOfRegistration"]["parties"][1]
        del new_party_json["officer"]["id"]
        new_party_json["officer"]["firstName"] = "New Name"
        filing["filing"]["changeOfRegistration"]["parties"].append(new_party_json)

    if test_name == "gp_edit_partner_name_and_address":
        filing["filing"]["changeOfRegistration"]["parties"][0]["officer"]["firstName"] = "New Name a"
        filing["filing"]["changeOfRegistration"]["parties"][0]["officer"]["middleName"] = "New Name a"
        filing["filing"]["changeOfRegistration"]["parties"][0]["mailingAddress"]["streetAddress"] = "New Name"
        filing["filing"]["changeOfRegistration"]["parties"][0]["deliveryAddress"]["streetAddress"] = "New Name"

    if test_name == "gp_delete_partner":
        del filing["filing"]["changeOfRegistration"]["parties"][1]

    del filing["filing"]["changeOfRegistration"]["nameRequest"]

    payment_id = str(random.SystemRandom().getrandbits(0x58))
    filing_id = (create_filing(payment_id, filing, business_id=business.id)).id

    filing_msg = FilingMessage(filing_identifier=filing_id)

    # mock out the email sender and event publishing
    # mocker.patch("entity_filer.worker.publish_email_message", return_value=None)
    # mocker.patch("entity_filer.worker.publish_event", return_value=None)
    # mocker.patch(
    #     "entity_filer.filing_processors.filing_components.name_request.consume_nr",
    #     return_value=None,
    # )
    # mocker.patch(
    #     "entity_filer.filing_processors.filing_components.business_profile.update_business_profile",
    #     return_value=None,
    # )
    # mocker.patch(
    #     "legal_api.services.bootstrap.AccountService.update_entity", return_value=None
    # )

    # Test
    with patch.object(NaicsService, "find_by_code", return_value=naics_response):
        process_filing(filing_msg)

    # Check outcome
    business = LegalEntity.find_by_internal_id(business_id)

    if test_name == "gp_edit_partner_name_and_address":
        party = business.entity_roles.all()[0].related_entity
        assert (
            party.first_name == filing["filing"]["changeOfRegistration"]["parties"][0]["officer"]["firstName"].upper()
        )
        assert (
            party.entity_delivery_address.street
            == filing["filing"]["changeOfRegistration"]["parties"][0]["deliveryAddress"]["streetAddress"]
        )
        assert (
            party.entity_mailing_address.street
            == filing["filing"]["changeOfRegistration"]["parties"][0]["mailingAddress"]["streetAddress"]
        )
        assert business.entity_roles.all()[0].cessation_date is None
        assert business.entity_roles.all()[1].cessation_date is None

    if test_name == "gp_delete_partner":
        deleted_role = EntityRole.get_entity_roles_by_party_id(business_id, party_id_2)[0]
        assert deleted_role.cessation_date is not None

    if test_name == "gp_add_partner":
        assert len(EntityRole.get_parties_by_role(business_id, "partner")) == 3
        assert len(business.entity_roles.all()) == 3
        for party_role in business.entity_roles.all():
            assert party_role.cessation_date is None
