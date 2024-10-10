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

"""Tests to assure the Review Model.

Test-Suite to ensure that the Review Model is working as expected.
"""
import copy
from registry_schemas.example_data import (
    CONTINUATION_IN,
)

from legal_api.models import Review, ReviewStatus

from tests.unit.models import factory_filing


def test_review_save(session):
    """Assert that the review was saved."""
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
    review.contact_details = 'contact@email.com'
    review.status = ReviewStatus.AWAITING_REVIEW
    review.save()

    assert review.id

    review = Review.find_by_id(review.id)
    assert review

    review = Review.get_review(review.filing_id)
    assert review
