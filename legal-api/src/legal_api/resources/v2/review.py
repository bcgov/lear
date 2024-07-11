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

from flask import Blueprint, jsonify
from flask_cors import cross_origin

from legal_api.models import Filing, Review, ReviewResult
from legal_api.utils.auth import jwt


bp = Blueprint('Review', __name__, url_prefix='/api/v2/review')


@bp.route('/<int:review_id>', methods=['GET', 'OPTIONS'])
@cross_origin(origin='*')
@jwt.requires_auth
def get_review(review_id: int):
    """Return specific review."""
    review = Review.find_by_id(review_id)
    review_results = ReviewResult.get_review_results(review_id)

    if not review:
        return jsonify({'message': 'Review not found.'}), HTTPStatus.NOT_FOUND
    result = review.json
    result['results'] = review_results

    # Update the submission date if the status is RESUBMITTED
    if review.status == 'RESUBMITTED' and review.results:
        review.submission_date = review.results[0].submission_date

    # Get filing_json data in endpoint for UI to use
    filing = Filing.find_by_id(review.filing_id)
    filing_json = filing.json if filing else {}
    result['filing'] = filing_json

    return jsonify(result), HTTPStatus.OK
