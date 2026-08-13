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
"""Retrieve the extended data for the entity."""
from http import HTTPStatus

from flask import current_app, jsonify
from flask_cors import cross_origin

from business_model.models import Business, Filing, Jurisdiction
from business_model.utils.legislation_datetime import LegislationDatetime
from legal_api.core import Filing as CoreFiling
from legal_api.services import authorized
from legal_api.utils.auth import jwt

from .bp import bp


@bp.route("/<string:identifier>/extended/<string:filing_type>", methods=["GET", "OPTIONS"])
@cross_origin()
@jwt.requires_auth
def get_extended_data(identifier, filing_type):
    """Return a JSON of the extended data for a filing type."""
    business = Business.find_by_identifier(identifier)
    if not business:
        return jsonify({"message": f"{identifier} not found"}), HTTPStatus.NOT_FOUND

    # check authorization
    if not authorized(identifier, jwt, action=["view"]):
        return jsonify({"message":
                        f"You are not authorized to view extended data for {filing_type} for {identifier}."}), \
            HTTPStatus.UNAUTHORIZED

    supported_filing_types = [
        CoreFiling.FilingTypes.AMALGAMATIONOUT,
        CoreFiling.FilingTypes.CONTINUATIONIN,
        CoreFiling.FilingTypes.CONTINUATIONOUT,
    ]
    if filing_type not in supported_filing_types:
        return jsonify({"message": f"{filing_type} not supported"}), HTTPStatus.BAD_REQUEST

    if filing_type == CoreFiling.FilingTypes.CONTINUATIONIN:
        return _get_continuation_in_data(business)
    elif filing_type == CoreFiling.FilingTypes.CONTINUATIONOUT:
        return _get_continuation_out_data(business)
    elif filing_type == CoreFiling.FilingTypes.AMALGAMATIONOUT:
        return _get_amalgamation_out_data(business)


def _get_continuation_in_data(business: Business):
    jurisdiction = Jurisdiction.get_continuation_in_jurisdiction(business.id)
    if not jurisdiction:
        return jsonify({
            "message": f"Could not find continuationIn data for {business.identifier}"
        }), HTTPStatus.NOT_FOUND

    incorporation_date = None
    if jurisdiction.incorporation_date:
        incorporation_date = LegislationDatetime.as_legislation_timezone(jurisdiction.incorporation_date)
        incorporation_date = incorporation_date.date().isoformat()
    continuation_in = {
        "country": jurisdiction.country,
        "region": jurisdiction.region,
        "identifier": jurisdiction.identifier,
        "legalName": jurisdiction.legal_name,
        "incorporationDate": incorporation_date
    }
    if jurisdiction.expro_identifier or jurisdiction.expro_legal_name:
        continuation_in["xpro"] = {
            "identifier": jurisdiction.expro_identifier,
            "legalName": jurisdiction.expro_legal_name
        }
    return {
        "continuationIn": continuation_in
    }, HTTPStatus.OK


def _get_continuation_out_data(business: Business):
    if not (
        business.state == Business.State.HISTORICAL and
        (
            (filing := Filing.find_by_id(business.state_filing_id)) and
            filing.filing_type == CoreFiling.FilingTypes.CONTINUATIONOUT
        )
    ):
        return jsonify({
            "message": f"Could not find continuationOut data for {business.identifier}"
        }), HTTPStatus.NOT_FOUND

    return {
        "continuationOut": {
            "date": LegislationDatetime.format_as_legislation_date(business.continuation_out_date),
            "country": business.jurisdiction,
            "region": business.foreign_jurisdiction_region,
            "legalName": business.foreign_legal_name
        }
    }, HTTPStatus.OK


def _get_amalgamation_out_data(business: Business):
    if not (
        business.state == Business.State.HISTORICAL and
        (
            (filing := Filing.find_by_id(business.state_filing_id)) and
            filing.filing_type == CoreFiling.FilingTypes.AMALGAMATIONOUT
        )
    ):
        return jsonify({
            "message": f"Could not find amalgamationOut data for {business.identifier}"
        }), HTTPStatus.NOT_FOUND

    return {
        "amalgamationOut": {
            "date": LegislationDatetime.format_as_legislation_date(business.amalgamation_out_date),
            "country": business.jurisdiction,
            "region": business.foreign_jurisdiction_region,
            "legalName": business.foreign_legal_name
        }
    }, HTTPStatus.OK
