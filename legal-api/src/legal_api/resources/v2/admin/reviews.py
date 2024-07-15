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

from flask import current_app, jsonify, request
from flask_cors import cross_origin

from legal_api.models import Filing, Review, UserRoles, db
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

    return reviews, HTTPStatus.OK


@bp_admin.route('/reviews/<int:review_id>', methods=['GET', 'OPTIONS'])
@cross_origin(origin='*')
@jwt.has_one_of_roles([UserRoles.staff])
def get_review(review_id: int):
    """Return specific review."""
    review = Review.find_by_id(review_id)

    if not review:
        return jsonify({'message': 'Review not found.'}), HTTPStatus.NOT_FOUND
    result = review.json

    filing = Filing.find_by_id(review.filing_id)
    base_url = current_app.config.get('LEGAL_API_BASE_URL')
    filing_link = f'{base_url}/{filing.temp_reg}/filings/{filing.id}'

    result['filingLink'] = filing_link

    return jsonify(result), HTTPStatus.OK
