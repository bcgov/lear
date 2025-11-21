# Copyright © 2024 Province of British Columbia
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
"""Retrieve the specified letter for the furnishing entry."""
from http import HTTPStatus
from typing import Final

from flask import current_app, jsonify, request
from flask_cors import cross_origin

from legal_api.exceptions import ErrorCode, get_error_message
from legal_api.models import Business, Furnishing, UserRoles
from legal_api.reports.report_v2 import ReportTypes
from legal_api.services import FurnishingDocumentsService, authorized
from legal_api.utils.auth import jwt

from ..bp import bp

FURNISHING_DOC_BASE_ROUTE: Final = "/<string:identifier>/furnishings/<string:furnishing_id>/document"


@bp.route(FURNISHING_DOC_BASE_ROUTE, methods=["GET", "OPTIONS"])
@cross_origin(origins="*")
@jwt.has_one_of_roles([UserRoles.system, UserRoles.staff])
def get_furnishing_document(identifier: str, furnishing_id: int):
    """Return a JSON object with meta information about the Service."""
    # basic checks
    if not authorized(identifier, jwt, ["view", ]):
        return jsonify(
            message=get_error_message(ErrorCode.NOT_AUTHORIZED, identifier=identifier)
        ), HTTPStatus.UNAUTHORIZED

    if not (business := Business.find_by_identifier(identifier)):
        return jsonify(
            message=get_error_message(ErrorCode.MISSING_BUSINESS,
                                      identifier=identifier)
        ), HTTPStatus.NOT_FOUND
    if not (furnishing := Furnishing.find_by_id(furnishing_id)) or\
        furnishing.business_id != business.id or\
            furnishing.furnishing_type == Furnishing.FurnishingType.GAZETTE:
        return jsonify(
            message=get_error_message(ErrorCode.FURNISHING_NOT_FOUND,
                                      furnishing_id=furnishing_id, identifier=identifier)
        ), HTTPStatus.NOT_FOUND

    variant = request.args.get("variant", "default").lower()
    if variant not in ["default", "greyscale"]:
        return jsonify({"message": f"{variant} not a valid variant"}), HTTPStatus.BAD_REQUEST

    if "application/pdf" in request.accept_mimetypes:
        try:
            pdf = FurnishingDocumentsService(ReportTypes.DISSOLUTION, variant).get_furnishing_document(furnishing)
            if not pdf:
                return jsonify({"message": "Unable to get furnishing document."}), HTTPStatus.INTERNAL_SERVER_ERROR
            return current_app.response_class(
                response=pdf,
                status=HTTPStatus.OK,
                mimetype="application/pdf"
            )
        except Exception:
            return jsonify({"message": "Unable to get furnishing document."}), HTTPStatus.INTERNAL_SERVER_ERROR

    return {}, HTTPStatus.NOT_FOUND
