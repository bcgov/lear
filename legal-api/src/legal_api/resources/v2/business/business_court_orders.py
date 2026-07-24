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
"""Retrieve the court orders for the entity."""
from http import HTTPStatus

from flask import jsonify
from flask_cors import cross_origin

from business_model.models import Business, CourtOrder, Filing
from legal_api.core import Filing as CoreFiling
from legal_api.services import authorized
from legal_api.utils.auth import jwt

from .bp import bp


@bp.route("/<string:identifier>/court-orders", methods=["GET", "OPTIONS"])
@bp.route("/<string:identifier>/court-orders/<int:court_order_id>", methods=["GET", "OPTIONS"])
@cross_origin()
@jwt.requires_auth
def get_court_orders(identifier, court_order_id=None):
    """Return a JSON of the court orders."""
    business = Business.find_by_identifier(identifier)

    if not business:
        return jsonify({"message": f"{identifier} not found"}), HTTPStatus.NOT_FOUND

    # check authorization
    if not authorized(identifier, jwt, action=["view"]):
        return jsonify({"message":
                        f"You are not authorized to view court orders for {identifier}."}), \
            HTTPStatus.UNAUTHORIZED

    # return the matching court order
    if court_order_id:
        court_order, code = _get_court_order(business, court_order_id)
        return jsonify(court_order), code

    court_orders_list = CourtOrder.get_json_with_filing_type(business.id)
    return jsonify({
        'courtOrders': court_orders_list
    })


def _get_court_order(business, court_order_id=None):
    court_order = None
    if court_order_id:
        court_order = CourtOrder.get_by_id(court_order_id)
        if court_order:
            return _include_court_order_files(court_order, business, jwt), HTTPStatus.OK

    return {"message": f"{business.identifier} court order not found"}, HTTPStatus.NOT_FOUND


def _include_court_order_files(court_order, business, jwt):
    """Return a JSON of the court orders."""
    court_order_json = court_order.json
    filing = Filing.find_by_id(court_order.filing_id)
    if filing.filing_type == 'courtOrder':
        court_order_json['files'] = []  # TODO: implement

    return court_order_json
