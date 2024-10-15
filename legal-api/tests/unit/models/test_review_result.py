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

"""Tests to assure the Review Result Model.

Test-Suite to ensure that the Review Result Model is working as expected.
"""
import copy
from datetime import datetime, timezone
from registry_schemas.example_data import (
    CONTINUATION_IN,
)

from legal_api.models import Review, ReviewResult, ReviewStatus, User

from tests.unit.models import factory_filing


def test_review_result_save(session):
    """Assert that the review result was saved."""
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
    review.contact_email = 'no_one@never.get'
    review.status = ReviewStatus.AWAITING_REVIEW
    review.save()

    assert review.id

    user = User(username='username',
                firstname='firstname',
                middlename='middlename',
                lastname='lastname',
                sub='sub',
                iss='iss',
                idp_userid='123',
                login_source='IDIR')
    user.save()

    change_requested = ReviewResult()
    change_requested.review_id = review.id
    change_requested.comments = 'do the change'
    change_requested.status = ReviewStatus.CHANGE_REQUESTED
    change_requested.reviewer_id = user.id
    change_requested.submission_date = review.submission_date
    review.review_results.append(change_requested)
    review.save()
    assert change_requested.id

    review.status = ReviewStatus.APPROVED
    review.submission_date = datetime.now(timezone.utc)

    approved = ReviewResult()
    approved.review_id = review.id
    approved.comments = 'approved'
    approved.status = ReviewStatus.APPROVED
    approved.reviewer_id = user.id
    approved.submission_date = review.submission_date
    review.review_results.append(approved)
    review.save()

    review_results = ReviewResult.get_review_results(review.id)
    assert len(review_results) == 2

    last_review_result = ReviewResult.get_last_review_result(review.filing_id)
    assert last_review_result.id == approved.id
