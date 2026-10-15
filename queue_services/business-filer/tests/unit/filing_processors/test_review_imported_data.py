# Copyright © 2026 Province of British Columbia
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
"""Tests for Review Imported Data filing processing."""
import copy
from datetime import UTC, datetime

import pytest
from business_model.models import Address, Filing, Office, OfficeType, Party, PartyRole
from registry_schemas.example_data import FILING_TEMPLATE

from business_filer.exceptions import QueueException
from business_filer.filing_meta import FilingMeta
from business_filer.filing_processors import review_imported_data
from business_filer.filing_processors.filing_components import create_address
from tests.unit import create_business


def _address(street: str) -> dict:
    return {
        "streetAddress": street,
        "addressCity": "delivery_address city",
        "addressCountry": "CA",
        "addressRegion": "BC",
        "postalCode": "H0H0H0",
    }


def _filing(payload: dict) -> Filing:
    filing_json = copy.deepcopy(FILING_TEMPLATE)
    filing_json["filing"]["header"]["name"] = "reviewImportedData"
    filing_json["filing"]["reviewImportedData"] = payload
    return Filing(filing_json=filing_json)


def _process(business, payload: dict) -> FilingMeta:
    filing_meta = FilingMeta(application_date=datetime(2026, 1, 2, tzinfo=UTC))
    review_imported_data.process(business, _filing(payload), filing_meta)
    return filing_meta



def _add_director(business, session, cessation_date=None):
    party = Party(first_name="Phillip Tandy", last_name="Miller")
    party.delivery_address = create_address(_address("Old director delivery"), Address.DELIVERY)
    party.mailing_address = create_address(_address("Old director mailing"), Address.MAILING)
    party.save()
    role = PartyRole(
        role=PartyRole.RoleTypes.DIRECTOR.value,
        appointment_date=datetime(2020, 1, 1, tzinfo=UTC),
        cessation_date=cessation_date,
        party_id=party.id,
        business_id=business.id,
    )
    role.save()
    session.refresh(party)
    return party, role


@pytest.fixture
def business(session):
    return create_business("BC1234567", legal_type="BC", legal_name="Example Ltd.")


def test_process_offices_only(app, session, business):
    """Update registered office addresses while leaving other business dates unchanged."""
    office = business.offices.filter_by(office_type=OfficeType.REGISTERED).one()
    business.last_coa_date = datetime(2024, 1, 1, tzinfo=UTC)

    filing_meta = _process(business, {
        "offices": {
            "registeredOffice": {
                "deliveryAddress": _address("New delivery"),
                "mailingAddress": _address("New mailing"),
            }
        }
    })

    assert office.addresses.filter_by(address_type=Address.DELIVERY).one().street == "New delivery"
    assert office.addresses.filter_by(address_type=Address.MAILING).one().street == "New mailing"
    assert business.last_coa_date == datetime(2024, 1, 1, tzinfo=UTC)
    assert filing_meta.asjson["reviewImportedData"]["sectionsChanged"] == ["offices"]


def test_process_records_office_only(app, session, business):
    """Create a missing records office without changing the registered office."""
    registered_office = business.offices.filter_by(office_type=OfficeType.REGISTERED).one()
    registered_delivery = registered_office.addresses.filter_by(address_type=Address.DELIVERY).one()
    original_registered_street = registered_delivery.street

    filing_meta = _process(business, {
        "offices": {
            "recordsOffice": {
                "deliveryAddress": _address("New records delivery"),
                "mailingAddress": _address("New records mailing"),
            }
        }
    })

    records_office = business.offices.filter_by(office_type=OfficeType.RECORDS).one()
    assert records_office.addresses.filter_by(address_type=Address.DELIVERY).one().street == "New records delivery"
    assert records_office.addresses.filter_by(address_type=Address.MAILING).one().street == "New records mailing"
    assert registered_delivery.street == original_registered_street
    assert filing_meta.asjson["reviewImportedData"]["sectionsChanged"] == ["offices"]


def test_process_directors_only_ignores_names_and_preserves_missing_address(app, session, business):
    """Update one submitted director address without changing names or the omitted address."""
    party, role = _add_director(business, session)
    original_appointment_date = role.appointment_date

    filing_meta = _process(business, {
        "relationships": [{
            "entity": {
                "identifier": str(party.id),
                "givenName": "Changed",
                "familyName": "Name",
            },
            "deliveryAddress": _address("New director delivery"),
            "mailingAddress": _address("New director mailing"),
            "roles": [{"roleType": "Director", "appointmentDate": "2026-01-01"}],
        }]
    })

    assert party.mailing_address.street == "New director mailing"
    assert party.delivery_address.street == "New director delivery"
    assert party.first_name == "Phillip Tandy"
    assert party.last_name == "Miller"
    assert role.appointment_date == original_appointment_date
    assert role.cessation_date is None
    assert business.last_cod_date is None
    assert filing_meta.asjson["reviewImportedData"]["sectionsChanged"] == ["directors"]


def test_process_offices_and_directors(app, session, business):
    """Update both filing sections and record both sections in metadata."""
    party, _ = _add_director(business, session)
    office = business.offices.filter_by(office_type=OfficeType.REGISTERED).one()

    filing_meta = _process(business, {
        "offices": {"registeredOffice": {
            "deliveryAddress": _address("New office delivery"),
            "mailingAddress": _address("New office mailing"),
        }},
        "relationships": [{
            "entity": {"identifier": str(party.id)},
            "deliveryAddress": _address("New director delivery"),
        }],
    })

    assert office.addresses.filter_by(address_type=Address.DELIVERY).one().street == "New office delivery"
    assert party.delivery_address.street == "New director delivery"
    assert filing_meta.asjson["reviewImportedData"]["sectionsChanged"] == ["offices", "directors"]


def test_process_partial_director_address_leaves_other_address_unchanged(app, session, business):
    """Leave an omitted director address untouched when updating the supplied address."""
    party, _ = _add_director(business, session)
    original_delivery = party.delivery_address.street

    _process(business, {"relationships": [{
        "entity": {"identifier": str(party.id)},
        "mailingAddress": _address("New director mailing"),
        "roles": [{"roleType": "Director"}],
    }]})

    assert party.delivery_address.street == original_delivery
    assert party.mailing_address.street == "New director mailing"


def test_process_unknown_director_identifier_raises(app, session, business):
    """Reject an identifier that does not resolve to a party role."""
    with pytest.raises(QueueException) as exc_info:
        _process(business, {"relationships": [{"entity": {"identifier": "999999"}}]})
    assert "Could not find active director" in exc_info.value.error


def test_process_ceased_director_identifier_raises(app, session, business):
    """Reject a director whose role has been ceased."""
    party, _ = _add_director(business, session, cessation_date=datetime(2025, 1, 1, tzinfo=UTC))

    with pytest.raises(QueueException) as exc_info:
        _process(business, {"relationships": [{"entity": {"identifier": str(party.id)}}]})
    assert "Could not find active director" in exc_info.value.error
