# Copyright © 2026 Province of British Columbia
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
"""
    Filing part validation.
    Helper to expose complex validations to the UI.
    Enables UI to send lightweight validation checks without having to construct the whole filing payload.
"""
from http import HTTPStatus
from flask import jsonify, request
from flask_babel import _
from flask_cors import cross_origin

from business_model.models import (
    Business,
)
from legal_api.resources.v2.business.bp import bp
from legal_api.services.filings.validations.sections import validate_section
from legal_api.services import authorized
from legal_api.utils.auth import jwt


@bp.route("/<string:identifier>/filings/validate-section", methods=["POST"])
@cross_origin()
@jwt.requires_auth
def validate_filing_section(identifier: str):
    """Validate an individual filing section without requiring a complete filing payload."""
    business = Business.find_by_identifier(identifier)
    if not business:
        return (
            jsonify({"message": _("Business %(identifier)s not found", identifier=identifier)}),
            HTTPStatus.NOT_FOUND,
        )

    if not authorized(identifier, jwt, action=["edit"]):
        return (
            jsonify({
                "message": _(
                    "Not Authorized - You are not authorized to validate filings for %(identifier)s.",
                    identifier=identifier,
                )
            }),
            HTTPStatus.FORBIDDEN,
        )

    json_input = request.get_json(silent=True) or {}

    filing_type = json_input.get("filingType")
    filing_sub_type = json_input.get("filingSubType")
    section = json_input.get("section")
    data = json_input.get("data") or {}

    if not filing_type or not section:
        return (
            jsonify({"message": _("Both 'filingType' and 'section' are required.")}),
            HTTPStatus.BAD_REQUEST,
        )

    errors, is_supported = validate_section(
        business=business,
        filing_type=filing_type,
        section=section,
        data=data,
        filing_sub_type=filing_sub_type,
    )

    if not is_supported:
        detail = f"'{section}' on '{filing_type}'"
        if filing_sub_type:
            detail += f" ({filing_sub_type})"
        return (
            jsonify({"message": _("Validation for %(detail)s is not supported.", detail=detail)}),
            HTTPStatus.BAD_REQUEST,
        )

    return (
        jsonify({
            "isValid": len(errors) == 0,
            "errors": errors,
        }),
        HTTPStatus.OK,
    )