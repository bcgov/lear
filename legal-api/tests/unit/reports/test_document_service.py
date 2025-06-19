# Copyright © 2025 Province of British Columbia
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

"""Test-Suite to ensure that the Report class is working as expected."""
import copy
from datetime import datetime
from http import HTTPStatus
import datedelta
import pytest

from legal_api.reports.document_service import DocumentService
from tests.unit.models import factory_business, factory_completed_filing
from registry_schemas.example_data import FILING_TEMPLATE

def test_create_document(session):
    founding_date = datetime.utcnow()
    business = factory_business('CP1234567', founding_date=founding_date)
    filing = copy.deepcopy(FILING_TEMPLATE)
    filing['filing']['header']['name'] = 'Involuntary Dissolution'
    completed_filing = \
        factory_completed_filing(business, filing, filing_date=founding_date + datedelta.datedelta(months=1))
    document_service = DocumentService()
    assert document_service.has_document(business.identifier, completed_filing.id, 'annualReport') == False
    response, status = document_service.create_document(business.identifier, completed_filing.id, 'annualReport', 3113, completed_filing.filing_type)
    assert status == HTTPStatus.CREATED
    assert response['identifier'] == 1
    assert response['url'] == 'https://document-service.com/document/1'
    assert document_service.has_document(business.identifier, completed_filing.id, 'annualReport') != False