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

from flask import jsonify, request
from flask_babel import _ as babel
from flask_restx import Resource, cors

from legal_api.models import Business, Filing, RegistrationBootstrap
from legal_api.resources.v1.business.business_filings import ListFilingResource
from legal_api.services import RegistrationBootstrapService, authorized
from legal_api.utils.auth import jwt
from legal_api.utils.util import cors_preflight

from .api_namespace import API


@cors_preflight("GET, POST")
@API.route("/<string:identifier>", methods=["GET", "OPTIONS"])
@API.route("", methods=["POST", "OPTIONS"])
class BusinessResource(Resource):
    """Meta information about the overall service."""

    @staticmethod
    @cors.crossdomain(origin="*")
    @jwt.requires_auth
    def get(identifier: str):
        """Return a JSON object with meta information about the Service."""
        if identifier.startswith("T"):
            return {"message": babel("No information on temp registrations.")}, 200

        business = Business.find_by_identifier(identifier)

        if not business:
            return jsonify({"message": f"{identifier} not found"}), HTTPStatus.NOT_FOUND

        # check authorization
        if not authorized(identifier, jwt, action=["view"]):
            return jsonify({"message":
                            f"You are not authorized to view business {identifier}."}), \
                HTTPStatus.UNAUTHORIZED

        return jsonify(business=business.json())

    @staticmethod
    @cors.crossdomain(origin="*")
    @jwt.requires_auth
    def post():
        """Create a valid filing, else error out."""
        json_input = request.get_json()
        valid_filing_types = [
            Filing.FILINGS["incorporationApplication"]["name"],
            Filing.FILINGS["registration"]["name"]
        ]

        try:
            filing_account_id = json_input["filing"]["header"]["accountId"]
            filing_type = json_input["filing"]["header"]["name"]
            if filing_type not in valid_filing_types:
                raise TypeError
        except (TypeError, KeyError):
            return {"error": babel("Requires a valid filing.")}, HTTPStatus.BAD_REQUEST

        # @TODO rollback bootstrap if there is A failure, awaiting changes in the affiliation service
        bootstrap = RegistrationBootstrapService.create_bootstrap(filing_account_id)
        if not isinstance(bootstrap, RegistrationBootstrap):
            return {"error": babel("Unable to create {0} Filing.".format(Filing.FILINGS[filing_type]["title"]))}, \
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
                                                             corp_sub_type_code=legal_type)
        if not isinstance(rv, HTTPStatus):
            with suppress(Exception):
                bootstrap.delete()
            return {"error": babel("Unable to create {0} Filing.".format(Filing.FILINGS[filing_type]["title"]))}, \
                HTTPStatus.SERVICE_UNAVAILABLE

        return ListFilingResource.put(bootstrap.identifier, None)
