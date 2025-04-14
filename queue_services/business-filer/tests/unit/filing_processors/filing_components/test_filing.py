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
from typing import Final

from registry_schemas.example_data import ALTERATION_FILING_TEMPLATE

from business_filer.filing_processors.filing_components import filings
from tests.unit import create_filing


def test_update_filing_court_order(app, session):
    """Assert that the new aliases are created."""
    # setup
    file_number: Final  = '#1234-5678/90'
    order_date: Final = '2021-01-30T09:56:01+08:00'
    effect_of_order: Final  = 'hasPlan'

    filing = copy.deepcopy(ALTERATION_FILING_TEMPLATE)
    alteration_filing = create_filing(token='123', json_filing=filing)
    court_order_json= {'courtOrder':
                                   {
                                       'fileNumber': file_number,
                                       'orderDate': order_date,
                                       'effectOfOrder': effect_of_order
                                    }
    }

    # test
    filings.update_filing_court_order(alteration_filing, court_order_json['courtOrder'])

    # validate
    assert file_number == alteration_filing.court_order_file_number
    assert datetime.fromisoformat(order_date) == alteration_filing.court_order_date
    assert effect_of_order == alteration_filing.court_order_effect_of_order
    
