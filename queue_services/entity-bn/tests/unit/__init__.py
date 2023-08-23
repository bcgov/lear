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
"""The Unit Tests and the helper routines."""
import base64
import copy
from datetime import datetime

from simple_cloudevent import SimpleCloudEvent, to_queue_message

from tests import EPOCH_DATETIME


def create_filing(
    token=None,
    json_filing=None,
    legal_entity_id=None,
    filing_date=EPOCH_DATETIME,
):
    """Return a test filing."""
    from legal_api.models import Filing

    filing = Filing()
    filing.filing_date = filing_date

    if token:
        filing.payment_token = str(token)
    if json_filing:
        filing.filing_json = json_filing
    if legal_entity_id:
        filing.legal_entity_id = legal_entity_id

    return filing


def create_legal_entity(
    identifier,
    legal_type=None,
    legal_name=None,
    bn9=None,
    tax_id=None,
    change_filing_id=None,
):
    """Return a test legal_entity."""
    from legal_api.models import LegalEntity

    legal_entity = LegalEntity()
    legal_entity.identifier = identifier
    legal_entity.entity_type = legal_type
    legal_entity.bn9 = bn9
    legal_entity.change_filing_id = change_filing_id

    alternate_name = create_alternate_name(operating_name=legal_name, tax_id=tax_id)
    alternate_name.change_filing_id = change_filing_id
    legal_entity.alternate_names.append(alternate_name)

    office = create_business_address(change_filing_id=change_filing_id)
    legal_entity.offices.append(office)

    return legal_entity


def create_alternate_name(operating_name, tax_id=None):
    """Create operating name."""
    from legal_api.models import AlternateName

    alternate_name = AlternateName(
        # identifier="BC1234567",
        name_type=AlternateName.NameType.OPERATING,
        name=operating_name,
        bn15=tax_id,
        start_date=datetime.utcnow(),
    )
    return alternate_name


def create_business_address(office_type="businessOffice", change_filing_id=None):
    """Create an address."""
    from legal_api.models import Address, Office

    office = Office(office_type=office_type)
    office.change_filing_id = change_filing_id

    office.addresses.append(create_office(Address.DELIVERY))
    office.addresses.append(create_office(Address.MAILING))

    return office


def create_office(type):
    """Create an office."""
    from legal_api.models import Address

    address = Address(
        city="Test City",
        street="Test Street",
        postal_code="T3S3T3",
        country="CA",
        region="BC",
        address_type=type,
    )
    return address


def create_related_entity(party_json):
    """Create a party."""
    from legal_api.models import Address, LegalEntity

    new_party = LegalEntity()
    new_party.first_name = party_json["officer"].get("firstName", "").upper()
    new_party.last_name = party_json["officer"].get("lastName", "").upper()
    new_party.middle_initial = party_json["officer"].get("middleInitial", "").upper()
    new_party.title = party_json.get("title", "").upper()
    new_party._legal_name = party_json["officer"].get("organizationName", "").upper()
    new_party.email = party_json["officer"].get("email")
    new_party.entity_type = party_json["officer"].get("entityType")
    new_party.identifier = party_json["officer"].get("identifier")
    new_party.tax_id = party_json["officer"].get("taxId")

    if party_json.get("mailingAddress"):
        mailing_address = Address(
            street=party_json["mailingAddress"]["streetAddress"],
            city=party_json["mailingAddress"]["addressCity"],
            country="CA",
            postal_code=party_json["mailingAddress"]["postalCode"],
            region=party_json["mailingAddress"]["addressRegion"],
            delivery_instructions=party_json["mailingAddress"]
            .get("deliveryInstructions", "")
            .upper(),
        )
        new_party.entity_mailing_address = mailing_address
    if party_json.get("deliveryAddress"):
        delivery_address = Address(
            street=party_json["deliveryAddress"]["streetAddress"],
            city=party_json["deliveryAddress"]["addressCity"],
            country="CA",
            postal_code=party_json["deliveryAddress"]["postalCode"],
            region=party_json["deliveryAddress"]["addressRegion"],
            delivery_instructions=party_json["deliveryAddress"]
            .get("deliveryInstructions", "")
            .upper(),
        )
        new_party.entity_delivery_address = delivery_address
    return new_party


def create_entity_role(
    legal_entity, related_entity, roles, appointment_date=EPOCH_DATETIME
):
    """Create party roles."""
    from legal_api.models import EntityRole

    for role in roles:
        entity_role = EntityRole(
            role_type=role,
            related_entity=related_entity,
            appointment_date=appointment_date,
            cessation_date=None,
        )
        legal_entity.entity_roles.append(entity_role)


def create_registration_data(legal_type, identifier="FM1234567", bn9=None, tax_id=None):
    """Test data for registration."""
    person_json = {
        "officer": {
            "id": 2,
            "firstName": "Peter",
            "lastName": "Griffin",
            "middleName": "",
            "entityType": "person",
        },
        "mailingAddress": {
            "streetAddress": "mailing_address - address line one",
            "streetAddressAdditional": "",
            "addressCity": "mailing_address city",
            "addressCountry": "CA",
            "postalCode": "H0H0H0",
            "addressRegion": "BC",
        },
    }

    org_json = copy.deepcopy(person_json)
    org_json["officer"] = {
        "id": 2,
        "organizationName": "Xyz Inc.",
        "identifier": "BC1234567",
        "taxId": "123456789",
        "email": "peter@email.com",
        "entityType": "organization",
    }

    json_filing = {"filing": {"header": {"name": "registration"}, "registration": {}}}
    filing = create_filing(json_filing=json_filing)
    filing.save()

    legal_entity = create_legal_entity(
        identifier,
        legal_type=legal_type,
        legal_name="test-reg-" + legal_type,
        tax_id=tax_id,
        change_filing_id=filing.id,
    )

    related_entity = create_related_entity(
        person_json if legal_type == "SP" else org_json
    )
    role = "proprietor" if legal_type == "SP" else "partner"
    create_entity_role(legal_entity, related_entity, [role])
    legal_entity.save()

    filing.legal_entity_id = legal_entity.id
    filing.save()

    return filing.id, legal_entity.id


def get_json_message(
    filing_id, identifier, message_id, type, request_type=None, business_number=None
):
    CLOUD_EVENT = SimpleCloudEvent(
        source="fake-for-tests",
        subject="fake-subject",
        id=message_id,
        type=type,
        data={
            "filingId": filing_id,
            "identifier": identifier,
            "request": request_type,
            "businessNumber": business_number,
        },
    )

    json_data = {
        "subscription": "projects/PUBSUB_PROJECT_ID/subscriptions/SUBSCRIPTION_ID",
        "message": {
            "data": base64.b64encode(to_queue_message(CLOUD_EVENT)).decode("utf-8"),
        },
    }
    return json_data
