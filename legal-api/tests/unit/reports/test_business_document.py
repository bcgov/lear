# Copyright © 2021 Province of British Columbia
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

"""Test-Suite to ensure that the Business Report class is working as expected."""
import pytest

from legal_api.reports.business_document import BusinessDocument  # noqa:I001
from legal_api.services.authz import STAFF_ROLE
from tests.unit.services.utils import create_header

from tests.unit.models import factory_business, factory_business_mailing_address


@pytest.mark.parametrize(
    'identifier, entity_type, document_name',
    [
        ('CP1234567', 'CP', 'summary'),
        ('BC1234567', 'BC', 'summary'),
        ('BC7654321', 'BEN', 'summary'),
        ('BC1234567', 'CC', 'summary'),
        ('BC7654321', 'ULC', 'summary'),
        ('BC1234567', 'LLC', 'summary'),
    ]
)
def test_get_pdf(session, app, jwt, identifier, entity_type, document_name):
    """Assert business document can be returned as a PDF."""
    request_ctx = app.test_request_context(
        headers=create_header(jwt, [STAFF_ROLE], identifier)
    )
    with request_ctx:
        business = factory_business(identifier='CP7654321', entity_type='CP')
        factory_business_mailing_address(business)
        report = BusinessDocument(business, document_name)
        filename = report._get_report_filename()
        assert filename
        template = report._get_template()
        assert template
        template_data = report._get_template_data()
        assert template_data
        assert template_data['business']
        assert template_data['formatted_founding_date_time']
        assert template_data['formatted_founding_date']
        assert template_data['registrarInfo']
        assert template_data['entityDescription']
        assert template_data['entityAct']


