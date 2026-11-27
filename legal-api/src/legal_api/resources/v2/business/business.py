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
"""Searching on a business entity.

Provides all the search and retrieval from the business entity datastore.
"""
from contextlib import suppress
from http import HTTPStatus

from flask import current_app, g, jsonify, request
from flask_babel import _ as babel
from flask_cors import cross_origin

from business_account import AccountService
from business_model.models import Business, Filing, RegistrationBootstrap, db
from legal_api.core import Filing as CoreFiling
from legal_api.resources.v2.business.business_filings import saving_filings
from legal_api.services import (
    ACCOUNT_IDENTITY,
    STAFF_ROLE,
    SYSTEM_ROLE,
    RegistrationBootstrapService,
    check_warnings,
    colin,
    flags,
)
from legal_api.services.authz import (
    COLIN_SVC_ROLE,
    CONTACT_CENTRE_STAFF_ROLE,
    MAXIMUS_STAFF_ROLE,
    SBC_FINANCE_STAFF_ROLE,
    SBC_STAFF_ROLE,
    auth_v2_denied,
    authorized,
    get_allowable_actions,
    get_allowed,
    get_could_files,
    has_any_roles,
    is_account_member,
    is_new_feature_enabled,
    log_unauthorized_request,
)
from legal_api.services.permissions import ListActionsPermissionsAllowed, PermissionService
from legal_api.services.search_service import AffiliationSearchDetails, BusinessSearchService
from legal_api.utils.auth import jwt
from legal_api.utils.util import is_temp_reg_identifier

from .bp import bp


@bp.route("/<string:identifier>", methods=["GET"])
@cross_origin()
@jwt.requires_auth
def get_businesses(identifier: str):
    """Return a JSON object with meta information about the Service."""
    if str(request.args.get("slim", None)).lower() == "true":
        # getting all business info is expensive so returning the slim version is desirable for some flows
        # - (i.e. business/person search updates)
        return get_businesses_public(identifier, True)

    if is_temp_reg_identifier(identifier):
        return {"message": babel("No information on temp registrations.")}, 200

    business = Business.find_by_identifier(identifier)

    if not business:
        return jsonify({"message": f"{identifier} not found"}), HTTPStatus.NOT_FOUND

    # check authorization if required
    if auth_v2_denied("authV2Business", "business", identifier, jwt, ["view"]):
        return jsonify({"message":
                        f"You are not authorized to view business {identifier}."}), \
            HTTPStatus.UNAUTHORIZED

    is_staff = has_any_roles(jwt, [
        STAFF_ROLE,
        SYSTEM_ROLE,
        COLIN_SVC_ROLE,
        SBC_STAFF_ROLE,
        SBC_FINANCE_STAFF_ROLE,
        CONTACT_CENTRE_STAFF_ROLE,
        MAXIMUS_STAFF_ROLE,
    ])
    warnings = check_warnings(business, is_staff)
    # TODO remove complianceWarnings line when UI has been integrated to use warnings instead of complianceWarnings
    business.compliance_warnings = warnings
    business.warnings = warnings

    allowable_actions = get_allowable_actions(jwt, business)
    business.allowable_actions = allowable_actions

    business_json = business.json()

    recent_filing_json = CoreFiling.get_most_recent_filing_json(business.id, None, jwt)
    if recent_filing_json:
        business_json["submitter"] = recent_filing_json["filing"]["header"]["submitter"]

    allowed_filings = str(request.args.get("allowed_filings", None)).lower() == "true"
    if allowed_filings:
        business_json["allowedFilings"] = get_allowed(business.state, business.legal_type, jwt)

    q_account = request.args.get("account")
    current_app.logger.info("account info request, for account: %s", q_account)
    if q_account and has_any_roles(jwt, [SYSTEM_ROLE, ACCOUNT_IDENTITY]):
        account_response = AccountService.get_account_by_affiliated_identifier(identifier, flags)
        current_app.logger.info("VALID account request, for accountId: %s, by: %s, jwt: %s, for org account: %s",
                                q_account,
                                g.jwt_oidc_token_info.get("preferred_username"),
                                g.jwt_oidc_token_info,
                                account_response)
        # A business can be affiliated in multiple accounts (in user account as well as in gov staff account's)
        # AccountService.get_account_by_affiliated_identifier will fetch all of it
        # check one of it has `q_account`
        if (
            (orgs := account_response.get("orgs")) and
            any(str(org.get("id")) == q_account for org in orgs)
        ):
            business_json["accountId"] = q_account

    return jsonify(business=business_json)


