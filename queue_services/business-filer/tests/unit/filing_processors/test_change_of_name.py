# Copyright © 2019 Province of British Columbia
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
"""The Unit Tests for the Change of Name filing."""
from business_filer.filing_meta import FilingMeta
from business_filer.filing_processors import change_of_name
from tests.unit import create_business


def test_change_of_name_process(app, session):
    """Assert that the legal name is changed."""
    # setup
    new_name = 'new legal_name'
    identifier = 'CP1234567'
    con = {'changeOfName': {'legalName': new_name}}

    business = create_business(identifier)
    business.legal_name = 'original name'

    filing_meta = FilingMeta()

    # test
    change_of_name.process(business, con, filing_meta)

    # validate
    assert business.legal_name == new_name


def test_change_of_name_with_nr_process(app, session):
    """Assert that the legal name is changed."""
    # setup
    new_name = 'new legal_name'
    identifier = 'CP1234567'
    con = {
        'changeOfName': {
            'nameRequest': {
                'nrNumber': 'NR 8798956',
                'legalName': new_name,
                'legalType': 'BC'
            }
        }
    }

    business = create_business(identifier)
    business.legal_name = 'original name'

    filing_meta = FilingMeta()

    # test
    change_of_name.process(business, con, filing_meta)

    # validate
    assert business.legal_name == new_name
