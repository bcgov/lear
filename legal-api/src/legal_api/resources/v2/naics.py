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
"""API endpoints for searching NAICS resources."""

import re
from http import HTTPStatus

from flask import Blueprint, jsonify, request
from flask_cors import cross_origin

from legal_api.models import NaicsStructure
from legal_api.utils.auth import jwt


bp = Blueprint("NAICS2", __name__, url_prefix="/api/v2/naics")


@bp.route("", methods=["GET", "OPTIONS"])
@cross_origin(origin="*")
@jwt.requires_auth
def get_naics_results():
    """Return naics results matching search term."""
    results = []
    results_list = []
    search_term = request.args.get("search_term", None)

    if not search_term:
        return jsonify({"message": "search_term query parameter is required."}), HTTPStatus.BAD_REQUEST

    if len(search_term) < 3:
        return jsonify({"message": "search_term cannot be less than 3 characters."}), HTTPStatus.BAD_REQUEST

    if is_naics_code_format(search_term):
        result = NaicsStructure.find_by_code(search_term)
        if result:
            results.append(result)
    else:
        results = NaicsStructure.find_by_search_term(search_term)

    for result in results:
        results_list.append(result.json)

    return jsonify(results=results_list), HTTPStatus.OK


@bp.route("/<string:naics_code_or_key>", methods=["GET", "OPTIONS"])
@cross_origin(origin="*")
@jwt.requires_auth
def get_naics_code(naics_code_or_key: str):
    """Return naics code."""
    if is_naics_code_format(naics_code_or_key):
        naics_structure = NaicsStructure.find_by_code(naics_code_or_key)
    elif is_naics_key_format(naics_code_or_key):
        naics_structure = NaicsStructure.find_by_naics_key(naics_code_or_key)
    else:
        return jsonify(
            {"message": "Invalid NAICS code(6 digits) or naics key(uuid v4) format."}
        ), HTTPStatus.BAD_REQUEST

    if not naics_structure:
        return jsonify({"message": "NAICS code not found."}), HTTPStatus.NOT_FOUND

    result = naics_structure.json
    return jsonify(result), HTTPStatus.OK


def is_naics_code_format(value: str) -> bool:
    """Determine whether input value is a valid NAICS code format."""
    pattern = "\\d{6}"
    result = bool(re.fullmatch(pattern, value))
    return result


def is_naics_key_format(value: str) -> bool:
    """Determine whether input value is a valid uuidv4 format."""
    pattern = "[0-9A-F]{8}-[0-9A-F]{4}-4[0-9A-F]{3}-[89AB][0-9A-F]{3}-[0-9A-F]{12}"
    result = bool(re.fullmatch(pattern, value, flags=re.IGNORECASE))
    return result
