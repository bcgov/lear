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
"""Retrieve the share classes for the entity."""

from http import HTTPStatus

from flask import jsonify
from flask_cors import cross_origin

from legal_api.models import Business, ShareClass
from legal_api.services import authorized
from legal_api.utils.auth import jwt

from .bp import bp


# @cors_preflight('GET,')
@bp.route("/<string:identifier>/share-classes", methods=["GET", "OPTIONS"])
@bp.route("/<string:identifier>/share-classes/<int:share_class_id>", methods=["GET", "OPTIONS"])
@cross_origin(origin="*")
@jwt.requires_auth
def get_share_class(identifier, share_class_id=None):
    """Return a JSON of the share classes."""
    business = Business.find_by_identifier(identifier)

    if not business:
        return jsonify({"message": f"{identifier} not found"}), HTTPStatus.NOT_FOUND

    # check authorization
    if not authorized(identifier, jwt, action=["view"]):
        return jsonify(
            {"message": f"You are not authorized to view share classes for {identifier}."}
        ), HTTPStatus.UNAUTHORIZED

    # return the matching share class
    if share_class_id:
        share_class, msg, code = _get_share_class(business, share_class_id)
        return jsonify(share_class or msg), code

    share_classes = []
    for share_class in business.share_classes.all():
        share_classes.append(share_class.json)

    return jsonify(shareClasses=share_classes)


def _get_share_class(business, share_class_id=None):
    # find by ID
    share_class = None
    if share_class_id:
        rv = ShareClass.find_by_share_class_id(share_class_id)
        if rv:
            share_class = {"shareClass": rv.json}

    if not share_class:
        return None, {"message": f"{business.identifier} share class not found"}, HTTPStatus.NOT_FOUND

    return share_class, None, HTTPStatus.OK
