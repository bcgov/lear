# Copyright © 2020 Province of British Columbia
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
"""Retrieve the aliases for the entity."""

from http import HTTPStatus

from flask import jsonify, request
from flask_restx import Resource, cors

from legal_api.models import Alias, Business
from legal_api.utils.util import cors_preflight

from .api_namespace import API


@cors_preflight("GET,")
@API.route("/<string:identifier>/aliases", methods=["GET", "OPTIONS"])
@API.route("/<string:identifier>/aliases/<int:alias_id>", methods=["GET", "OPTIONS"])
class AliasResource(Resource):
    """Business Aliases service."""

    @staticmethod
    @cors.crossdomain(origin="*")
    def get(identifier, alias_id=None):
        """Return a JSON of the aliases."""
        business = Business.find_by_identifier(identifier)

        if not business:
            return jsonify({"message": f"{identifier} not found"}), HTTPStatus.NOT_FOUND

        # return the matching alias
        if alias_id:
            alias, msg, code = AliasResource._get_alias(business, alias_id)
            return jsonify(alias or msg), code

        aliases_list = []

        alias_type = request.args.get("type")
        if alias_type:
            aliases = Alias.find_by_type(business.id, alias_type.upper())
        else:
            aliases = business.aliases.all()

        for alias in aliases:
            alias_json = alias.json
            aliases_list.append(alias_json)

        return jsonify(aliases=aliases_list)

    @staticmethod
    def _get_alias(business, alias_id=None):
        # find by ID
        alias = None
        if alias_id:
            rv = Alias.find_by_id(alias_id=alias_id)
            if rv:
                alias = {"alias": rv.json}

        if not alias:
            return None, {"message": f"{business.identifier} alias not found"}, HTTPStatus.NOT_FOUND

        return alias, None, HTTPStatus.OK
