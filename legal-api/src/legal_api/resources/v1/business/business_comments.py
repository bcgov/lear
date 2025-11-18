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
from flask_restx import Resource, cors

from legal_api.exceptions import BusinessException
from legal_api.models import Business, Comment, User, db
from legal_api.services import authorized
from legal_api.services.comments import validate
from legal_api.utils.auth import jwt
from legal_api.utils.util import cors_preflight

from .api_namespace import API

# noqa: I003; the multiple route decorators cause an erroneous error in line space counting


@cors_preflight("GET, POST")
@API.route("/<string:identifier>/comments", methods=["GET", "POST", "OPTIONS"])
@API.route("/<string:identifier>/comments/<int:comment_id>", methods=["GET", "OPTIONS"])
class BusinessCommentResource(Resource):
    """Business Comment service."""

    @staticmethod
    @cors.crossdomain(origin="*")
    @jwt.requires_auth
    def get(identifier, comment_id=None):
        """Return a JSON object with meta information about the Service."""
        # basic checks
        business = Business.find_by_identifier(identifier)
        err_msg, err_code = BusinessCommentResource._basic_checks(identifier, business, request)
        if err_msg:
            return jsonify(err_msg), err_code

        comments = db.session.query(Comment).filter(Comment.business_id == business.id, Comment.filing_id.is_(None))

        if comment_id:
            comment = comments.filter(Comment.id == comment_id).one_or_none()
            if not comment:
                return jsonify({"message": f"Comment {comment_id} not found"}), HTTPStatus.NOT_FOUND

            return jsonify(comment.json)

        rv = []
        for comment in comments:
            rv.append(comment.json)

        return jsonify(comments=rv)

    @staticmethod
    @cors.crossdomain(origin="*")
    @jwt.requires_auth
    def post(identifier):
        """Create a new comment for the business."""
        # basic checks
        business = Business.find_by_identifier(identifier)
        err_msg, err_code = BusinessCommentResource._basic_checks(identifier, business, request)
        if err_msg:
            return jsonify(err_msg), err_code

        json_input = request.get_json()

        # check authorization
        if not authorized(identifier, jwt, action=["add_comment"]):
            return jsonify({"message":
                            f"You are not authorized to submit a comment for {identifier}."}), \
                HTTPStatus.UNAUTHORIZED

        # validate comment
        err = validate(json_input, False)
        if err:
            json_input["errors"] = err.msg
            return jsonify(json_input), err.code

        # save comment
        user = User.get_or_create_user_by_jwt(g.jwt_oidc_token_info)
        try:
            comment = Comment()
            comment.comment = json_input["comment"]["comment"]
            comment.staff_id = user.id
            comment.business_id = business.id
            comment.timestamp = datetime.datetime.utcnow()
            comment.save()
        except BusinessException as err:
            reply = json_input
            reply["errors"] = [{"error": err.error}, ]
            return jsonify(reply), err.status_code

        # all done
        return jsonify(comment.json), HTTPStatus.CREATED

    @staticmethod
    def _basic_checks(identifier: str, business: Business, client_request) -> Tuple[dict, int]:
        """Perform basic checks to ensure put can do something."""
        json_input = client_request.get_json()
        if client_request.method == "POST" and not json_input:
            return ({"message": f"No comment json data in body of post for {identifier}."},
                    HTTPStatus.BAD_REQUEST)

        if not business:
            return ({"message": f"{identifier} not found"}, HTTPStatus.NOT_FOUND)

        return (None, None)
