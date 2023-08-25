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
"""The Test Suites to ensure that the registration is operating correctly."""
from http import HTTPStatus
import uuid
import xml.etree.ElementTree as Et

import pytest
from legal_api.models import LegalEntity, RequestTracker

from tests.unit import get_json_message, create_registration_data


acknowledgement_response = """<?xml version="1.0"?>
    <SBNAcknowledgement>
        <header>
            <transactionID>BNTUQ0E1OC0</transactionID>
        </header>
        <body>A Valid SBNCreateProgramAccountRequest Document Type was received.</body>
    </SBNAcknowledgement>"""

message_type = "bc.registry.business.registration"


@pytest.mark.parametrize(
    "legal_type",
    [
        ("SP"),
        ("GP"),
    ],
)
def test_registration(app, session, client, mocker, legal_type):
    """Test inform cra about new SP/GP registration."""
    identifier = "FM1234567"
    filing_id, legal_entity_id = create_registration_data(
        legal_type, identifier=identifier
    )

    def side_effect(input_xml):
        root = Et.fromstring(input_xml)
        if root.tag == "SBNCreateProgramAccountRequest":
            return 200, acknowledgement_response

    mocker.patch(
        "entity_bn.bn_processors.registration.request_bn_hub", side_effect=side_effect
    )
    # mocker.patch("entity_bn.bn_processors.registration.publish_event")

    business_number = "993775204"
    business_program_id = "BC"
    program_account_ref_no = 1
    mocker.patch(
        "entity_bn.bn_processors.registration._get_program_account",
        return_value=(
            200,
            {
                "business_no": business_number,
                "business_program_id": business_program_id,
                "cross_reference_program_no": identifier,
                "program_account_ref_no": program_account_ref_no,
            },
        ),
    )

    message_id = str(uuid.uuid4())
    json_data = get_json_message(filing_id, identifier, message_id, message_type)
    rv = client.post("/", json=json_data)
    assert rv.status_code == HTTPStatus.OK

    request_trackers = RequestTracker.find_by(
        legal_entity_id,
        RequestTracker.ServiceName.BN_HUB,
        RequestTracker.RequestType.INFORM_CRA,
    )
    assert request_trackers
    assert len(request_trackers) == 1
    assert request_trackers[0].is_processed
    assert request_trackers[0].retry_number == 0

    request_trackers = RequestTracker.find_by(
        legal_entity_id,
        RequestTracker.ServiceName.BN_HUB,
        RequestTracker.RequestType.GET_BN,
    )
    assert request_trackers
    assert len(request_trackers) == 1
    assert request_trackers[0].is_processed
    assert request_trackers[0].retry_number == 0

    legal_entity = LegalEntity.find_by_internal_id(legal_entity_id)
    assert (
        legal_entity.alternate_names.first().bn15
        == f"{business_number}{business_program_id}{str(program_account_ref_no).zfill(4)}"
    )


@pytest.mark.parametrize(
    "request_type",
    [
        (RequestTracker.RequestType.INFORM_CRA),
        (RequestTracker.RequestType.GET_BN),
    ],
)
def test_retry_registration(app, session, client, mocker, request_type):
    """Test retry new SP/GP registration."""
    is_inform_cra = request_type == RequestTracker.RequestType.INFORM_CRA
    identifier = "FM1234567"
    filing_id, legal_entity_id = create_registration_data("SP", identifier=identifier)

    def side_effect(input_xml):
        root = Et.fromstring(input_xml)
        if root.tag == "SBNCreateProgramAccountRequest":
            return 200, "" if is_inform_cra else acknowledgement_response

    mocker.patch(
        "entity_bn.bn_processors.registration.request_bn_hub", side_effect=side_effect
    )
    mocker.patch(
        "entity_bn.bn_processors.registration._get_program_account",
        return_value=(
            500,
            {"message": "Error when trying to retrieve program account from COLIN"},
        ),
    )
    # mocker.patch("entity_bn.bn_processors.registration.publish_event")

    message_id = str(uuid.uuid4())
    for _ in range(10):
        json_data = get_json_message(filing_id, identifier, message_id, message_type)
        rv = client.post("/", json=json_data)

        if rv.status_code == HTTPStatus.OK:
            break

    request_trackers = RequestTracker.find_by(
        legal_entity_id,
        RequestTracker.ServiceName.BN_HUB,
        RequestTracker.RequestType.INFORM_CRA,
    )
    assert request_trackers
    assert len(request_trackers) == 1
    assert request_trackers[0].is_processed is (False if is_inform_cra else True)
    assert request_trackers[0].retry_number == (9 if is_inform_cra else 0)

    request_trackers = RequestTracker.find_by(
        legal_entity_id,
        RequestTracker.ServiceName.BN_HUB,
        RequestTracker.RequestType.GET_BN,
    )

    if is_inform_cra:
        assert not request_trackers
    else:
        assert len(request_trackers) == 1
        assert request_trackers[0].is_processed is False
        assert request_trackers[0].retry_number == 9
