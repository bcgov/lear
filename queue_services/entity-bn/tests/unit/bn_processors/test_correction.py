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
"""The Test Suites to ensure that the correction of registration or change of registration is operating correctly."""
from http import HTTPStatus
import uuid
import xml.etree.ElementTree as Et

import pytest
from legal_api.models import RequestTracker

from entity_bn.bn_processors import bn_note
from tests.unit import create_filing, create_registration_data, get_json_message


message_type = "bc.registry.business.correction"


@pytest.mark.parametrize(
    "legal_type",
    [
        ("SP"),
        ("GP"),
    ],
)
def test_correction(app, session, client, mocker, legal_type):
    """Test inform cra about correction of SP/GP."""
    identifier = "FM1234567"
    filing_id, legal_entity_id = create_registration_data(
        legal_type, identifier=identifier, tax_id="993775204BC0001"
    )
    json_filing = {
        "filing": {
            "header": {"name": "correction"},
            "correction": {
                "offices": {
                    "businessOffice": {"mailingAddress": {}, "deliveryAddress": {}}
                },
                "parties": [{}],
            },
        }
    }
    filing = create_filing(json_filing=json_filing, legal_entity_id=legal_entity_id)
    filing._meta_data = {"correction": {"toLegalName": "new name"}}
    filing.save()
    filing_id = filing.id

    acknowledgement_response = """<?xml version="1.0"?>
        <SBNAcknowledgement>
            <header></header>
            <body>A Valid Document Type was received.</body>
        </SBNAcknowledgement>"""

    def side_effect(input_xml):
        root = Et.fromstring(input_xml)
        if root.tag in ["SBNChangeName", "SBNChangeAddress"]:
            return 200, acknowledgement_response

    mocker.patch(
        "entity_bn.bn_processors.change_of_registration.request_bn_hub",
        side_effect=side_effect,
    )
    mocker.patch(
        "entity_bn.bn_processors.correction.has_previous_address", return_value=True
    )
    mocker.patch(
        "entity_bn.bn_processors.correction.has_party_name_changed", return_value=True
    )

    message_id = str(uuid.uuid4())
    json_data = get_json_message(filing_id, identifier, message_id, message_type)
    rv = client.post("/", json=json_data)
    assert rv.status_code == HTTPStatus.OK

    request_trackers = RequestTracker.find_by(
        legal_entity_id,
        RequestTracker.ServiceName.BN_HUB,
        RequestTracker.RequestType.CHANGE_NAME,
        filing_id=filing_id,
    )
    assert request_trackers
    assert len(request_trackers) == 1
    assert request_trackers[0].is_processed
    assert request_trackers[0].retry_number == 0

    request_trackers = RequestTracker.find_by(
        legal_entity_id,
        RequestTracker.ServiceName.BN_HUB,
        RequestTracker.RequestType.CHANGE_PARTY,
        filing_id=filing_id,
    )
    assert request_trackers
    assert len(request_trackers) == 1
    assert request_trackers[0].is_processed
    assert request_trackers[0].retry_number == 0

    request_trackers = RequestTracker.find_by(
        legal_entity_id,
        RequestTracker.ServiceName.BN_HUB,
        RequestTracker.RequestType.CHANGE_DELIVERY_ADDRESS,
        filing_id=filing_id,
    )
    assert request_trackers
    assert len(request_trackers) == 1
    assert request_trackers[0].is_processed
    assert request_trackers[0].retry_number == 0

    request_trackers = RequestTracker.find_by(
        legal_entity_id,
        RequestTracker.ServiceName.BN_HUB,
        RequestTracker.RequestType.CHANGE_MAILING_ADDRESS,
        filing_id=filing_id,
    )
    assert request_trackers
    assert len(request_trackers) == 1
    assert request_trackers[0].is_processed
    assert request_trackers[0].retry_number == 0


