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
"""Tests to assure the Furnishing Documents Service.

Test-Suite to ensure that the Furnishing Documents Service is working as expected.
"""
from http import HTTPStatus
from legal_api.models import Business
from tests.unit.models import factory_business_with_stage_one_furnishing
from unittest.mock import patch, MagicMock
from legal_api.services import MrasService, FurnishingDocumentsService
from legal_api.reports.report_v2 import ReportTypes
import requests

PDF_CONTENT = b'TEST'

mock_response = MagicMock()
mock_response.status_code = HTTPStatus.OK
mock_response.content =  PDF_CONTENT


def test_get_furnishing_document(session, app):
    """Assert that a single furnishing document is returned."""
    business, furnishing = factory_business_with_stage_one_furnishing(
        legal_type=Business.LegalTypes.COMP.value
    )
    with patch.object(requests, 'post', return_value=mock_response):
        with patch.object(MrasService, 'get_jurisdictions', return_value=[]):
            service = FurnishingDocumentsService(ReportTypes.DISSOLUTION, 'default')
            pdf = service.get_furnishing_document(furnishing)
            assert pdf == PDF_CONTENT


def test_get_merged_furnishing_document(session, app):
    """Assert that a merged furnishing document with cover is returned."""
    _, furnishing1 = factory_business_with_stage_one_furnishing(
        identifier='BC1234567',
        legal_type=Business.LegalTypes.COMP.value
    )
    _, furnishing2 = factory_business_with_stage_one_furnishing(
        identifier='BC7654321',
        legal_type=Business.LegalTypes.COMP.value
    )
    furnishings = [furnishing1, furnishing2]
    with patch.object(requests, 'post', return_value=mock_response):
        with patch.object(MrasService, 'get_jurisdictions', return_value=[]):
            with patch.object(FurnishingDocumentsService, '_merge_documents', return_value=PDF_CONTENT) as mock_merge:
                service = FurnishingDocumentsService(ReportTypes.DISSOLUTION, 'default')
                pdf = service.get_merged_furnishing_document(furnishings)
                assert pdf == PDF_CONTENT
                assert mock_merge.assert_called()
