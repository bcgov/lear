# Copyright © 2022 Province of British Columbia
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""API endpoints for managing Request Tracker resource."""

import uuid
from http import HTTPStatus

from flask import Blueprint, jsonify, request
from flask_cors import cross_origin

from legal_api.models import Business, RequestTracker, UserRoles
from legal_api.resources.v2.admin.administrative_bn import publish_entity_event
from legal_api.utils.auth import jwt


bp = Blueprint("REQUEST_TRACKER", __name__, url_prefix="/api/v2/requestTracker")


@bp.route("bn/<string:identifier>", methods=["GET"])
@cross_origin(origin="*")
@jwt.has_one_of_roles([UserRoles.admin_edit, UserRoles.bn_edit])
def get_bn_request_trackers(identifier: str):
    """Return a list of request trackers."""
    business = Business.find_by_identifier(identifier)
    if business is None:
        return ({"message": "A valid business is required."}, HTTPStatus.BAD_REQUEST)

    request_trackers = RequestTracker.find_by(business.id, RequestTracker.ServiceName.BN_HUB)
    return jsonify(
        {
            "requestTrackers": [
                request_tracker.json
                for request_tracker in request_trackers
                if request_tracker.request_type != RequestTracker.RequestType.GET_BN
            ]
        }
    ), HTTPStatus.OK


@bp.route("bn/<string:identifier>", methods=["POST"])
@cross_origin(origin="*")
@jwt.has_one_of_roles([UserRoles.admin_edit, UserRoles.bn_edit])
def resubmit_bn_request(identifier: str):
    """Resubmit BN request."""
    business = Business.find_by_identifier(identifier)
    if business is None:
        return ({"message": "A valid business is required."}, HTTPStatus.BAD_REQUEST)

    message_id = str(uuid.uuid4())
    json_input = request.get_json()
    request_object = json_input["request"]
    request_type = RequestTracker.RequestType[json_input["requestType"]]

    request_tracker = RequestTracker(
        request_type=request_type,
        retry_number=-1,
        service_name=RequestTracker.ServiceName.BN_HUB,
        business_id=business.id,
        is_admin=True,
        message_id=message_id,
        request_object=request_object,
    )
    request_tracker.save()

    publish_entity_event(business, request_name=f"RESUBMIT_{request_type.name}", message_id=message_id)
    return {"message": "BN request queued."}, HTTPStatus.OK


@bp.route("<int:request_tracker_id>", methods=["GET"])
@cross_origin(origin="*")
@jwt.has_one_of_roles([UserRoles.admin_edit, UserRoles.bn_edit])
def get_request_tracker(request_tracker_id: int):
    """Return request/response objects."""
    request_tracker = RequestTracker.find_by_id(request_tracker_id)
    return jsonify(
        {"request": request_tracker.request_object, "response": request_tracker.response_object, **request_tracker.json}
    ), HTTPStatus.OK
