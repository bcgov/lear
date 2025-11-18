# Copyright © 2019 Province of British Columbia
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
"""Searching on a business entity.

Provides all the search and retrieval from the business entity datastore.
"""

import datetime
from http import HTTPStatus
from typing import Tuple

from flask import g, jsonify, request
from flask_cors import cross_origin

from legal_api.exceptions import BusinessException
from legal_api.models import Business, Comment, Filing, User, db
from legal_api.services import authorized
from legal_api.services.comments import validate
from legal_api.utils.auth import jwt

from .bp import bp
# noqa: I003; the multiple route decorators cause an erroneous error in line space counting


@bp.route("/<string:identifier>/filings/<int:filing_id>/comments/<int:comment_id>", methods=["PUT", "PATCH", "DELETE"])
@cross_origin(origin="*")
@jwt.requires_auth
def not_allowed_filing_comments(identifier, filing_id, comment_id=None):  # pylint: disable=W0613; matching signature
    """Block the redirect of the versioned API calls."""
    return {}, HTTPStatus.METHOD_NOT_ALLOWED


@bp.route("/<string:identifier>/filings/<int:filing_id>/comments", methods=["GET"])
@bp.route("/<string:identifier>/filings/<int:filing_id>/comments/<int:comment_id>", methods=["GET"])
@cross_origin(origin="*")
@jwt.requires_auth
def get_filing_comments(identifier, filing_id, comment_id=None):
    """Return a JSON object with meta information about the Service."""
    # basic checks
    err_msg, err_code = _basic_checks(identifier, filing_id, request)
    if err_msg:
        return jsonify(err_msg), err_code

    comments = db.session.query(Comment).filter(Comment.filing_id == filing_id)

    if comment_id:
        comment = comments.filter(Comment.id == comment_id).one_or_none()
        if not comment:
            return jsonify({"message": f"Comment {comment_id} not found"}), HTTPStatus.NOT_FOUND

        return jsonify(comment.json)

    rv = []
    for comment in comments:
        rv.append(comment.json)

    return jsonify(comments=rv)


@bp.route("/<string:identifier>/filings/<int:filing_id>/comments", methods=["POST"])
@bp.route("/<string:identifier>/filings/<int:filing_id>/comments/<int:comment_id>", methods=["POST"])
@cross_origin(origin="*")
@jwt.requires_auth
def post_filing_comments(identifier, filing_id):
    """Create a new comment for the filing."""
    # basic checks
    err_msg, err_code = _basic_checks(identifier, filing_id, request)
    if err_msg:
        return jsonify(err_msg), err_code

    json_input = request.get_json()

    # check authorization
    if not authorized(identifier, jwt, action=["add_comment"]):
        return jsonify(
            {"message": f"You are not authorized to submit a comment for {identifier}."}
        ), HTTPStatus.UNAUTHORIZED

    # validate comment
    err = validate(json_input, True)
    if err:
        json_input["errors"] = err.msg
        return jsonify(json_input), err.code

    # confirm that the filing ID in the URL is the same as in the json
    if json_input["comment"]["filingId"] != filing_id:
        json_input["errors"] = [
            {"error": "Invalid filingId in request"},
        ]
        return jsonify(json_input), HTTPStatus.BAD_REQUEST

    # save comment
    user = User.get_or_create_user_by_jwt(g.jwt_oidc_token_info)
    try:
        comment = Comment()
        comment.comment = json_input["comment"]["comment"]
        comment.staff_id = user.id
        comment.filing_id = filing_id
        comment.timestamp = datetime.datetime.utcnow()

        comment.save()
    except BusinessException as err:
        reply = json_input
        reply["errors"] = [
            {"error": err.error},
        ]
        return jsonify(reply), err.status_code or (
            HTTPStatus.CREATED if (request.method == "POST") else HTTPStatus.ACCEPTED
        )

    # all done
    return jsonify(comment.json), HTTPStatus.CREATED


def _basic_checks(identifier, filing_id, client_request) -> Tuple[dict, int]:
    """Perform basic checks to ensure put can do something."""
    json_input = client_request.get_json()
    if client_request.method == "POST" and not json_input:
        return ({"message": f"No filing json data in body of post for {identifier}."}, HTTPStatus.BAD_REQUEST)

    if client_request.method == "GET" and identifier.startswith("T"):
        filing_model = Filing.get_temp_reg_filing(identifier)
        business = Business.find_by_internal_id(filing_model.business_id)
    else:
        business = Business.find_by_identifier(identifier)

    filing = Filing.find_by_id(filing_id)

    if not business:
        return ({"message": f"{identifier} not found"}, HTTPStatus.NOT_FOUND)

    # check that filing belongs to this business
    if not filing or filing.business_id != business.id:
        return ({"message": f"Filing {filing_id} not found"}, HTTPStatus.NOT_FOUND)

    return (None, None)
