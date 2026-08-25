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

from flask import jsonify, request
from flask_cors import cross_origin

from business_model.models import Business, Filing, Jurisdiction
from business_model.utils.legislation_datetime import LegislationDatetime
from legal_api.core import Filing as CoreFiling
from legal_api.services import authorized
from legal_api.utils.auth import jwt

from .bp import bp


@bp.route("/<string:identifier>/extended/<string:filing_type>", methods=["GET", "OPTIONS"])
@bp.route("/<string:identifier>/extended", methods=["GET", "OPTIONS"])
@cross_origin()
@jwt.requires_auth
def get_extended_data(identifier, filing_type=None):
    """Return a JSON of the extended data for a filing type."""
    business = Business.find_by_identifier(identifier)
    if not business:
        return jsonify({"message": f"{identifier} not found"}), HTTPStatus.NOT_FOUND

    # check authorization
    if not authorized(identifier, jwt, action=["view"]):
        return jsonify({"message": f"You are not authorized to view extended data for {identifier}."}), \
            HTTPStatus.UNAUTHORIZED

    for_correction = str(request.args.get("forCorrection", None)).lower() == "true"

    if filing_type:
        return _get_extended_filing_data(business, filing_type, for_correction)
    else:
        return _get_all_extended_data(business, for_correction)


def _get_extended_filing_data(business: Business, filing_type: str, for_correction: bool = False):
    supported_filing_types = [
        CoreFiling.FilingTypes.AMALGAMATIONAPPLICATION,
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
    elif filing_type == CoreFiling.FilingTypes.AMALGAMATIONAPPLICATION:
        return _get_amalgamation_application_data(business, for_correction)


def _get_all_extended_data(business: Business, for_correction):
    continuation_in, continuation_in_status = _get_continuation_in_data(business)
    continuation_out, continuation_out_status = _get_continuation_out_data(business)
    amalgamation_out, amalgamation_out_status = _get_amalgamation_out_data(business)
    amalgamation, amalgamation_status = _get_amalgamation_application_data(business, for_correction)

    return {
        **(continuation_in if continuation_in_status == HTTPStatus.OK else {}),
        **(amalgamation if amalgamation_status == HTTPStatus.OK else {}),
        **(continuation_out if continuation_out_status == HTTPStatus.OK else {}),
        **(amalgamation_out if amalgamation_out_status == HTTPStatus.OK else {}),
    }, HTTPStatus.OK


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
        continuation_in["expro"] = {
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


def _get_amalgamation_application_data(business: Business, for_correction: bool = False):
    amalgamation = business.amalgamation.first()
    if not amalgamation:
        return jsonify({
            "message": f"Could not find amalgamation data for {business.identifier}"
        }), HTTPStatus.NOT_FOUND

    amalgamating_businesses = []
    for ting in amalgamation.amalgamating_businesses:
        ting_info = {
            "id": ting.id,
            "role": ting.role.name
        }
        if ting.business_id:
            ting_business = Business.find_by_internal_id(ting.business_id)
            ting_info.update({
                "identifier": ting_business.identifier
            })
            if for_correction:
                ting_info.update({
                    "legalName": ting_business.legal_name,
                    "legalType": ting_business.legal_type
                })
                mailing_address = ting_business.mailing_address.one_or_none()
                if mailing_address:
                    ting_info["mailingAddress"] = mailing_address.json
        else:
            ting_info.update({
                "identifier": ting.foreign_identifier,
                "foreignJurisdiction": {
                    "country": ting.foreign_jurisdiction,
                    "region": ting.foreign_jurisdiction_region
                },
                "legalName": ting.foreign_name
            })
        amalgamating_businesses.append(ting_info)

    return {
        "amalgamation": {
            "amalgamatingBusinesses": amalgamating_businesses,
            "courtApproval": amalgamation.court_approval
        }
    }, HTTPStatus.OK