@bp.route("/<string:identifier>/public", methods=["GET"])
@cross_origin()
@jwt.requires_auth
def get_businesses_public(identifier: str, slim = False):
    """Return a JSON object with public meta information about the business."""
    if is_temp_reg_identifier(identifier):
        return {"message": babel("No information on temp registrations.")}, 200

    business = Business.find_by_identifier(identifier)

    if not business:
        return jsonify({"message": f"{identifier} not found"}), HTTPStatus.NOT_FOUND

    business_json = business.json(slim=True)
    # add extras here that are not a part of the initial slim JSON
    business_json["alternateNames"] = business.get_alternate_names()

    if slim or str(request.args.get("slim", None)).lower() == "true":
        return jsonify(business=business_json)

    # NOTE: warnings can take longer to process which is why its not returned in the slim business call
    business_json["warnings"] = check_warnings(business)

    return jsonify(business=business_json)


@bp.route("/<string:identifier>/colin-snapshot", methods=["GET"])
@cross_origin()
@jwt.requires_auth
def get_businesses_colin_snapshot(identifier: str):
    """Return the snapshot data of a COLIN business not yet managed in LEAR."""
    if not authorized(identifier, jwt, action=["view"]):
        return jsonify({"message":
                        f"You are not authorized to view business {identifier}."}), \
            HTTPStatus.UNAUTHORIZED

    if Business.find_by_identifier(identifier):
        # a business in LEAR is managed here - its COLIN data may be stale
        return jsonify({"message": f"{identifier} is managed in the Business Registry."}), HTTPStatus.NOT_FOUND

    snapshot_json, status_code = colin.get_snapshot(identifier)
    if status_code == HTTPStatus.NOT_FOUND:
        return jsonify({"message": f"{identifier} not found"}), HTTPStatus.NOT_FOUND
    if snapshot_json is None or status_code != HTTPStatus.OK:
        return jsonify({"message": f"Unable to retrieve {identifier} data from COLIN."}), \
            HTTPStatus.INTERNAL_SERVER_ERROR

    return jsonify(snapshot_json), HTTPStatus.OK


