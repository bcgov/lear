# Copyright © 2019 Province of British Columbia
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
"""Calls used by internal services.

TODO: Move in internal filings calls.
"""
from http import HTTPStatus

from flask import current_app, jsonify, request
from flask_cors import cross_origin

from legal_api.models import LegalEntity, UserRoles
from legal_api.services import business_service, COLIN_SVC_ROLE
from legal_api.utils.auth import jwt

from .bp import bp


@bp.route("/internal/tax_ids", methods=["GET"])
@cross_origin(origin="*")
@jwt.has_one_of_roles([UserRoles.system])
def get_internal_tax_ids():
    """Return all identifiers with no tax_id set that are supposed to have a tax_id.

    Excludes COOPS because they do not get a tax id/business number.
    Excludes SP/GP we don't sync firm to colin and we use entity-bn to get tax id/business number.
    """
    if not jwt.validate_roles([COLIN_SVC_ROLE]):
        return jsonify({"message": "You are not authorized to update the colin id"}), HTTPStatus.UNAUTHORIZED

    identifiers = []
    bussinesses_no_taxid = LegalEntity.get_all_by_no_tax_id()
    for business in bussinesses_no_taxid:
        identifiers.append(business.identifier)
    return jsonify({"identifiers": identifiers}), HTTPStatus.OK


@bp.route("/internal/tax_ids", methods=["POST"])
@cross_origin(origin="*")
@jwt.has_one_of_roles([UserRoles.system])
def post_internal_tax_ids():
    """Set tax ids for businesses for given identifiers."""
    if not jwt.validate_roles([COLIN_SVC_ROLE]):
        return jsonify({"message": "You are not authorized to update the colin id"}), HTTPStatus.UNAUTHORIZED

    json_input = request.get_json()
    if not json_input:
        return ({"message": "No identifiers in body of post."}, HTTPStatus.BAD_REQUEST)

    for identifier in json_input.keys():
        # json input is a dict -> identifier: tax id
        business = business_service.fetch_business(identifier)
        if business:
            business.tax_id = json_input[identifier]
            business.save()
        else:
            current_app.logger.error("Unable to update tax_id for business (%s), which is missing in lear", identifier)
    return jsonify({"message": "Successfully updated tax ids."}), HTTPStatus.CREATED
