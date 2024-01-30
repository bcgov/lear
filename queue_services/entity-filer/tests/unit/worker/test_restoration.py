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
"""The Unit Tests for the Restoration filing."""
import copy
import random

import pytest
from business_model import LegalEntity, Filing, EntityRole, OfficeType, Address
from business_model.utils.datetime import datetime
from business_model.utils.legislation_datetime import LegislationDatetime
from registry_schemas.example_data import FILING_HEADER, RESTORATION

from entity_filer.resources.worker import process_filing
from entity_filer.resources.worker import FilingMessage
from tests.unit import create_business, create_filing

from sql_versioning import versioned_session
from tests.unit import nested_session

legal_name = "old name"
legal_type = "BC"


@pytest.mark.parametrize(
    "restoration_type",
    [
        ("fullRestoration"),
        ("limitedRestoration"),
        ("limitedRestorationExtension"),
        ("limitedRestorationToFull"),
    ],
)
def test_restoration_business_update(app, session, mocker, restoration_type):
    """Assert the worker process update business correctly."""
    identifier = "BC1234567"
    business = create_business(identifier, legal_type=legal_type, legal_name=legal_name)
    business.state = LegalEntity.State.HISTORICAL
    business.dissolution_date = datetime(2017, 5, 17)
    business.save()
    business_id = business.id

    filing = copy.deepcopy(FILING_HEADER)
    filing["filing"]["restoration"] = copy.deepcopy(RESTORATION)
    filing["filing"]["header"]["name"] = "restoration"
    expiry_date = "2023-05-18"
    if restoration_type in ("limitedRestoration", "limitedRestorationExtension"):
        filing["filing"]["restoration"]["expiry"] = expiry_date
    payment_id = str(random.SystemRandom().getrandbits(0x58))
    del filing["filing"]["restoration"]["parties"][0]["officer"]["id"]

    filing_id = (create_filing(payment_id, filing, business_id=business_id)).id
    filing_msg = FilingMessage(filing_identifier=filing_id)

    _mock_out(mocker)

    process_filing(filing_msg)

    # Check outcome
    business = LegalEntity.find_by_internal_id(business_id)
    assert business.state == LegalEntity.State.ACTIVE
    assert business.state_filing_id == filing_id
    assert business.dissolution_date is None

    if restoration_type in ("limitedRestoration", "limitedRestorationExtension"):
        assert business.restoration_expiry_date == datetime.fromisoformat(f"{expiry_date}T07:00:00+00:00")

        final_filing = Filing.find_by_id(filing_id)
        restoration = final_filing.meta_data.get("restoration", {})
        assert restoration.get("expiry") == expiry_date
    else:
        assert business.restoration_expiry_date is None


@pytest.mark.parametrize(
    "test_name",
    [
        ("name"),
        ("number"),
    ],
)
def test_restoration_legal_name(app, session, mocker, test_name):
    """Assert the worker process calls the legal name change correctly."""
    identifier = "BC1234567"
    business = create_business(identifier, legal_type=legal_type, legal_name=legal_name)
    business.save()
    business_id = business.id
    filing = copy.deepcopy(FILING_HEADER)
    filing["filing"]["restoration"] = copy.deepcopy(RESTORATION)
    filing["filing"]["header"]["name"] = "restoration"

    new_legal_name = "new name"
    if test_name == "name":
        filing["filing"]["restoration"]["nameRequest"]["legalName"] = new_legal_name
        filing["filing"]["restoration"]["nameRequest"]["nrNumber"] = "NR 123456"
    del filing["filing"]["restoration"]["parties"][0]["officer"]["id"]

    payment_id = str(random.SystemRandom().getrandbits(0x58))

    filing_id = (create_filing(payment_id, filing, business_id=business_id)).id
    filing_msg = FilingMessage(filing_identifier=filing_id)

    _mock_out(mocker)

    process_filing(filing_msg)

    # Check outcome
    final_filing = Filing.find_by_id(filing_id)
    restoration = final_filing.meta_data.get("restoration", {})
    business = LegalEntity.find_by_internal_id(business_id)

    if test_name == "name":
        assert business.legal_name == new_legal_name
        assert restoration.get("toLegalName") == new_legal_name
        assert restoration.get("fromLegalName") == legal_name
    else:
        numbered_legal_name_suffix = LegalEntity.BUSINESSES[legal_type]["numberedBusinessNameSuffix"]
        new_legal_name = f"{identifier[2:]} {numbered_legal_name_suffix}"
        assert business.legal_name == new_legal_name
        assert restoration.get("toLegalName") == new_legal_name
        assert restoration.get("fromLegalName") == legal_name


