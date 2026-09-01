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

from flask import current_app, jsonify, url_for
from flask_cors import cross_origin

from business_model.models import Business, CourtOrder, Filing
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
        "courtOrders": court_orders_list
    }), HTTPStatus.OK


def _get_court_order(business, court_order_id=None):
    if court_order := CourtOrder.get_by_id(court_order_id):
        court_order_json = court_order.json
        filing = Filing.find_by_id(court_order.filing_id)
        if filing.filing_type == "courtOrder":
            _include_court_order_files(court_order_json, filing, business)

        return {"courtOrder": court_order_json}, HTTPStatus.OK

    return {"message": f"{business.identifier} court order not found"}, HTTPStatus.NOT_FOUND


def _include_court_order_files(court_order_json, filing, business):
    if documents := filing.documents.all():
        base_url = current_app.config.get("BUSINESS_API_GW_URL")
        doc_url = url_for(
            "API2.get_documents",
            identifier=business.identifier,
            filing_id=filing.id,
            legal_filing_name=None
        )
        files = []
        for doc in documents:
            file_name = doc.file_name
            if not file_name:
                file_name = f"Court Order {court_order_json.get('fileNumber')}"
            files.append({
                "fileName": file_name,
                "fileKey": doc.file_key,
                "url": f"{base_url}{doc_url}/static/{doc.file_key}",
                "documentType": doc.type
            })
        court_order_json["files"] = files