@bp.route("", methods=["POST"])
@cross_origin()
@jwt.requires_auth
def post_businesses():
    """Create a valid filing, else error out."""
    json_input = request.get_json()
    try:
        filing_account_id = json_input["filing"]["header"]["accountId"]
        filing_type = json_input["filing"]["header"]["name"]
        if filing_type not in CoreFiling.NEW_BUSINESS_FILING_TYPES:
            raise TypeError
    except (TypeError, KeyError):
        return {"error": babel("Requires a valid filing.")}, HTTPStatus.BAD_REQUEST

    filing_title = filing_type
    with suppress(KeyError):
        if filing_sub_type := Filing.get_filings_sub_type(filing_type, json_input):
            filing_title = Filing.FILINGS[filing_type][filing_sub_type]["title"]
        else:
            filing_title = Filing.FILINGS[filing_type]["title"]

    is_create_gate_on = is_new_feature_enabled("authV2BusinessCreate")
    if is_create_gate_on and not is_account_member(jwt, filing_account_id):
        log_unauthorized_request("business create", filing_account_id)
        return {"message": babel("You are not authorized to create a business for this account.")}, \
            HTTPStatus.FORBIDDEN

    bootstrap = RegistrationBootstrapService.create_bootstrap(filing_account_id)
    if not isinstance(bootstrap, RegistrationBootstrap):
        return {"error": babel(f"Unable to create {filing_title} Filing.")}, \
            HTTPStatus.SERVICE_UNAVAILABLE

    try:
        business_name = json_input["filing"][filing_type]["nameRequest"]["nrNumber"]
        nr_number = json_input["filing"][filing_type]["nameRequest"]["nrNumber"]
    except KeyError:
        business_name = bootstrap.identifier
        nr_number = None

    legal_type = json_input["filing"][filing_type]["nameRequest"]["legalType"]
    corp_type_code = Filing.FILINGS[filing_type]["temporaryCorpTypeCode"]
    rv = RegistrationBootstrapService.register_bootstrap(bootstrap=bootstrap,
                                                         business_name=business_name,
                                                         nr_number=nr_number,
                                                         corp_type_code=corp_type_code,
                                                         corp_sub_type_code=legal_type,
                                                         )
    if not isinstance(rv, HTTPStatus):
        with suppress(Exception):
            bootstrap.delete()
        return {"error": babel(f"Unable to create {filing_title} Filing.")}, \
            HTTPStatus.SERVICE_UNAVAILABLE

    # The temporary identifier was created in this request, so the caller cannot know it yet.
    # Write it into the body here (Flask returns this same cached object to every later get_json()),
    # so the identifier check, validation and save all see the one the API just created.
    business_block = json_input["filing"].get("business")
    json_input["filing"]["business"] = {
        **(business_block if isinstance(business_block, dict) else {}),
        "identifier": bootstrap.identifier
    }

    try:
        response = saving_filings(identifier=bootstrap.identifier)  # pylint: disable=no-value-for-parameter
    except Exception:
        db.session.rollback()
        _rollback_unused_bootstrap(bootstrap)
        raise
    _rollback_unused_bootstrap(bootstrap)
    return response


def _rollback_unused_bootstrap(bootstrap: RegistrationBootstrap):
    """Remove the temp identifier and its account affiliation when no filing was saved against it.

    Covers only_validate, rejected filings and errors before the save. A filing saved before a later
    failure (eg: payment) keeps its temp identifier so the draft can still be opened or deleted.
    """
    try:
        if Filing.query.filter(Filing.temp_reg == bootstrap.identifier).first():
            return
        if RegistrationBootstrapService.deregister_bootstrap(bootstrap) != HTTPStatus.OK:
            current_app.logger.error(f"Unable to deregister unused temp reg: {bootstrap.identifier}")
        RegistrationBootstrapService.delete_bootstrap(bootstrap)
    except Exception:  # pylint: disable=broad-exception-caught
        current_app.logger.exception(f"Unable to roll back unused temp reg {bootstrap.identifier}")


@bp.route("/<string:identifier>/ar-reminder", methods=["GET"])
@cross_origin()
@jwt.requires_auth
def get_ar_reminder(identifier):
    """Return send ar reminder flag."""
    if identifier.startswith("T"):
        return {"message": "No information on temp registrations."}, 200

    business = Business.find_by_identifier(identifier)
    if not business:
        return {"message": f"{identifier} not found"}, HTTPStatus.NOT_FOUND

    if auth_v2_denied("authV2ArReminder", "ar-reminder", identifier, jwt, ["view"]):
        return jsonify({"message":
                        f"You are not authorized to view the ar reminder for {identifier}."}), \
            HTTPStatus.FORBIDDEN

    return {"arReminder": business.send_ar_ind}, HTTPStatus.OK


