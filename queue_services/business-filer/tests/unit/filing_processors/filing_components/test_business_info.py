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
"""The Unit Tests for the business filing component processors."""
import pytest
from business_model.models import Business

from business_filer.filing_processors.filing_components import business_info


@pytest.mark.parametrize('test_name,original_legal_type,new_legal_type,expected_legal_type,expected_error', [
    ('valid C -> BC', 'C', 'BC', 'BC', None),
    ('valid None -> BC', None, 'BC', 'BC', None),
    ('valid None -> BC', 'C', None, 'C', None)
])
def test_set_corp_type(app, session,
                       test_name, original_legal_type, new_legal_type, expected_legal_type, expected_error):
    """Assert that the corp type is set correctly."""
    new_data = {
        'legalType': new_legal_type
    }

    business = Business(legal_type=original_legal_type)
    err = business_info.set_corp_type(business, new_data)

    assert business.legal_type == expected_legal_type
    assert err == expected_error
