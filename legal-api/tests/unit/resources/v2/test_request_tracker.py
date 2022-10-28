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
import pytest
from http import HTTPStatus
from unittest.mock import patch

from legal_api.models import Business, RequestTracker, UserRoles
from legal_api.resources.v2 import request_tracker

from tests.unit.models import factory_business
from tests.unit.services.utils import create_header


def test_get_bn_request_trackers(session, client, jwt):
    """Get all BN request."""
    identifier = 'FM0000001'
    business = factory_business(identifier, entity_type=Business.LegalTypes.SOLE_PROP.value)

    request_tracker = RequestTracker(
        request_type=RequestTracker.RequestType.INFORM_CRA,
        retry_number=-1,
        service_name=RequestTracker.ServiceName.BN_HUB,
        business_id=business.id,
        request_object='<SBNCreateProgramAccountRequest></SBNCreateProgramAccountRequest>'
    )
    request_tracker.save()

    rv = client.get(f'/api/v2/requestTracker/bn/{identifier}',
                    headers=create_header(jwt, [UserRoles.bn_edit], identifier))

    assert rv.status_code == HTTPStatus.OK
    assert rv.json['requestTrackers'][0]['id'] == request_tracker.id
    assert rv.json['requestTrackers'][0]['requestType'] == request_tracker.request_type.name
    assert rv.json['requestTrackers'][0]['isProcessed'] == request_tracker.is_processed
    assert rv.json['requestTrackers'][0]['serviceName'] == request_tracker.service_name.name
    assert rv.json['requestTrackers'][0]['isAdmin'] == request_tracker.is_admin


def test_get_request_tracker(session, client, jwt):
    """Get request tracker."""
    identifier = 'FM0000001'
    business = factory_business(identifier, entity_type=Business.LegalTypes.SOLE_PROP.value)

    request_tracker = RequestTracker(
        request_type=RequestTracker.RequestType.INFORM_CRA,
        retry_number=-1,
        service_name=RequestTracker.ServiceName.BN_HUB,
        business_id=business.id,
        request_object='<SBNCreateProgramAccountRequest></SBNCreateProgramAccountRequest>',
        response_object='<SBNAcknowledgement></SBNAcknowledgement>'
    )
    request_tracker.save()

    rv = client.get(f'/api/v2/requestTracker/{request_tracker.id}',
                    headers=create_header(jwt, [UserRoles.bn_edit], identifier))

    assert rv.status_code == HTTPStatus.OK
    assert rv.json['id'] == request_tracker.id
    assert rv.json['requestType'] == request_tracker.request_type.name
    assert rv.json['isProcessed'] == request_tracker.is_processed
    assert rv.json['serviceName'] == request_tracker.service_name.name
    assert rv.json['isAdmin'] == request_tracker.is_admin
    assert rv.json['request'] == request_tracker.request_object
    assert rv.json['response'] == request_tracker.response_object


@pytest.mark.parametrize('request_type, request_xml', [
    (RequestTracker.RequestType.INFORM_CRA, '<SBNCreateProgramAccountRequest></SBNCreateProgramAccountRequest>'),
    (RequestTracker.RequestType.CHANGE_DELIVERY_ADDRESS, '<SBNChangeAddress></SBNChangeAddress>'),
    (RequestTracker.RequestType.CHANGE_MAILING_ADDRESS, '<SBNChangeAddress></SBNChangeAddress>'),
    (RequestTracker.RequestType.CHANGE_NAME, '<SBNChangeName></SBNChangeName>'),
    (RequestTracker.RequestType.CHANGE_PARTY, '<SBNChangeName></SBNChangeName>'),
    (RequestTracker.RequestType.CHANGE_STATUS, '<SBNChangeStatus></SBNChangeStatus>'),
])
def test_resubmit_bn_request(session, client, jwt, request_type, request_xml):
    """Get all BN request."""
    identifier = 'FM0000001'
    business = factory_business(identifier, entity_type=Business.LegalTypes.SOLE_PROP.value)
    json_data = {
        'requestType': request_type.name,
        'request': request_xml
    }
    with patch.object(request_tracker, 'publish_entity_event'):
        rv = client.post(f'/api/v2/requestTracker/bn/{identifier}',
                         headers=create_header(jwt, [UserRoles.bn_edit], identifier),
                         json=json_data)

        assert rv.status_code == HTTPStatus.OK

        request_trackers = RequestTracker.find_by(business.id,
                                                  RequestTracker.ServiceName.BN_HUB,
                                                  request_type=request_type)
        assert request_trackers[0].request_object == request_xml
        assert request_trackers[0].is_admin
        assert request_trackers[0].message_id
