# Copyright © 2024 Province of British Columbia
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Tests to assure the reviews end-point.

Test-Suite to ensure that admin/reviews endpoints are working as expected.
"""
import copy
from registry_schemas.example_data import (
    CONTINUATION_IN,
)
from http import HTTPStatus

from flask import current_app

from legal_api.services.authz import BASIC_USER, STAFF_ROLE
from tests.unit.services.utils import create_header

from legal_api.models import Review, ReviewStatus

from tests.unit.models import factory_filing


def create_test_review(no_of_reviews=1):
    filing_dict = {
        'filing': {
            'header': {
                'name': 'continuationIn',
                'date': '2019-04-08',
                'certifiedBy': 'full name',
                'email': 'no_one@never.get',
            }
        }
    }
    filing_dict['filing']['continuationIn'] = copy.deepcopy(CONTINUATION_IN)

    reviews = []
    for _ in range(no_of_reviews):
        filing = factory_filing(None, filing_dict)

        review = Review()
        review.filing_id = filing.id
        review.nr_number = filing_dict['filing']['continuationIn']['nameRequest']['nrNumber']
        review.identifier = filing_dict['filing']['continuationIn']['foreignJurisdiction']['identifier']
        review.completing_party = 'completing party'
        review.status = ReviewStatus.AWAITING_REVIEW
        review.save()
        reviews.append(review)

    return reviews


def test_get_reviews_with_invalid_user(app, session, client, jwt):
    """Assert unauthorized for BASIC_USER role."""
    rv = client.get(f'/api/v2/admin/reviews',
                    headers=create_header(jwt, [BASIC_USER], 'user'))
    assert rv.status_code == HTTPStatus.UNAUTHORIZED


def test_get_reviews_with_valid_user(app, session, client, jwt):
    """Assert review object returned for STAFF role."""
    no_of_reviews = 11
    create_test_review(no_of_reviews)

    rv = client.get(f'/api/v2/admin/reviews',
                    headers=create_header(jwt, [STAFF_ROLE], 'user'))

    assert rv.status_code == HTTPStatus.OK
    assert len(rv.json.get('reviews')) == 10
    assert 1 == rv.json.get('page')
    assert 10 == rv.json.get('limit')
    assert no_of_reviews == rv.json.get('total')


def test_get_specific_review_with_valid_user(app, session, client, jwt, mocker):
    """Assert specific review object returned for STAFF role."""
    review = create_test_review(1)[0]

    base_url = current_app.config.get('LEGAL_API_BASE_URL')

    mock_filing = mocker.Mock()
    mock_filing.temp_reg = 'BC1234567'
    mock_filing.id = 1
    mocker.patch('legal_api.models.Filing.find_by_id', return_value=mock_filing)

    mocker.patch('legal_api.resources.v2.admin.reviews.current_app.config.get', return_value=base_url)

    rv = client.get(f'/api/v2/admin/reviews/{review.id}',
                    headers=create_header(jwt, [STAFF_ROLE], 'user'))

    assert rv.status_code == HTTPStatus.OK
    assert rv.json['id'] == review.id
    assert 'filingLink' in rv.json
    assert rv.json['filingLink'] == f'{base_url}/{mock_filing.temp_reg}/filings/{mock_filing.id}'


def test_get_specific_review_with_invalid_user(app, session, client, jwt):
    """Assert unauthorized for BASIC_USER role when getting a specific review."""
    review = create_test_review(1)[0]

    rv = client.get(f'/api/v2/admin/reviews/{review.id}',
                    headers=create_header(jwt, [BASIC_USER], 'user'))

    assert rv.status_code == HTTPStatus.UNAUTHORIZED


def test_get_nonexistent_review(app, session, client, jwt):
    """Assert not found for non-existent review ID."""
    rv = client.get('/api/v2/admin/reviews/99999',
                    headers=create_header(jwt, [STAFF_ROLE], 'user'))

    assert rv.status_code == HTTPStatus.NOT_FOUND
    assert 'message' in rv.json
    assert rv.json['message'] == 'Review not found.'