def test_restoration_office_addresses(app, session, mocker):
    """Assert the worker process calls the address change correctly."""
    identifier = "BC1234567"
    business = create_business(identifier, legal_type=legal_type, legal_name=legal_name)
    business.save()
    business_id = business.id
    filing = copy.deepcopy(FILING_HEADER)
    filing["filing"]["restoration"] = copy.deepcopy(RESTORATION)
    filing["filing"]["header"]["name"] = "restoration"
    del filing["filing"]["restoration"]["parties"][0]["officer"]["id"]

    payment_id = str(random.SystemRandom().getrandbits(0x58))

    filing_id = (create_filing(payment_id, filing, business_id=business_id)).id
    filing_msg = FilingMessage(filing_identifier=filing_id)

    _mock_out(mocker)

    process_filing(filing_msg)

    # Check outcome
    # changed_delivery_address = business.entity_delivery_address.one_or_none()
    offices = business.offices.all()
    registered_office = None
    for office in offices:
        if office.office_type == OfficeType.REGISTERED:
            registered_office = office
            break
    assert registered_office

    for address in registered_office.addresses.all():
        if address.address_type == Address.DELIVERY:
            changed_delivery_address = address
        if address.address_type == Address.MAILING:
            changed_mailing_address = address

    for key in ["streetAddress", "postalCode", "addressCity", "addressRegion"]:
        assert (
            changed_delivery_address.json[key]
            == filing["filing"]["restoration"]["offices"]["registeredOffice"]["deliveryAddress"][key]
        )
    # changed_mailing_address = business.entity_mailing_address.one_or_none()
    for key in ["streetAddress", "postalCode", "addressCity", "addressRegion"]:
        assert (
            changed_mailing_address.json[key]
            == filing["filing"]["restoration"]["offices"]["registeredOffice"]["mailingAddress"][key]
        )


@pytest.mark.parametrize("approval_type", [("registrar"), ("courtOrder")])
def test_restoration_court_order(app, session, mocker, approval_type):
    """Assert the worker process the court order correctly."""
    identifier = "BC1234567"
    business = create_business(identifier, legal_type=legal_type, legal_name=legal_name)
    business.save()
    business_id = business.id
    filing = copy.deepcopy(FILING_HEADER)
    filing["filing"]["restoration"] = copy.deepcopy(RESTORATION)
    filing["filing"]["header"]["name"] = "restoration"
    filing["filing"]["restoration"]["approvalType"] = approval_type
    if approval_type == "registrar":
        del filing["filing"]["restoration"]["courtOrder"]
    del filing["filing"]["restoration"]["parties"][0]["officer"]["id"]

    payment_id = str(random.SystemRandom().getrandbits(0x58))

    filing_id = (create_filing(payment_id, filing, business_id=business_id)).id
    filing_msg = FilingMessage(filing_identifier=filing_id)

    _mock_out(mocker)

    process_filing(filing_msg)

    # Check outcome
    final_filing = Filing.find_by_id(filing_id)
    assert filing["filing"]["restoration"]["approvalType"] == final_filing.approval_type
    if approval_type == "courtOrder":
        assert filing["filing"]["restoration"]["courtOrder"]["fileNumber"] == final_filing.court_order_file_number
    else:
        assert final_filing.court_order_file_number is None


@pytest.mark.parametrize("approval_type", [("registrar"), ("courtOrder")])
def test_restoration_registrar(app, session, mocker, approval_type):
    """Assert the worker process the registrar correctly."""
    identifier = "BC1234567"
    business = create_business(identifier, legal_type=legal_type, legal_name=legal_name)
    business.save()
    business_id = business.id
    filing = copy.deepcopy(FILING_HEADER)
    filing["filing"]["restoration"] = copy.deepcopy(RESTORATION)
    filing["filing"]["header"]["name"] = "restoration"
    filing["filing"]["restoration"]["approvalType"] = approval_type
    application_date = "2023-01-15"
    notice_date = "2023-05-02"
    filing["filing"]["restoration"]["applicationDate"] = application_date
    filing["filing"]["restoration"]["noticeDate"] = notice_date

    if approval_type == "courtOrder":
        del filing["filing"]["restoration"]["applicationDate"]
        del filing["filing"]["restoration"]["noticeDate"]
    del filing["filing"]["restoration"]["parties"][0]["officer"]["id"]

    payment_id = str(random.SystemRandom().getrandbits(0x58))

    filing_id = (create_filing(payment_id, filing, business_id=business_id)).id
    filing_msg = FilingMessage(filing_identifier=filing_id)

    _mock_out(mocker)

    process_filing(filing_msg)

    # Check outcome
    final_filing = Filing.find_by_id(filing_id)
    assert filing["filing"]["restoration"]["approvalType"] == final_filing.approval_type
    if approval_type == "registrar":
        assert final_filing.application_date == datetime.fromisoformat(f"{application_date}T08:00:00+00:00")
        assert final_filing.notice_date == datetime.fromisoformat(f"{notice_date}T07:00:00+00:00")
        assert application_date == LegislationDatetime.format_as_legislation_date(final_filing.application_date)
        assert notice_date == LegislationDatetime.format_as_legislation_date(final_filing.notice_date)
    else:
        assert final_filing.application_date is None
        assert final_filing.notice_date is None


