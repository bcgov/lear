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

"""Tests to assure the business-furnishings end-point

Test-Suite to ensure that the /businesses/_id_/furnishings endpoint is working as expected.
"""
import pytest
from http import HTTPStatus
from unittest.mock import patch

from legal_api.models import UserRoles
from legal_api.reports.report_v2 import ReportV2
from tests.unit.models import factory_business_with_stage_one_furnishing
from tests.unit.services.utils import create_header



def test_get_furnishing_document(session, client, jwt):
    """Assert that the endpoint is worked as expected."""

    business, furnishing = factory_business_with_stage_one_furnishing()
    with patch.object(ReportV2, 'get_pdf', return_value=('', HTTPStatus.OK)):
        rv = client.get(f'/api/v2/businesses/{business.identifier}/furnishings/{furnishing.id}/document',
                        headers=create_header(jwt, [UserRoles.system, ], business.identifier, **{'accept': 'application/pdf'}))
        
        assert rv
        assert rv.status_code == HTTPStatus.OK


def test_get_furnishing_document_invalid_role(session, client, jwt):
    """Assert the call fails for invalid user role."""
    business, furnishing = factory_business_with_stage_one_furnishing()
    rv = client.get(f'/api/v2/businesses/{business.identifier}/furnishings/{furnishing.id}/document',
                    headers=create_header(jwt, [UserRoles.basic, ], business.identifier, **{'accept': 'application/pdf'}))
    
    assert rv
    assert rv.status_code == HTTPStatus.UNAUTHORIZED
    code = rv.json.get('code')
    assert code == 'missing_a_valid_role'


def test_get_furnishing_document_missing_business(session, client, jwt):
    business, furnishing = factory_business_with_stage_one_furnishing()
    invalid_identifier = 'ABC'
    rv = client.get(f'/api/v2/businesses/{invalid_identifier}/furnishings/{furnishing.id}/document',
                    headers=create_header(jwt, [UserRoles.system, ], business.identifier, **{'accept': 'application/pdf'}))
    
    assert rv
    assert rv.status_code == HTTPStatus.NOT_FOUND
    message = rv.json.get('message')
    assert message
    assert invalid_identifier in message


def test_get_furnishing_document_missing_furnishing(session, client, jwt):
    business, furnishing = factory_business_with_stage_one_furnishing()
    invalid_furnishing_id = '123456789'
    rv = client.get(f'/api/v2/businesses/{business.identifier}/furnishings/{invalid_furnishing_id}/document',
                    headers=create_header(jwt, [UserRoles.system, ], business.identifier, **{'accept': 'application/pdf'}))
    
    assert rv
    assert rv.status_code == HTTPStatus.NOT_FOUND
    message = rv.json.get('message')
    assert message
    assert business.identifier in message
    assert invalid_furnishing_id in message

@pytest.mark.parametrize(
    'test_name, output_type, valid', [
        ('TEST_EMAIL', 'email', True),
        ('TEST_MAIL', 'mail', True),
        ('TEST_VALID_CASE_INSENSITIVE', 'eMAIL', True),
        ('TEST_INVALID', 'paper', False)
    ]
)
def test_get_furnishing_document_output_type(session, client, jwt, test_name, output_type, valid):
    business, furnishing = factory_business_with_stage_one_furnishing()
    with patch.object(ReportV2, 'get_pdf', return_value=('', HTTPStatus.OK)):
        rv = client.get(f'/api/v2/businesses/{business.identifier}/furnishings/{furnishing.id}/document?output_type={output_type}',
                        headers=create_header(jwt, [UserRoles.system, ], business.identifier, **{'accept': 'application/pdf'}))
        
        assert rv
        if valid:
            assert rv.status_code == HTTPStatus.OK
        else:
            assert rv.status_code == HTTPStatus.BAD_REQUEST
            message = rv.json.get('message')
            assert message
            assert output_type in message
