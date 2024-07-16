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

from legal_api.services.authz import BASIC_USER, STAFF_ROLE
from tests.unit.services.utils import create_header

from legal_api.models import Review, ReviewStatus

from tests.unit.models import factory_filing


def basic_test_review():
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
    filing = factory_filing(None, filing_dict)

    review = Review()
    review.filing_id = filing.id
    review.nr_number = filing_dict['filing']['continuationIn']['nameRequest']['nrNumber']
    review.identifier = filing_dict['filing']['continuationIn']['foreignJurisdiction']['identifier']
    review.completing_party = 'completing party'
    review.status = ReviewStatus.AWAITING_REVIEW

    return review


def test_get_reviews_with_invalid_user(app, session, client, jwt):
    """Assert unauthorized for BASIC_USER role."""

    rv = client.get(f'/api/v2/admin/reviews',
                    headers=create_header(jwt, [BASIC_USER], 'user'))

    assert rv.status_code == HTTPStatus.UNAUTHORIZED

def test_get_reviews_with_valid_user(app, session, client, jwt):
    """Assert review object returned for STAFF role."""

    review_one = basic_test_review()
    review_one.save()

    review_two = basic_test_review()
    review_two.save()

    review_three = basic_test_review()
    review_three.save()

    rv = client.get(f'/api/v2/admin/reviews',
                    headers=create_header(jwt, [STAFF_ROLE], 'user'))

    assert rv.status_code == HTTPStatus.OK
    assert 'reviews' in rv.json
    assert 1 == rv.json.get('page')
    assert 10 == rv.json.get('limit')
    assert 3 == rv.json.get('total')

