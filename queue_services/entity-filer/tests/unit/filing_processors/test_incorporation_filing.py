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
"""The Unit Tests for the Incorporation filing."""

import copy
from datetime import datetime
from unittest.mock import patch

from legal_api.models import Filing
from registry_schemas.example_data import INCORPORATION_FILING_TEMPLATE

from entity_filer.filing_processors import incorporation_filing
from tests.unit import create_filing


def test_incorporation_filing_process(app, session):
    """Assert that the incorporation object is correctly populated to model objects."""
    # setup
    next_corp_num = 'BC0001095'
    with patch.object(incorporation_filing, 'get_next_corp_num', return_value=next_corp_num) as mock_get_next_corp_num:
        filing = copy.deepcopy(INCORPORATION_FILING_TEMPLATE)
        identifier = 'NR 1234567'
        filing['filing']['incorporationApplication']['nameRequest']['nrNumber'] = identifier
        filing['filing']['incorporationApplication']['nameRequest']['legalName'] = 'Test'
        create_filing('123', filing)

        effective_date = datetime.utcnow()
        filing_rec = Filing(effective_date=effective_date, filing_json=filing)

        # test
        business, filing_rec = incorporation_filing.process(None, filing['filing'], filing_rec)

        # Assertions
        assert business.identifier == next_corp_num
        assert business.founding_date == effective_date
        assert business.legal_type == filing['filing']['incorporationApplication']['nameRequest']['legalType']
        assert business.legal_name == filing['filing']['incorporationApplication']['nameRequest']['legalName']
        assert len(business.share_classes.all()) == 2
        assert len(business.offices.all()) == 2  # One office is created in create_business method.

    mock_get_next_corp_num.assert_called_with(filing['filing']['incorporationApplication']['nameRequest']['legalType'])