@pytest.mark.parametrize(
    "legal_type, bn9",
    [
        ("SP", None),
        ("SP", ""),
        ("SP", "993775204"),
        ("GP", None),
        ("GP", ""),
        ("GP", "993775204"),
    ],
)
def test_bn15_not_available_correction(app, session, client, mocker, legal_type, bn9):
    """Skip cra call when BN15 is not available while doing a correction of SP/GP."""
    identifier = "FM1234567"
    filing_id, legal_entity_id = create_registration_data(
        legal_type, identifier=identifier, bn9=bn9
    )
    json_filing = {
        "filing": {
            "header": {"name": "correction"},
            "correction": {
                "offices": {
                    "businessOffice": {"mailingAddress": {}, "deliveryAddress": {}}
                },
                "parties": [{}],
            },
        }
    }
    filing = create_filing(json_filing=json_filing, legal_entity_id=legal_entity_id)
    filing._meta_data = {"correction": {"toLegalName": "new name"}}
    filing.save()
    filing_id = filing.id

    mocker.patch(
        "entity_bn.bn_processors.correction.has_previous_address", return_value=True
    )
    mocker.patch(
        "entity_bn.bn_processors.correction.has_party_name_changed", return_value=True
    )

    message_id = str(uuid.uuid4())
    json_data = get_json_message(filing_id, identifier, message_id, message_type)
    rv = client.post("/", json=json_data)
    assert rv.status_code == HTTPStatus.OK

    request_trackers = RequestTracker.find_by(
        legal_entity_id,
        RequestTracker.ServiceName.BN_HUB,
        RequestTracker.RequestType.CHANGE_NAME,
        filing_id=filing_id,
    )
    assert request_trackers
    assert len(request_trackers) == 1
    assert not request_trackers[0].is_processed
    assert request_trackers[0].response_object == bn_note
    assert request_trackers[0].retry_number == 0

    request_trackers = RequestTracker.find_by(
        legal_entity_id,
        RequestTracker.ServiceName.BN_HUB,
        RequestTracker.RequestType.CHANGE_PARTY,
        filing_id=filing_id,
    )
    assert request_trackers
    assert len(request_trackers) == 1
    assert not request_trackers[0].is_processed
    assert request_trackers[0].response_object == bn_note
    assert request_trackers[0].retry_number == 0

    request_trackers = RequestTracker.find_by(
        legal_entity_id,
        RequestTracker.ServiceName.BN_HUB,
        RequestTracker.RequestType.CHANGE_DELIVERY_ADDRESS,
        filing_id=filing_id,
    )
    assert request_trackers
    assert len(request_trackers) == 1
    assert not request_trackers[0].is_processed
    assert request_trackers[0].response_object == bn_note
    assert request_trackers[0].retry_number == 0

    request_trackers = RequestTracker.find_by(
        legal_entity_id,
        RequestTracker.ServiceName.BN_HUB,
        RequestTracker.RequestType.CHANGE_MAILING_ADDRESS,
        filing_id=filing_id,
    )
    assert request_trackers
    assert len(request_trackers) == 1
    assert not request_trackers[0].is_processed
    assert request_trackers[0].response_object == bn_note
    assert request_trackers[0].retry_number == 0


@pytest.mark.parametrize(
    "request_type, data",
    [
        (
            RequestTracker.RequestType.CHANGE_NAME,
            {"nameRequest": {"legalName": "new name"}},
        ),
        (RequestTracker.RequestType.CHANGE_PARTY, {"parties": [{}]}),
        (
            RequestTracker.RequestType.CHANGE_DELIVERY_ADDRESS,
            {
                "offices": {
                    "businessOffice": {"mailingAddress": {}, "deliveryAddress": {}}
                }
            },
        ),
        (
            RequestTracker.RequestType.CHANGE_MAILING_ADDRESS,
            {
                "offices": {
                    "businessOffice": {"mailingAddress": {}, "deliveryAddress": {}}
                }
            },
        ),
    ],
)
def test_retry_correction(app, session, client, mocker, request_type, data):
    """Test retry correction of SP/GP."""
    identifier = "FM1234567"
    filing_id, legal_entity_id = create_registration_data(
        "SP", identifier=identifier, tax_id="993775204BC0001"
    )
    json_filing = {"filing": {"header": {"name": "correction"}, "correction": {}}}
    json_filing["filing"]["correction"] = data
    filing = create_filing(json_filing=json_filing, legal_entity_id=legal_entity_id)
    if request_type == RequestTracker.RequestType.CHANGE_NAME:
        filing._meta_data = {"correction": {"toLegalName": "new name"}}
    filing.save()
    filing_id = filing.id

    mocker.patch(
        "entity_bn.bn_processors.change_of_registration.request_bn_hub",
        return_value=(500, ""),
    )

    def side_effect(transaction_id, office_id, address_type):
        if address_type in request_type.name.lower():
            return True
        return False

    mocker.patch(
        "entity_bn.bn_processors.correction.has_previous_address",
        side_effect=side_effect,
    )
    mocker.patch(
        "entity_bn.bn_processors.correction.has_party_name_changed", return_value=True
    )

    message_id = str(uuid.uuid4())
    for _ in range(10):
        json_data = get_json_message(filing_id, identifier, message_id, message_type)
        rv = client.post("/", json=json_data)

        if rv.status_code == HTTPStatus.OK:
            break

    request_trackers = RequestTracker.find_by(
        legal_entity_id,
        RequestTracker.ServiceName.BN_HUB,
        request_type,
        filing_id=filing_id,
    )
    assert request_trackers
    assert len(request_trackers) == 1
    assert request_trackers[0].is_processed is False
    assert request_trackers[0].retry_number == 9
