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
from datetime import datetime, timedelta
import pytest
from http import HTTPStatus

from flask import current_app
from registry_schemas.example_data import CONTINUATION_IN

from legal_api.models import Filing, RegistrationBootstrap, Review, ReviewStatus
from legal_api.services.authz import BASIC_USER, STAFF_ROLE

from tests.unit.models import factory_filing
from tests.unit.services.utils import create_header


def create_reviews(no_of_reviews=1):
    reviews = []
    for index in range(no_of_reviews):
        review = create_review(f'T1z3a56{index}', f'NR 879895{index}')
        reviews.append(review)
    return reviews


def create_review(identifier, nr, status=ReviewStatus.AWAITING_REVIEW):
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
    filing_dict['filing']['continuationIn']['nameRequest']['nrNumber'] = nr

    filing = factory_filing(None, filing_dict)
    temp_reg = RegistrationBootstrap()
    temp_reg._identifier = identifier
    temp_reg.save()
    filing.temp_reg = identifier
    filing.save()

    review = Review()
    review.filing_id = filing.id
    review.nr_number = filing_dict['filing']['continuationIn']['nameRequest']['nrNumber']
    review.identifier = filing_dict['filing']['continuationIn']['foreignJurisdiction']['identifier']
    review.contact_email = 'no_one@never.get'
    review.status = status
    review.save()

    return review


def create_nr_data(no_of_reviews):
    nrs = create_nrs(no_of_reviews)
    add_dates(nrs)
    return nrs


def create_nrs(no_of_reviews):
    nr_numbers = []
    for index in range(no_of_reviews):
        nr_numbers.append(f'NR 879895{index}')

    nrs_details = [{
        'actions': [],
        'applicants': {
            'emailAddress': '1@1.com',
            'phoneNumber': '1234567890',
        },
        'names': [{
            'name': f'TEST INC. {nr}',
            'state': 'APPROVED'
        }],
        'stateCd': 'APPROVED',
        'requestTypeCd': 'BC',
        'request_action_cd': nr[1],
        'nrNum': nr
    } for nr in nr_numbers]

    return nrs_details


def add_dates(nrs_details):
    current_date = datetime.now()

    for index in range(len(nrs_details)):
        future_date = current_date + timedelta(days=index)
        nrs_details[index]['expirationDate'] = future_date.isoformat()


def test_get_reviews_with_invalid_user(app, session, client, jwt):
    """Assert unauthorized for BASIC_USER role."""
    rv = client.get(f'/api/v2/admin/reviews',
                    headers=create_header(jwt, [BASIC_USER], 'user'))
    assert rv.status_code == HTTPStatus.UNAUTHORIZED


def test_get_reviews_with_valid_user(app, session, client, jwt, mocker):
    """Assert review object returned for STAFF role."""
    no_of_reviews = 11
    create_reviews(no_of_reviews)
    nrs_response = create_nr_data(no_of_reviews)

    mock_response_obj = mocker.Mock()
    mock_response_obj.json.return_value = nrs_response

    mocker.patch('legal_api.services.NameXService.query_nr_numbers', return_value=mock_response_obj)

    rv = client.get(f'/api/v2/admin/reviews',
                    headers=create_header(jwt, [STAFF_ROLE], 'user'))

    assert rv.status_code == HTTPStatus.OK
    assert len(rv.json.get('reviews')) == 10
    assert 1 == rv.json.get('page')
    assert 10 == rv.json.get('limit')
    assert no_of_reviews == rv.json.get('total')


def test_filterd_get_reviews(app, session, client, jwt, mocker):
    """Assert reviews are filtered and sorted by given params."""
    no_of_reviews = 6
    create_reviews(no_of_reviews)
    nrs_response = create_nr_data(no_of_reviews)

    mock_response_obj = mocker.Mock()
    mock_response_obj.json.return_value = nrs_response

    mocker.patch('legal_api.services.NameXService.query_nr_numbers', return_value=mock_response_obj)

    rv = client.get(f'/api/v2/admin/reviews?sortBy=nrNumber&sortDesc=true&page=1&limit=5',
                    headers=create_header(jwt, [STAFF_ROLE], 'user'))

    assert rv.status_code == HTTPStatus.OK
    assert len(rv.json.get('reviews')) == 5
    assert no_of_reviews == rv.json.get('total')
    assert rv.json.get('reviews')[0]['nrNumber'] == 'NR 8798955'
    assert rv.json.get('reviews')[4]['nrNumber'] == 'NR 8798951'


