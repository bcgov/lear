# Copyright © 2024 Province of British Columbia
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
"""API endpoints for retrieving review data."""
from datetime import datetime, timezone
from http import HTTPStatus

from flask import current_app, g, jsonify, request
from flask_cors import cross_origin
from html_sanitizer import Sanitizer

from legal_api.models import Filing, Review, ReviewResult, ReviewStatus, User, UserRoles
from legal_api.services import queue
from legal_api.utils.auth import jwt

from .bp import bp_admin


@bp_admin.route('/reviews', methods=['GET'])
@cross_origin(origin='*')
@jwt.has_one_of_roles([UserRoles.staff])
def get_reviews():
    """Return a list of reviews."""
    page = int(request.args.get('page', 1))
    limit = int(request.args.get('limit', 10))
    reviews = Review.get_paginated_reviews(page, limit)

    return jsonify(reviews), HTTPStatus.OK


@bp_admin.route('/reviews/<int:review_id>', methods=['POST'])
@cross_origin(origin='*')
@jwt.has_one_of_roles([UserRoles.staff])
def save_review(review_id: int):
    """Save review.

    Current review status -> Allowable review status
    AWAITING_REVIEW/RESUBMITTED -> CHANGE_REQUESTED/APPROVED/REJECTED
    CHANGE_REQUESTED/APPROVED/REJECTED -> No changes allowed
    """
    user = User.get_or_create_user_by_jwt(g.jwt_oidc_token_info)
    if review := Review.find_by_id(review_id):
        if review.status not in [ReviewStatus.AWAITING_REVIEW, ReviewStatus.RESUBMITTED]:
            return jsonify({'message': 'No changes allowed.'}), HTTPStatus.BAD_REQUEST
    else:
        return jsonify({'message': 'Review not found.'}), HTTPStatus.NOT_FOUND

    json_input = request.get_json()
    status = json_input.get('status')
    comment = json_input.get('comment')
    if not status or not comment:
        return jsonify({'message': 'Status and Comment are required.'}), HTTPStatus.BAD_REQUEST

    if not ((status := ReviewStatus[status]) and
            (status in [ReviewStatus.CHANGE_REQUESTED,
                        ReviewStatus.APPROVED,
                        ReviewStatus.REJECTED])):
        return jsonify({'message': 'Invalid Status.'}), HTTPStatus.BAD_REQUEST

    filing = Filing.find_by_id(review.filing_id)

    review_result = ReviewResult()
    review_result.reviewer_id = user.id
    review_result.status = status
    review_result.comments = Sanitizer().sanitize(comment)
    review.review_results.append(review_result)
    review.status = status
    review.save()

    status_mapping = {
        ReviewStatus.CHANGE_REQUESTED: Filing.Status.CHANGE_REQUESTED.value,
        ReviewStatus.APPROVED: Filing.Status.APPROVED.value,
        ReviewStatus.REJECTED: Filing.Status.REJECTED.value,
    }
    filing.set_review_status(status_mapping[status])

    # emailer notification
    queue.publish_json(
        {"email": {"filingId": filing.id, "type": filing.filing_type, "option": filing.status}},
        current_app.config.get('NATS_EMAILER_SUBJECT')
    )

    if (filing.status == Filing.Status.APPROVED.value and
            filing.effective_date <= datetime.now(timezone.utc)):
        # filer notification
        queue.publish_json(
            {'filing': {'id': filing.id}},
            current_app.config.get('NATS_FILER_SUBJECT'))

    return jsonify({'message': 'Review saved.'}), HTTPStatus.CREATED


@bp_admin.route('/reviews/<int:review_id>', methods=['GET'])
@cross_origin(origin='*')
@jwt.has_one_of_roles([UserRoles.staff])
def get_review(review_id: int):
    """Return specific review."""
    review = Review.find_by_id(review_id)

    if not review:
        return jsonify({'message': 'Review not found.'}), HTTPStatus.NOT_FOUND
    result = review.json

    base_url = current_app.config.get('LEGAL_API_BASE_URL')
    filing = Filing.find_by_id(review.filing_id)
    filing_link = f'{base_url}/{filing.temp_reg}/filings/{filing.id}'
    result['filingLink'] = filing_link

    return jsonify(result), HTTPStatus.OK
