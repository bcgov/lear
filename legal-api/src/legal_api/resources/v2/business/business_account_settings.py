# Copyright (c) 2025, Province of British Columbia
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# 
# 1. Redistributions of source code must retain the above copyright notice, this
#    list of conditions and the following disclaimer.
# 
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
# 
# 3. Neither the name of the copyright holder nor the names of its
#    contributors may be used to endorse or promote products derived from
#    this software without specific prior written permission.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""Provides retrieval and edit endpoints for business account settings."""
from __future__ import annotations

from http import HTTPStatus

from flask import jsonify, request
from flask_cors import cross_origin

from legal_api.models import Business, BusinessAccountSettings
from legal_api.services.authz import authorized, get_account_products
from legal_api.utils.auth import jwt

from .bp import bp


@bp.route("/settings/<string:account_id>", methods=["GET"])
@bp.route("/settings/<string:account_id>/<string:identifier>", methods=["GET"])
@cross_origin(origin="*")
@jwt.requires_auth
def get_business_account_settings(account_id: str, identifier: str | None = None):
    """Return a JSON object containing the settings information for the business and account combination."""
    if identifier:
        if not authorized(identifier, jwt, action=["view"]):
            return jsonify({"message": f"You are not authorized to view business {identifier} settings."}), HTTPStatus.UNAUTHORIZED

        business = Business.find_by_identifier(identifier)
        if not business:
            return jsonify({"message": f"{identifier} not found"}), HTTPStatus.NOT_FOUND

        business_id = business.id

        default_settings = BusinessAccountSettings.find_by_business_account(business_id, None)
        account_settings = BusinessAccountSettings.find_by_business_account(business_id, int(account_id))

        settings = account_settings if account_settings else default_settings
        if not settings:
            return jsonify({"message": "Business account settings not found"}), HTTPStatus.NOT_FOUND

        return jsonify(settings.json)

    # check the jwt has access to the requested account id
    if not get_account_products(jwt.get_token_auth_header(), account_id):
        return jsonify({"message": "Not authorized to view business settings for this account."}), HTTPStatus.UNAUTHORIZED

    # return settings across all businesses for account id
    return jsonify([settings.json for settings in BusinessAccountSettings.find_all(None, account_id)])


@bp.route("/settings/<string:account_id>/<string:identifier>", methods=["POST", "PUT", "PATCH"])
@cross_origin(origin="*")
@jwt.requires_auth
def update_business_account_settings(account_id: str, identifier: str):
    """Update the settings information for the business and account combination."""
    # FUTURE: Verify they are allowed to update the account - #30992
    if not authorized(identifier, jwt, action=["edit"]):
        return jsonify({"message": f"You are not authorized to edit business {identifier} settings."}), HTTPStatus.UNAUTHORIZED

    business = Business.find_by_identifier(identifier)
    if not business:
        return jsonify({"message": f"{identifier} not found"}), HTTPStatus.NOT_FOUND

    business_id = business.id
    settings = BusinessAccountSettings.create_or_update(business_id, account_id, request.get_json())
    return jsonify(settings.json), HTTPStatus.CREATED


@bp.route("/settings/<string:account_id>/<string:identifier>", methods=["DELETE"])
@cross_origin(origin="*")
@jwt.requires_auth
def delete_business_account_settings(account_id: str, identifier: str):
    """Update the settings information for the business and account combination."""
    # FUTURE: Verify they are allowed to update the account - #30992
    if not authorized(identifier, jwt, action=["edit"]):
        return jsonify({"message": f"You are not authorized to remove business {identifier} settings."}), HTTPStatus.UNAUTHORIZED

    business = Business.find_by_identifier(identifier)
    if not business:
        return jsonify({"message": f"{identifier} not found"}), HTTPStatus.NOT_FOUND

    business_id = business.id
    BusinessAccountSettings.delete(business_id, account_id)
    return jsonify({"message": f"{identifier} settings for account {account_id} have been deleted."}), HTTPStatus.OK