def test_restoration_name_translations(app, session, mocker):
    """Assert the worker process the name translations correctly."""
    identifier = "BC1234567"
    business = create_business(identifier, legal_type=legal_type, legal_name=legal_name)
    business.save()
    business_id = business.id
    filing = copy.deepcopy(FILING_HEADER)
    filing["filing"]["restoration"] = copy.deepcopy(RESTORATION)
    filing["filing"]["header"]["name"] = "restoration"
    del filing["filing"]["restoration"]["parties"][0]["officer"]["id"]

    payment_id = str(random.SystemRandom().getrandbits(0x58))

    filing_id = (create_filing(payment_id, filing, business_id=business_id)).id
    filing_msg = FilingMessage(filing_identifier=filing_id)

    _mock_out(mocker)

    process_filing(filing_msg)

    # Check outcome
    assert filing["filing"]["restoration"]["nameTranslations"] == [{"name": "ABCD Ltd."}]
    assert business.aliases is not None


def test_update_party(app, session, mocker):
    """Assert the worker process the party correctly."""

    versioned_session(session)
    with nested_session(session):
        identifier = "BC1234567"
        business = create_business(identifier, legal_type=legal_type, legal_name=legal_name)
        business.save()
        business_id = business.id
        filing = copy.deepcopy(FILING_HEADER)
        filing["filing"]["restoration"] = copy.deepcopy(RESTORATION)
        filing["filing"]["header"]["name"] = "restoration"
        del filing["filing"]["restoration"]["parties"][0]["officer"]["id"]

        payment_id = str(random.SystemRandom().getrandbits(0x58))

        filing_id = (create_filing(payment_id, filing, business_id=business_id)).id
        filing_msg = FilingMessage(filing_identifier=filing_id)

        _mock_out(mocker)

        member = LegalEntity(
            first_name="Michael",
            last_name="Crane",
            middle_initial="Joe",
            title="VP",
            entity_type=LegalEntity.EntityTypes.PERSON,
        )
        member.save()
        assert member.id

        party_role = EntityRole(
            role_type=EntityRole.RoleTypes.custodian.value,
            appointment_date=datetime(2017, 5, 17),
            cessation_date=None,
            related_entity_id=member.id,
            legal_entity_id=business_id,
            change_filing_id=None,
            filing_id=None,
        )
        party_role.save()

        process_filing(filing_msg)

        # Check outcome
        # TODO by business not filing
        historical_roles = EntityRole.get_entity_roles_history_for_entity(entity_id=business_id)
        number_of_historical_roles = len(historical_roles)
        assert number_of_historical_roles == 2
        assert historical_roles[1].cessation_date

        filing_rec = Filing.find_by_id(filing_id)
        party_roles = filing_rec.filing_entity_roles.all()
        assert len(party_roles) == 1
        party_role = party_roles[0]
        assert party_role.role_type == EntityRole.RoleTypes.applicant.value
        assert (
            party_role.related_entity.first_name
            == filing["filing"]["restoration"]["parties"][0]["officer"]["firstName"].upper()
        )
        assert (
            party_role.delivery_address.street
            == filing["filing"]["restoration"]["parties"][0]["deliveryAddress"]["streetAddress"]
        )
        assert (
            party_role.mailing_address.street
            == filing["filing"]["restoration"]["parties"][0]["mailingAddress"]["streetAddress"]
        )


def _mock_out(mocker):
    # mocker.patch('entity_filer.worker.publish_email_message', return_value=None)
    # mocker.patch('entity_filer.worker.publish_event', return_value=None)
    mocker.patch(
        "entity_filer.filing_processors.filing_components.name_request.consume_nr",
        return_value=None,
    )
    # mocker.patch('entity_filer.filing_processors.filing_components.business_profile.update_business_profile',
    #              return_value=None)
    # mocker.patch('legal_api.services.bootstrap.AccountService.update_entity', return_value=None)
