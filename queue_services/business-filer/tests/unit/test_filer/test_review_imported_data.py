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
"""Filer dispatch tests for Review Imported Data."""
import copy
from datetime import UTC, datetime

from business_model.models import Business, Filing
from registry_schemas.example_data import FILING_TEMPLATE

from business_filer.common.filing_message import FilingMessage
from business_filer.services.filer import process_filing
from tests.unit import create_business, create_filing, create_party, create_party_role


def test_process_filing_review_imported_data(app, session):
    """Apply submitted office addresses and complete a Review Imported Data filing."""
    business = create_business("BC1234567", legal_type="BC", legal_name="Example Ltd.")
    filing_json = copy.deepcopy(FILING_TEMPLATE)
    filing_json["filing"]["header"]["name"] = "reviewImportedData"
    filing_json["filing"]["business"]["identifier"] = business.identifier
    filing_json["filing"]["reviewImportedData"] = {
        "offices": {
            "registeredOffice": {
                "deliveryAddress": {
                    "streetAddress": "New delivery",
                    "addressCity": "Victoria",
                    "addressCountry": "CA",
                    "addressRegion": "BC",
                    "postalCode": "V8V 1A1",
                },
                "mailingAddress": {
                    "streetAddress": "New mailing",
                    "addressCity": "Victoria",
                    "addressCountry": "CA",
                    "addressRegion": "BC",
                    "postalCode": "V8V 1A1",
                },
            }
        }
    }
    filing = create_filing("review-imported-data", filing_json, business.id)

    process_filing(FilingMessage(filing_identifier=filing.id))

    completed_filing = Filing.find_by_id(filing.id)
    updated_business = Business.find_by_internal_id(business.id)
    registered_office = updated_business.offices.filter_by(office_type="registeredOffice").one()

    assert completed_filing.status == Filing.Status.COMPLETED.value
    assert completed_filing.transaction_id
    assert completed_filing.meta_data["reviewImportedData"]["sectionsChanged"] == ["offices"]
    assert registered_office.addresses.filter_by(address_type="delivery").one().street == "New delivery"
    assert registered_office.addresses.filter_by(address_type="mailing").one().street == "New mailing"
    assert updated_business.last_modified == completed_filing.completion_date


def test_process_filing_review_imported_data_director_addresses(app, session):
    """Update a director's addresses without changing their name."""
    business = create_business("BC1234568", legal_type="BC", legal_name="Example Ltd.")
    party = create_party({
        "officer": {"firstName": "Phillip Tandy", "lastName": "Miller"},
        "deliveryAddress": {
            "streetAddress": "delivery_address - address line one",
            "addressCity": "delivery_address city",
            "addressCountry": "CA",
            "addressRegion": "BC",
            "postalCode": "H0H0H0",
        },
        "mailingAddress": {
            "streetAddress": "mailing_address - address line one",
            "addressCity": "mailing_address city",
            "addressCountry": "CA",
            "addressRegion": "BC",
            "postalCode": "H0H0H0",
        },
    })
    create_party_role(business, party, ["director"], datetime(2020, 1, 1, tzinfo=UTC))

    filing_json = copy.deepcopy(FILING_TEMPLATE)
    filing_json["filing"]["header"]["name"] = "reviewImportedData"
    filing_json["filing"]["business"]["identifier"] = business.identifier
    filing_json["filing"]["reviewImportedData"] = {
        "relationships": [{
            "entity": {
                "identifier": str(party.id),
                "givenName": "Changed",
                "middleInitial": "Tandy",
                "familyName": "Miller",
                "alternateName": "Phil Mills",
            },
            "deliveryAddress": {
                "streetAddress": "Changed Delivery",
                "streetAddressAdditional": "",
                "addressCity": "Vancouver",
                "addressCountry": "CA",
                "addressRegion": "BC",
                "postalCode": "V0N4Y8",
                "deliveryInstructions": "",
            },
            "mailingAddress": {
                "streetAddress": "Changed Mailing",
                "streetAddressAdditional": "",
                "addressCity": "Vancouver",
                "addressCountry": "CA",
                "addressRegion": "BC",
                "postalCode": "V0N4Y8",
                "deliveryInstructions": "",
            },
            "roles": [{"roleType": "Director"}],
        }]
    }
    filing = create_filing("review-imported-data-director", filing_json, business.id)

    process_filing(FilingMessage(filing_identifier=filing.id))

    completed_filing = Filing.find_by_id(filing.id)
    updated_business = Business.find_by_internal_id(business.id)
    director_role = updated_business.party_roles.filter_by(party_id=party.id, role="director").one()

    assert completed_filing.status == Filing.Status.COMPLETED.value
    assert completed_filing.transaction_id
    assert completed_filing.meta_data["reviewImportedData"]["sectionsChanged"] == ["directors"]
    assert director_role.party.first_name == "PHILLIP TANDY"
    assert director_role.party.last_name == "MILLER"
    assert director_role.party.delivery_address.street == "Changed Delivery"
    assert director_role.party.mailing_address.street == "Changed Mailing"