def test_get_specific_review_with_valid_user(app, session, client, jwt, mocker):
    """Assert specific review object returned for STAFF role."""
    review = create_review('T1z3a567', 'NR 8798951')
    filing = Filing.find_by_id(review.filing_id)

    base_url = current_app.config.get('LEGAL_API_BASE_URL')
    mocker.patch('legal_api.resources.v2.admin.reviews.current_app.config.get', return_value=base_url)

    rv = client.get(f'/api/v2/admin/reviews/{review.id}',
                    headers=create_header(jwt, [STAFF_ROLE], 'user'))

    assert rv.status_code == HTTPStatus.OK
    assert rv.json['id'] == review.id
    assert 'filingLink' in rv.json
    assert rv.json['filingLink'] == f'{base_url}/{filing.temp_reg}/filings/{filing.id}'


def test_get_specific_review_with_invalid_user(app, session, client, jwt):
    """Assert unauthorized for BASIC_USER role when getting a specific review."""
    review = create_review('T1z3a567', 'NR 8798951')

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


@pytest.mark.parametrize('status, comment', [
    (ReviewStatus.CHANGE_REQUESTED, 'Upload all documents'),
    (ReviewStatus.APPROVED, None),
    (ReviewStatus.REJECTED, 'Upload all documents'),
])
def test_save_review(app, session, client, jwt, mocker, status, comment):
    """Assert that a review can be saved."""
    review = create_review('T1z3a567', 'NR 8798951')

    data = {
        'status': status.name,
        'comment': comment
    }

    def publish_json(payload, subject):
        pass

    mock_publish = mocker.patch('legal_api.resources.v2.admin.reviews.publish_to_queue')
    mock_publish_json = mocker.patch('legal_api.services.queue', side_effect=publish_json)
    mock_publish.return_value = None
    mock_publish_json.return_value = None

    rv = client.post(f'/api/v2/admin/reviews/{review.id}',
                     json=data,
                     headers=create_header(jwt, [STAFF_ROLE], 'user'))
    assert rv.status_code == HTTPStatus.CREATED
    review = Review.find_by_id(review.id)
    assert review.status == status
    result = review.review_results.all()[0]
    assert result
    assert result.status == status
    assert result.comments == comment

    status_mapping = {
        ReviewStatus.CHANGE_REQUESTED: Filing.Status.CHANGE_REQUESTED.value,
        ReviewStatus.APPROVED: Filing.Status.APPROVED.value,
        ReviewStatus.REJECTED: Filing.Status.REJECTED.value,
    }
    filing = Filing.find_by_id(review.filing_id)
    assert filing.status == status_mapping[status]

    mock_publish.assert_called_with(
        data=mocker.ANY, # for the payload parameter
        subject=current_app.config.get('NATS_EMAILER_SUBJECT'),  # for the subject parameter,
        identifier=None,
        event_type=None,
        message_id=None,
        is_wrapped=False
    )



@pytest.mark.parametrize('data, message, response_code', [
    ({'comment': 'all docs'}, 'Status is required.', HTTPStatus.BAD_REQUEST),
    ({'status': ReviewStatus.CHANGE_REQUESTED.name}, 'Comment is required.', HTTPStatus.BAD_REQUEST),
    ({'status': ReviewStatus.REJECTED.name}, 'Comment is required.', HTTPStatus.BAD_REQUEST),
    ({'status': ReviewStatus.RESUBMITTED.name, 'comment': 'all docs'}, 'Invalid Status.', HTTPStatus.BAD_REQUEST),
])
def test_save_review_validation(app, session, client, jwt, mocker, data, message, response_code):
    """Assert that a save review can be validated."""
    review = create_review('T1z3a567', 'NR 8798951')

    mocker.patch('legal_api.resources.v2.admin.reviews.publish_to_queue', return_value=None)
    rv = client.post(f'/api/v2/admin/reviews/{review.id}',
                     json=data,
                     headers=create_header(jwt, [STAFF_ROLE], 'user'))
    assert rv.status_code == response_code
    assert rv.json['message'] == message


@pytest.mark.parametrize('status', [
    ReviewStatus.APPROVED,
    ReviewStatus.REJECTED,
    ReviewStatus.CHANGE_REQUESTED,
])
def test_save_review_not_allowed(app, session, client, jwt, mocker, status):
    """Assert that a save review can be validated."""
    review = create_review('T1z3a567', 'NR 8798951', status)

    data = {
        'status': status.name,
        'comment': 'Upload all documents'
    }

    mocker.patch('legal_api.resources.v2.admin.reviews.publish_to_queue', return_value=None)
    rv = client.post(f'/api/v2/admin/reviews/{review.id}',
                     json=data,
                     headers=create_header(jwt, [STAFF_ROLE], 'user'))
    assert rv.status_code == HTTPStatus.BAD_REQUEST
    assert rv.json['message'] == 'No changes allowed.'


def test_save_no_review_validation(app, session, client, jwt):
    """Assert that a save review can be validated."""
    rv = client.post(f'/api/v2/admin/reviews/{857}',
                     json={},
                     headers=create_header(jwt, [STAFF_ROLE], 'user'))
    assert rv.status_code == HTTPStatus.NOT_FOUND
    assert rv.json['message'] == 'Review not found.'
