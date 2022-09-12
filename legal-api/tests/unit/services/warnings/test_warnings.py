# Copyright © 2022 Province of British Columbia
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in business with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Test suite to ensure Firms business checks work correctly."""
from unittest.mock import patch
from datetime import datetime

import pytest

from legal_api.services import check_warnings
from legal_api.services.warnings.business.business_checks import firms
from tests.unit.services.warnings import factory_party_role_person, factory_party_role_organization, factory_party_roles, \
    create_business, factory_address, create_filing

from legal_api.models import Address, Business, Office, PartyRole



@pytest.mark.parametrize(
    'test_name, legal_type, identifier, has_office, num_persons_roles, num_org_roles, filing_types, filing_has_completing_party, expected_code, expected_msg',
    [
        # SP tests
        ('SUCCESS', 'SP', 'FM0000001', True, 1, 0, ['registration'], [True], None, None),
        ('SUCCESS', 'SP', 'FM0000001', True, 0, 1, ['registration'], [True], None, None),
        ('SUCCESS', 'SP', 'FM0000001', True, 1, 0, ['registration', 'conversion'], [False, True], None, None),
        ('SUCCESS', 'SP', 'FM0000001', True, 0, 1, ['registration', 'conversion'], [False, True], None, None),
        ('FAIL_NO_PROPRIETOR', 'SP', 'FM0000001', True, 0, 0, ['registration'], [True], 'NO_PROPRIETOR', 'A proprietor is required.'),
        ('FAIL_NO_OFFICE', 'SP', 'FM0000001', False, 1, 0, ['registration'], [True], 'NO_BUSINESS_OFFICE', 'A business office is required.'),
        ('FAIL_NO_COMPLETING_PARTY', 'SP', 'FM0000001', True, 1, 0, ['registration'], [False], 'NO_COMPLETING_PARTY', 'A completing party is required.'),

        # GP tests
        ('SUCCESS', 'GP', 'FM0000001', True, 2, 0, ['registration'], [True], None, None),
        ('SUCCESS', 'GP', 'FM0000001', True, 0, 2, ['registration'], [True], None, None),
        ('SUCCESS', 'GP', 'FM0000001', True, 1, 1, ['registration'], [True], None, None),
        ('SUCCESS', 'GP', 'FM0000001', True, 2, 0, ['registration', 'conversion'], [False, True], None, None),
        ('SUCCESS', 'GP', 'FM0000001', True, 0, 2, ['registration', 'conversion'], [False, True], None, None),
        ('SUCCESS', 'GP', 'FM0000001', True, 1, 1, ['registration', 'conversion'], [False, True], None, None),
        ('FAIL_NO_PARTNER', 'GP', 'FM0000001', True, 0, 0, ['registration'], [True], 'NO_PARTNER', '2 partners are required.'),
        ('FAIL_NO_PARTNER', 'GP', 'FM0000001', True, 1, 0, ['registration'], [True], 'NO_PARTNER', '2 partners are required.'),
        ('FAIL_NO_PARTNER', 'GP', 'FM0000001', True, 0, 1, ['registration'], [True], 'NO_PARTNER', '2 partners are required.'),
        ('FAIL_NO_OFFICE', 'GP', 'FM0000001', False, 2, 0, ['registration'], [True], 'NO_BUSINESS_OFFICE', 'A business office is required.'),
        ('FAIL_NO_COMPLETING_PARTY', 'GP', 'FM0000001', True, 2, 0, ['registration'], [False], 'NO_COMPLETING_PARTY', 'A completing party is required.'),

    ])
def test_check_warnings(session, test_name, legal_type, identifier, has_office, num_persons_roles:int, num_org_roles:int,
                        filing_types: list, filing_has_completing_party: list, expected_code, expected_msg):
    """Assert that warnings check functions properly."""

    business = None

    create_business(legal_type=legal_type,
                    identifier=identifier,
                    create_office=has_office,
                    create_office_mailing_address=has_office,
                    create_office_delivery_address=has_office,
                    firm_num_persons_roles=num_persons_roles,
                    firm_num_org_roles=num_org_roles,
                    filing_types=filing_types,
                    filing_has_completing_party=filing_has_completing_party,
                    start_date=datetime.utcnow())

    business = Business.find_by_identifier(identifier)
    assert business
    assert business.legal_type == legal_type
    assert business.identifier == identifier

    with patch.object(firms, 'check_address', return_value=[]):
        result = check_warnings(business)

    if expected_code:
        assert len(result) == 1
        warning = result[0]
        assert warning['code'] == expected_code
        assert warning['message'] == expected_msg
        assert warning['warningType'] == 'MISSING_REQUIRED_BUSINESS_INFO'
    else:
        assert len(result) == 0
