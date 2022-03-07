# Copyright © 2020 Province of British Columbia
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
"""The Unit Tests for the Name Request filing component."""

import copy
from datetime import datetime
from unittest.mock import patch

import pytest
from legal_api.models import Filing
from registry_schemas.example_data import INCORPORATION_FILING_TEMPLATE

from entity_filer.filing_meta import FilingMeta
from entity_filer.filing_processors import incorporation_filing
from entity_filer.filing_processors.filing_components import business_info, name_request
from tests.unit import create_filing


@pytest.mark.parametrize('test_name,nr_number,expected_result', [
    ('Has a different NR number in IA correction', 'NR 1234568', True),
    ('Has same NR number in IA correction', 'NR 1234567', False)
])
def test_has_new_nr_for_correction(app, session, test_name, nr_number, expected_result):
    """Assert that the incorporation object is correctly populated to model objects."""
    # setup
    next_corp_num = 'BC0001095'
    with patch.object(business_info, 'get_next_corp_num', return_value=next_corp_num):
        filing = copy.deepcopy(INCORPORATION_FILING_TEMPLATE)
        identifier = 'NR 1234567'
        filing['filing']['incorporationApplication']['nameRequest']['nrNumber'] = identifier
        filing['filing']['incorporationApplication']['nameRequest']['legalName'] = 'Test'
        original_filing = create_filing('123', filing)

        effective_date = datetime.utcnow()
        filing_rec = Filing(effective_date=effective_date, filing_json=filing)
        filing_meta = FilingMeta()

        # test
        business, filing_rec, filing_meta = incorporation_filing.process(None, filing, filing_rec, filing_meta)

        # Assertions
        assert business.identifier == next_corp_num
        assert business.founding_date == effective_date
        assert business.legal_type == filing['filing']['incorporationApplication']['nameRequest']['legalType']
        assert business.legal_name == filing['filing']['incorporationApplication']['nameRequest']['legalName']

        correction_filing = copy.deepcopy(INCORPORATION_FILING_TEMPLATE)
        correction_filing['filing']['incorporationApplication']['nameRequest']['nrNumber'] = nr_number
        correction_filing['filing']['correction'] = {}
        correction_filing['filing']['correction']['correctedFilingId'] = original_filing.id
        assert name_request.has_new_nr_for_correction(correction_filing) is expected_result
