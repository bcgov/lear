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
"""Test-Suite to ensure that the ReportV2(Gotenberg Report) class is working as expected."""
import pytest

from unittest.mock import patch
from legal_api.services import MrasService
from legal_api.reports.report_v2 import ReportV2, ReportTypes
from tests.unit.models import factory_business_with_stage_one_furnishing


@pytest.mark.parametrize(
    'test_name, output_type', [
        ('COMMENCEMENT_EMAIL', 'email'),
        ('COMMENCEMENT_MAIL', 'mail'),
    ]
)
def test_get_pdf(session, test_name, output_type):
    """Assert that furnishing can be returned as a Gotenberg PDF."""
    business, furnishing = factory_business_with_stage_one_furnishing()
    with patch.object(MrasService, 'get_jurisdictions', return_value=[]):
        report = ReportV2(business, furnishing, ReportTypes.DISSOLUTION, output_type)
        filename = report._get_report_filename()
        assert filename
        template = report._get_template()
        assert template
        template_data = report._get_template_data()
        assert template_data
        assert template_data['furnishing']
        assert template_data['outputType'] == output_type
        assert template_data['registrarInfo']
        assert template_data['title'] == 'NOTICE OF COMMENCEMENT OF DISSOLUTION'
        report_files = report._get_report_files(template_data)
        assert report_files
        assert 'header.html' in report_files
        assert 'index.html' in report_files
        assert 'footer.html' in report_files
