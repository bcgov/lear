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
from flask_restx import Resource, cors

from legal_api.models import Business
from legal_api.services import COLIN_SVC_ROLE
from legal_api.utils.auth import jwt
from legal_api.utils.util import cors_preflight

from .api_namespace import API


@cors_preflight("GET, POST")
@API.route("/internal/tax_ids", methods=["GET", "POST", "OPTIONS"])
class InternalBusinessResource(Resource):
    """Internal information about businesses."""

    @staticmethod
    @cors.crossdomain(origin="*")
    @jwt.requires_auth
    def get():
        """Return all identifiers with no tax_id set that are supposed to have a tax_id.

        Excludes COOPS because they do not get a tax id/business number.
        Excludes SP/GP we don't sync firm to colin and we use entity-bn to get tax id/business number.
        """
        if not jwt.validate_roles([COLIN_SVC_ROLE]):
            return jsonify({"message": "You are not authorized to update the colin id"}), HTTPStatus.UNAUTHORIZED

        identifiers = []
        bussinesses_no_taxid = Business.get_all_by_no_tax_id()
        for business in bussinesses_no_taxid:
            identifiers.append(business.identifier)
        return jsonify({"identifiers": identifiers}), HTTPStatus.OK

    @staticmethod
    @cors.crossdomain(origin="*")
    @jwt.requires_auth
    def post():
        """Set tax ids for businesses for given identifiers."""
        if not jwt.validate_roles([COLIN_SVC_ROLE]):
            return jsonify({"message": "You are not authorized to update the colin id"}), HTTPStatus.UNAUTHORIZED

        json_input = request.get_json()
        if not json_input:
            return ({"message": "No identifiers in body of post."}, HTTPStatus.BAD_REQUEST)

        for identifier in json_input:
            # json input is a dict -> identifier: tax id
            business = Business.find_by_identifier(identifier)
            if business:
                business.tax_id = json_input[identifier]
                business.save()
            else:
                current_app.logger.error("Unable to update tax_id for business (%s), which is missing in lear",
                                         identifier)
        return jsonify({"message": "Successfully updated tax ids."}), HTTPStatus.CREATED
