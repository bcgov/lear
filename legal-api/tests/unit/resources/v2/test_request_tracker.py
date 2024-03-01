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

"""Tests to assure the request tracker end-point.

Test-Suite to ensure that the /requestTracker endpoint is working as expected.
"""
from contextlib import suppress
from http import HTTPStatus
from unittest.mock import patch

import pytest

from legal_api.models import LegalEntity, RequestTracker, UserRoles
from legal_api.resources.v2 import request_tracker
from tests.unit import nested_session
from tests.unit.models import factory_legal_entity
from tests.unit.services.utils import create_header


def test_get_bn_request_trackers(session, client, jwt):
    """Get all BN request."""
    with nested_session(session):
        identifier = "FM0000001"
        legal_entity = factory_legal_entity(identifier, _entity_type=LegalEntity.EntityTypes.SOLE_PROP.value)

        request_tracker = RequestTracker(
            request_type=RequestTracker.RequestType.INFORM_CRA,
            retry_number=-1,
            service_name=RequestTracker.ServiceName.BN_HUB,
            legal_entity_id=legal_entity.id,
            request_object="<SBNCreateProgramAccountRequest></SBNCreateProgramAccountRequest>",
        )
        request_tracker.save()

        rv = client.get(
            f"/api/v2/requestTracker/bn/{identifier}", headers=create_header(jwt, [UserRoles.bn_edit], identifier)
        )

        assert rv.status_code == HTTPStatus.OK
        assert rv.json["requestTrackers"][0]["id"] == request_tracker.id
        assert rv.json["requestTrackers"][0]["requestType"] == request_tracker.request_type.name
        assert rv.json["requestTrackers"][0]["isProcessed"] == request_tracker.is_processed
        assert rv.json["requestTrackers"][0]["serviceName"] == request_tracker.service_name.name
        assert rv.json["requestTrackers"][0]["isAdmin"] == request_tracker.is_admin


def test_get_request_tracker(session, client, jwt):
    """Get request tracker."""
    with nested_session(session):
        identifier = "FM0000001"
        legal_entity = factory_legal_entity(identifier, _entity_type=LegalEntity.EntityTypes.SOLE_PROP.value)

        request_tracker = RequestTracker(
            request_type=RequestTracker.RequestType.INFORM_CRA,
            retry_number=-1,
            service_name=RequestTracker.ServiceName.BN_HUB,
            legal_entity_id=legal_entity.id,
            request_object="<SBNCreateProgramAccountRequest></SBNCreateProgramAccountRequest>",
            response_object="<SBNAcknowledgement></SBNAcknowledgement>",
        )
        request_tracker.save()

        rv = client.get(
            f"/api/v2/requestTracker/{request_tracker.id}", headers=create_header(jwt, [UserRoles.bn_edit], identifier)
        )

        assert rv.status_code == HTTPStatus.OK
        assert rv.json["id"] == request_tracker.id
        assert rv.json["requestType"] == request_tracker.request_type.name
        assert rv.json["isProcessed"] == request_tracker.is_processed
        assert rv.json["serviceName"] == request_tracker.service_name.name
        assert rv.json["isAdmin"] == request_tracker.is_admin
        assert rv.json["request"] == request_tracker.request_object
        assert rv.json["response"] == request_tracker.response_object


@pytest.mark.parametrize(
    "request_type, request_xml, identifier",
    [
        (RequestTracker.RequestType.INFORM_CRA, "<SBNCreateProgramAccountRequest></SBNCreateProgramAccountRequest>", "FM0000001"),
        (RequestTracker.RequestType.CHANGE_DELIVERY_ADDRESS, "<SBNChangeAddress></SBNChangeAddress>", "FM0000002"),
        (RequestTracker.RequestType.CHANGE_MAILING_ADDRESS, "<SBNChangeAddress></SBNChangeAddress>", "FM0000001"),
        (RequestTracker.RequestType.CHANGE_NAME, "<SBNChangeName></SBNChangeName>", "FM0000003"),
        (RequestTracker.RequestType.CHANGE_PARTY, "<SBNChangeName></SBNChangeName>", "FM0000004"),
        (RequestTracker.RequestType.CHANGE_STATUS, "<SBNChangeStatus></SBNChangeStatus>", "FM0000005"),
    ],
)
def test_resubmit_bn_request(session, client, jwt, request_type, request_xml, identifier):
    """Get all BN request."""
    with nested_session(session):
        legal_entity = factory_legal_entity(identifier, _entity_type=LegalEntity.EntityTypes.SOLE_PROP.value)
        json_data = {"requestType": request_type.name, "request": request_xml}
        with patch.object(request_tracker, "publish_entity_event"):
            rv = client.post(
                f"/api/v2/requestTracker/bn/{identifier}",
                headers=create_header(jwt, [UserRoles.bn_edit], identifier),
                json=json_data,
            )

            assert rv.status_code == HTTPStatus.OK

            request_trackers = RequestTracker.find_by(
                legal_entity, RequestTracker.ServiceName.BN_HUB, request_type=request_type
            )
            assert request_trackers[0].request_object == request_xml
            assert request_trackers[0].is_admin
            assert request_trackers[0].message_id