@bp.route("/<string:identifier>/ar-reminder", methods=["PUT"])
@cross_origin()
@jwt.requires_auth
def set_ar_reminder(identifier):
    """Update send ar reminder flag."""
    if identifier.startswith("T"):
        return {"message": "Cannot update ar reminder for temp registrations."}, HTTPStatus.BAD_REQUEST

    if auth_v2_denied("authV2ArReminder", "ar-reminder", identifier, jwt, ["edit"]):
        return jsonify({"message":
                        f"You are not authorized to update the ar reminder for {identifier}."}), \
            HTTPStatus.FORBIDDEN

    if (
        flags.is_on("enable-permissions-for-action") and
        PermissionService.check_user_permission(ListActionsPermissionsAllowed.AR_REMINDER_OPT_OUT.value)
    ):
        return (
            jsonify({
                "message": (
                    f"Permission Denied - You do not have permissions to change opt out ar reminder: {identifier}."
                )
            }),
            HTTPStatus.FORBIDDEN
        )

    json_input = request.get_json()
    ar_reminder = json_input.get("arReminder")
    if not isinstance(ar_reminder, bool):
        return {"message": "arReminder must be a boolean value"}, HTTPStatus.BAD_REQUEST

    business = Business.find_by_identifier(identifier)
    if not business:
        return {"message": f"{identifier} not found"}, HTTPStatus.NOT_FOUND

    business.send_ar_ind = ar_reminder
    business.save()
    return {"message": "arReminder flag updated"}, HTTPStatus.OK


@bp.route("/search", methods=["POST"])
@cross_origin()
@jwt.requires_roles([SYSTEM_ROLE])
def search_businesses():
    """Return the list of businesses and draft businesses."""
    try:
        json_input = request.get_json()
        identifiers = json_input.get("identifiers", None)
        temp_identifiers = []
        business_identifiers = []
        if not identifiers or not isinstance(identifiers, list):
            return {"message": "Expected a list of 1 or more for '/identifiers'"}, HTTPStatus.BAD_REQUEST

        for identifier in identifiers:
            if identifier.startswith("T"):
                temp_identifiers.append(identifier)
            else:
                business_identifiers.append(identifier)
        search_filters = AffiliationSearchDetails.from_request_args(json_input)

        bus_results, bus_hasmore = BusinessSearchService.get_search_filtered_businesses_results(
            business_json=json_input,
            identifiers=business_identifiers,
            search_filters=search_filters) or ([], False)
        draft_results, draft_hasmore = BusinessSearchService.get_search_filtered_filings_results(
            identifiers=temp_identifiers,
            search_filters=search_filters) or ([], False)
        has_more = bus_hasmore or draft_hasmore
        return jsonify({
            "businessEntities": bus_results,
            "draftEntities": draft_results,
            "hasMore": has_more
            }), HTTPStatus.OK
    except Exception as err:
        current_app.logger.info(err)
        current_app.logger.error("Error searching over business information for: %s", identifiers)
        return {"error": "Unable to retrieve businesses."}, HTTPStatus.INTERNAL_SERVER_ERROR


@bp.route("/search/affiliation_mappings", methods=["POST"])
@cross_origin()
@jwt.requires_roles([SYSTEM_ROLE])
def get_filing_details():
    """Return the list of Business filings with name requests. Being called from auth api."""
    data = request.get_json()
    identifiers = data.get("identifiers", [])
    if not identifiers or not isinstance(identifiers, list):
        return {"message": "Expected a list of 1 or more for '/identifiers'"}, HTTPStatus.BAD_REQUEST
    results = BusinessSearchService.get_affiliation_mapping_results(identifiers)
    return jsonify({
        "count": len(results),
        "entityDetails": results
    })


@bp.route("/allowable/<string:business_type>/<string:business_state>", methods=["GET"])
@cross_origin()
@jwt.requires_auth
def get_allowable_for_business_type(business_type: str, business_state: str):
    """Return a JSON object with information about what a user could theoretically file for a business type."""
    business_state = business_state.upper()
    business_type = business_type.upper()

    bs_state = getattr(Business.State, business_state, False)
    if not bs_state:
        return {"message": babel("Invalid business state.")}, HTTPStatus.BAD_REQUEST

    try:
        _ = Business.LegalTypes(business_type)
    except ValueError:
        return {"message": babel("Invalid business type.")}, HTTPStatus.BAD_REQUEST

    could_file = get_could_files(jwt, business_type, business_state)

    return jsonify(couldFile=could_file)
