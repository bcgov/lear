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
from http import HTTPStatus

from flask import current_app, g, jsonify, request
from flask_cors import cross_origin

from legal_api.models import Filing, Review, ReviewResult, ReviewStatus, User, UserRoles
from legal_api.services import namex
from legal_api.services.event_publisher import publish_to_queue
from legal_api.utils.auth import jwt

from .bp import bp_admin


@bp_admin.route('/reviews', methods=['GET'])
@cross_origin(origin='*')
@jwt.has_one_of_roles([UserRoles.staff])
def get_reviews():
    """Return a list of reviews."""
    review_filter = Review.ReviewFilter(
        start_date=request.args.get('startDate', None),
        end_date=request.args.get('endDate', None),
        nr_number=request.args.get('nrNumber', None),
        identifier=request.args.get('identifier', None),
        contact_email=request.args.get('contactEmail', None),
        status=request.args.getlist('status', None),
        submitted_sort_by=request.args.get('sortBy', None),
        submitted_sort_order=request.args.get('sortDesc', None),
        page=int(request.args.get('page', 1)),
        limit=int(request.args.get('limit', 10))
    )

    result = Review.get_paginated_reviews(review_filter, get_mapped_column(review_filter.submitted_sort_by))
    reviews = result['reviews']

    nr_numbers = get_applicable_nr_numbers(reviews)
    if nr_numbers:
        nr_expiry_dates = get_expiry_date_for_each_nr(nr_numbers)
        update_reviews(reviews, nr_expiry_dates)

    return jsonify(result), HTTPStatus.OK


def get_applicable_nr_numbers(reviews):
    """Return list of NR numbers of review with status CHANGE_REQUESTED/AWAITING_REVIEW/RESUBMITTED."""
    nr_numbers = []
    for review in reviews:
        current_nr = review['nrNumber']
        current_status = review['status']
        if (current_nr is not None and
            current_status in [ReviewStatus.CHANGE_REQUESTED.name,
                               ReviewStatus.AWAITING_REVIEW.name,
                               ReviewStatus.RESUBMITTED.name]):
            nr_numbers.append(current_nr)
    return nr_numbers


def get_expiry_date_for_each_nr(nr_numbers):
    """Return list of NR numbers and respective Expiry date."""
    nr_response = namex.query_nr_numbers(nr_numbers)
    response_json = nr_response.json()
    nr_expiry_dates = [{'nr': one['nrNum'], 'expiry_date': one['expirationDate']} for one in response_json]
    return nr_expiry_dates


def update_reviews(reviews, nr_expiry_date):
    """Update review by appending NR Expiry date."""
    for review in reviews:
        nr = review['nrNumber']
        if nr is not None:
            match = next((n for n in nr_expiry_date if n['nr'] == nr), None)
            if match:
                review['nrExpiryDate'] = match['expiry_date']


def get_mapped_column(submitted_sort_by):
    """Get mapped column for each param."""
    mapped_column = ''
    if submitted_sort_by:
        if submitted_sort_by == 'nrNumber':
            mapped_column = 'nr_number'
        elif submitted_sort_by == 'contactEmail':
            mapped_column = 'contact_email'
        elif submitted_sort_by == 'submissionDate':
            mapped_column = 'submission_date'
        elif submitted_sort_by == 'status':
            mapped_column = 'status'
        elif submitted_sort_by == 'identifier':
            mapped_column = 'identifier'
    return mapped_column


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
    if status := json_input.get('status'):
        if not ((status := ReviewStatus[status]) and
                (status in [ReviewStatus.CHANGE_REQUESTED,
                            ReviewStatus.APPROVED,
                            ReviewStatus.REJECTED])):
            return jsonify({'message': 'Invalid Status.'}), HTTPStatus.BAD_REQUEST

    else:
        return jsonify({'message': 'Status is required.'}), HTTPStatus.BAD_REQUEST

    comment = json_input.get('comment')
    if (status in [ReviewStatus.CHANGE_REQUESTED, ReviewStatus.REJECTED]
            and not comment):
        return jsonify({'message': 'Comment is required.'}), HTTPStatus.BAD_REQUEST

    filing = Filing.find_by_id(review.filing_id)

    review_result = ReviewResult()
    review_result.reviewer_id = user.id
    review_result.status = status
    review_result.comments = comment
    review.review_results.append(review_result)
    review.status = status
    review.save()

    status_mapping = {
        ReviewStatus.CHANGE_REQUESTED: Filing.Status.CHANGE_REQUESTED.value,
        ReviewStatus.APPROVED: Filing.Status.APPROVED.value,
        ReviewStatus.REJECTED: Filing.Status.REJECTED.value,
    }
    filing.set_review_decision(status_mapping[status])

    # emailer notification
    publish_to_queue(
        data={'email': {'filingId': filing.id, 'type': filing.filing_type, 'option': filing.status}},
        subject=current_app.config.get('NATS_EMAILER_SUBJECT'),
        identifier=None,  # todo: when new review types are added if they have business, add business identifier here
        event_type=None,
        message_id=None,
        is_wrapped=False
    )

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
