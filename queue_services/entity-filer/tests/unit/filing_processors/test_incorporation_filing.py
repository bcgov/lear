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
from unittest.mock import patch

from entity_filer.filing_processors import incorporation_filing
from tests.unit import INCORP_FILING, create_business, create_filing


def test_incorporation_filing_process(app, session):
    """Assert that the incorporation object is correctly populated to model objects."""
    # setup
    next_corp_num = 'BC0001095'
    with patch.object(incorporation_filing, 'get_next_corp_num', return_value=next_corp_num) as mock_get_next_corp_num:
        filing = copy.deepcopy(INCORP_FILING)
        identifier = filing['filing']['incorporationApplication']['nameRequest']['nrNumber']
        business = create_business(identifier)
        create_filing('123', filing, business.id)

        # test
        incorporation_filing.process(business, filing['filing'])

        # Assertions
        assert business.identifier == 'BC0001095'
        assert len(business.share_classes.all()) == 2
        assert len(business.offices.all()) == 3  # One office is created in create_business method.

    mock_get_next_corp_num.assert_called_with(filing['filing']['incorporationApplication']['nameRequest']['legalType'],
                                              None)
