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

from tests.unit.services.warnings import factory_party_role_person, factory_party_role_organization, factory_party_roles,\
    create_business, factory_address, create_filing

from legal_api.models import Address, Business, Office, PartyRole
from legal_api.services.warnings.business.business_checks import BusinessWarningReferers, firms
from legal_api.services.warnings.business.business_checks.firms import check_address, check_firm_party, check_firm_parties, \
    check_office, check_completing_party, check_completing_party_for_filing, check_parties, check_business,\
    check_start_date



@pytest.mark.parametrize(
    'test_name, address_type, null_addr_field_name, referer, expected_code, expected_msg',
    [
        # business office mailing address checks
        ('SUCCESS', 'mailing', None, BusinessWarningReferers.BUSINESS_OFFICE, None, None),
        ('FAIL_NO_STREET', 'mailing', 'street', BusinessWarningReferers.BUSINESS_OFFICE,
         'NO_BUSINESS_OFFICE_MAILING_ADDRESS_STREET', 'Street is required for business office mailing address.'),
        ('FAIL_NO_CITY', 'mailing', 'city', BusinessWarningReferers.BUSINESS_OFFICE,
         'NO_BUSINESS_OFFICE_MAILING_ADDRESS_CITY', 'City is required for business office mailing address.'),
        ('FAIL_NO_COUNTRY', 'mailing', 'country', BusinessWarningReferers.BUSINESS_OFFICE,
         'NO_BUSINESS_OFFICE_MAILING_ADDRESS_COUNTRY', 'Country is required for business office mailing address.'),
        ('FAIL_NO_POSTAL_CODE', 'mailing', 'postal_code', BusinessWarningReferers.BUSINESS_OFFICE,
         'NO_BUSINESS_OFFICE_MAILING_ADDRESS_POSTAL_CODE', 'Postal code is required for business office mailing address.'),
        ('FAIL_NO_REGION', 'mailing', 'region', BusinessWarningReferers.BUSINESS_OFFICE,
         'NO_BUSINESS_OFFICE_MAILING_ADDRESS_REGION', 'Region is required for business office mailing address.'),

        # business office delivery address checks
        ('SUCCESS', 'delivery', None, BusinessWarningReferers.BUSINESS_OFFICE, None, None),
        ('FAIL_NO_STREET', 'delivery', 'street', BusinessWarningReferers.BUSINESS_OFFICE,
         'NO_BUSINESS_OFFICE_DELIVERY_ADDRESS_STREET', 'Street is required for business office delivery address.'),
        ('FAIL_NO_CITY', 'delivery', 'city', BusinessWarningReferers.BUSINESS_OFFICE,
         'NO_BUSINESS_OFFICE_DELIVERY_ADDRESS_CITY', 'City is required for business office delivery address.'),
        ('FAIL_NO_COUNTRY', 'delivery', 'country', BusinessWarningReferers.BUSINESS_OFFICE,
         'NO_BUSINESS_OFFICE_DELIVERY_ADDRESS_COUNTRY', 'Country is required for business office delivery address.'),
        ('FAIL_NO_POSTAL_CODE', 'delivery', 'postal_code', BusinessWarningReferers.BUSINESS_OFFICE,
         'NO_BUSINESS_OFFICE_DELIVERY_ADDRESS_POSTAL_CODE', 'Postal code is required for business office delivery address.'),
        ('FAIL_NO_REGION', 'delivery', 'region', BusinessWarningReferers.BUSINESS_OFFICE,
         'NO_BUSINESS_OFFICE_DELIVERY_ADDRESS_REGION', 'Region is required for business office delivery address.'),

        # business office mailing address checks
        ('SUCCESS', 'mailing', None, BusinessWarningReferers.BUSINESS_PARTY, None, None),
        ('FAIL_NO_STREET', 'mailing', 'street', BusinessWarningReferers.BUSINESS_PARTY,
         'NO_BUSINESS_PARTY_MAILING_ADDRESS_STREET', 'Street is required for business party mailing address.'),
        ('FAIL_NO_CITY', 'mailing', 'city', BusinessWarningReferers.BUSINESS_PARTY,
         'NO_BUSINESS_PARTY_MAILING_ADDRESS_CITY', 'City is required for business party mailing address.'),
        ('FAIL_NO_COUNTRY', 'mailing', 'country', BusinessWarningReferers.BUSINESS_PARTY,
         'NO_BUSINESS_PARTY_MAILING_ADDRESS_COUNTRY', 'Country is required for business party mailing address.'),
        ('FAIL_NO_POSTAL_CODE', 'mailing', 'postal_code', BusinessWarningReferers.BUSINESS_PARTY,
         'NO_BUSINESS_PARTY_MAILING_ADDRESS_POSTAL_CODE', 'Postal code is required for business party mailing address.'),
        ('FAIL_NO_REGION', 'mailing', 'region', BusinessWarningReferers.BUSINESS_PARTY,
         'NO_BUSINESS_PARTY_MAILING_ADDRESS_REGION', 'Region is required for business party mailing address.'),

        # completing party mailing address checks
        ('SUCCESS', 'mailing', None, BusinessWarningReferers.COMPLETING_PARTY, None, None),
        ('FAIL_NO_STREET', 'mailing', 'street', BusinessWarningReferers.COMPLETING_PARTY,
         'NO_COMPLETING_PARTY_MAILING_ADDRESS_STREET', 'Street is required for completing party mailing address.'),
        ('FAIL_NO_CITY', 'mailing', 'city', BusinessWarningReferers.COMPLETING_PARTY,
         'NO_COMPLETING_PARTY_MAILING_ADDRESS_CITY', 'City is required for completing party mailing address.'),
        ('FAIL_NO_COUNTRY', 'mailing', 'country', BusinessWarningReferers.COMPLETING_PARTY,
         'NO_COMPLETING_PARTY_MAILING_ADDRESS_COUNTRY', 'Country is required for completing party mailing address.'),
        ('FAIL_NO_POSTAL_CODE', 'mailing', 'postal_code', BusinessWarningReferers.COMPLETING_PARTY,
         'NO_COMPLETING_PARTY_MAILING_ADDRESS_POSTAL_CODE', 'Postal code is required for completing party mailing address.'),
        ('FAIL_NO_REGION', 'mailing', 'region', BusinessWarningReferers.COMPLETING_PARTY,
         'NO_COMPLETING_PARTY_MAILING_ADDRESS_REGION', 'Region is required for completing party mailing address.'),
    ])
def test_check_address(session, test_name, address_type, null_addr_field_name, referer, expected_code, expected_msg):
    """Assert that business address checks functions properly."""

    fail_testcase_names = ['FAIL_NO_STREET', 'FAIL_NO_CITY', 'FAIL_NO_COUNTRY', 'FAIL_NO_POSTAL_CODE', 'FAIL_NO_REGION']

    if test_name == 'SUCCESS':
        address = factory_address(address_type=address_type)
    elif test_name in (fail_testcase_names):
        address = factory_address(address_type=address_type,
                                  make_null_field_name=null_addr_field_name)
    result = check_address(address, address_type, referer)

    if expected_code:
        assert len(result) == 1
        business_warning = result[0]
        assert business_warning['code'] == expected_code
        assert business_warning['message'] == expected_msg
    else:
        assert len(result) == 0


@pytest.mark.parametrize(
    'test_name, legal_type, role, party_type, expected_code, expected_msg',
    [
        # SP tests
        ('SUCCESS', 'SP', 'proprietor', 'person', None, None),
        ('SUCCESS', 'SP', 'proprietor', 'organization', None, None),
        ('FAIL_NO_PERSON_NAME', 'SP', 'proprietor', 'person', 'NO_PROPRIETOR_PERSON_NAME', 'Proprietor name is required.'),
        ('FAIL_NO_ORG_NAME', 'SP', 'proprietor', 'organization', 'NO_PROPRIETOR_ORG_NAME', 'Proprietor organization name is required.'),

        # GP tests
        ('SUCCESS', 'GP', 'partner', 'person', None, None),
        ('SUCCESS', 'GP', 'partner', 'organization', None, None),
        ('FAIL_NO_PERSON_NAME', 'GP', 'partner', 'person', 'NO_PARTNER_PERSON_NAME', 'Partner name is required.'),
        ('FAIL_NO_ORG_NAME', 'GP', 'partner', 'organization', 'NO_PARTNER_ORG_NAME', 'Partner organization name is required.'),
    ])
def test_check_firm_party(session, test_name, legal_type, role, party_type, expected_code, expected_msg):
    """Assert that business firm party checks functions properly."""

    if party_type == 'person':
        party_role = factory_party_role_person(role)
    elif party_type == 'organization':
        party_role = factory_party_role_organization(role)

    if test_name == 'FAIL_NO_PERSON_NAME':
        party_role.party.first_name = None
        party_role.party.last_name = None
    elif test_name == 'FAIL_NO_ORG_NAME':
        party_role.party.organization_name = None

    with patch.object(firms, 'check_address', return_value=[]):
        result = check_firm_party(legal_type, party_role)

    if expected_code:
        assert len(result) == 1
        business_warning = result[0]
        assert business_warning['code'] == expected_code
        assert business_warning['message'] == expected_msg
    else:
        assert len(result) == 0


@pytest.mark.parametrize(
    'test_name, legal_type, role, num_persons_roles, num_org_roles, expected_code, expected_msg',
    [
        # SP tests
        ('SUCCESS', 'SP', 'proprietor', 1, 0, None, None),
        ('SUCCESS', 'SP', 'proprietor', 0, 1, None, None),
        ('FAIL_PROPRIETOR_REQUIRED', 'SP', 'proprietor', 0, 0, 'NO_PROPRIETOR', 'A proprietor is required.'),

        # GP tests
        ('SUCCESS', 'GP', 'partner', 2, 0, None, None),
        ('SUCCESS', 'GP', 'partner', 0, 2, None, None),
        ('SUCCESS', 'GP', 'partner', 1, 1, None, None),
        ('FAIL_PARTNER_REQUIRED', 'GP', 'partner', 0, 0, 'NO_PARTNER', '2 partners are required.'),
        ('FAIL_PARTNER_REQUIRED', 'GP', 'partner', 1, 0, 'NO_PARTNER', '2 partners are required.'),
        ('FAIL_PARTNER_REQUIRED', 'GP', 'partner', 0, 1, 'NO_PARTNER', '2 partners are required.'),
    ])
def test_check_firm_parties(session, test_name, legal_type, role, num_persons_roles:int, num_org_roles:int,
                            expected_code, expected_msg):
    """Assert that business firm parties check functions properly."""

    party_roles = factory_party_roles(role, num_persons_roles, num_org_roles)

    with patch.object(firms, 'check_firm_party', return_value=[]):
        result = check_firm_parties(legal_type, party_roles)

    if expected_code:
        assert len(result) == 1
        business_warning = result[0]
        assert business_warning['code'] == expected_code
        assert business_warning['message'] == expected_msg
    else:
        assert len(result) == 0


@pytest.mark.parametrize(
    'test_name, role, party_type, expected_code, expected_msg',
    [
        ('SUCCESS', 'completing_party', 'person', None, None),
        ('SUCCESS', 'completing_party', 'organization', None, None),
        ('FAIL_NO_PERSON_NAME', 'completing_party', 'person', 'NO_COMPLETING_PARTY_PERSON_NAME', 'Completing Party name is required.'),
        ('FAIL_NO_ORG_NAME', 'completing_party', 'organization', 'NO_COMPLETING_PARTY_ORG_NAME', 'Completing Party organization name is required.'),
    ])
def test_check_completing_party(session, test_name, role, party_type, expected_code, expected_msg):
    """Assert that business firm party checks functions properly."""

    if party_type == 'person':
        party_role = factory_party_role_person(role)
    elif party_type == 'organization':
        party_role = factory_party_role_organization(role)

    if test_name == 'FAIL_NO_PERSON_NAME':
        party_role.party.first_name = None
        party_role.party.last_name = None
    elif test_name == 'FAIL_NO_ORG_NAME':
        party_role.party.organization_name = None

    with patch.object(firms, 'check_address', return_value=[]):
        result = check_completing_party(party_role)

    if expected_code:
        assert len(result) == 1
        business_warning = result[0]
        assert business_warning['code'] == expected_code
        assert business_warning['message'] == expected_msg
    else:
        assert len(result) == 0


@pytest.mark.parametrize(
    'test_name, filing_type, expected_code, expected_msg',
    [
        ('SUCCESS', 'registration', None, None),
        ('SUCCESS', 'conversion', None, None),
        ('FAIL_NO_COMPLETING_PARTY', 'registration', 'NO_COMPLETING_PARTY', 'A completing party is required.'),
        ('FAIL_NO_COMPLETING_PARTY', 'conversion', 'NO_COMPLETING_PARTY', 'A completing party is required.'),
    ])
def test_check_completing_party_for_filing(session, test_name, filing_type, expected_code, expected_msg):
    """Assert that business firm parties check functions properly."""

    filing = None
    if test_name == 'SUCCESS':
        filing = create_filing(filing_type=filing_type, add_completing_party=True)
    elif test_name == 'FAIL_NO_COMPLETING_PARTY':
        filing = create_filing(filing_type=filing_type, add_completing_party=False)

    with patch.object(firms, 'check_completing_party', return_value=[]):
        result = check_completing_party_for_filing(filing)

    if expected_code:
        assert len(result) == 1
        business_warning = result[0]
        assert business_warning['code'] == expected_code
        assert business_warning['message'] == expected_msg
    else:
        assert len(result) == 0


@pytest.mark.parametrize(
    'test_name, legal_type, identifier, num_persons_roles, num_org_roles, filing_types, filing_has_completing_party, expected_code, expected_msg',
    [
        # SP tests
        ('SUCCESS', 'SP', 'FM0000001', 1, 0, ['registration'], [True], None, None),
        ('SUCCESS', 'SP', 'FM0000001', 0, 1, ['registration'], [True], None, None),
        ('SUCCESS', 'SP', 'FM0000001', 1, 0, ['registration', 'conversion'], [False, True], None, None),
        ('SUCCESS', 'SP', 'FM0000001', 0, 1, ['registration', 'conversion'], [False, True], None, None),
        ('FAIL_NO_PROPRIETOR', 'SP', 'FM0000001', 0, 0, ['registration'], [True], 'NO_PROPRIETOR', 'A proprietor is required.'),
        ('NO_COMPLETING_PARTY', 'SP', 'FM0000001', 1, 0, ['registration'], [False], 'NO_COMPLETING_PARTY', 'A completing party is required.'),
        ('NO_COMPLETING_PARTY', 'SP', 'FM0000001', 0, 1, ['registration'], [False], 'NO_COMPLETING_PARTY', 'A completing party is required.'),

        # GP tests
        ('SUCCESS', 'GP', 'FM0000001', 2, 0, ['registration'], [True], None, None),
        ('SUCCESS', 'GP', 'FM0000001', 0, 2, ['registration'], [True], None, None),
        ('SUCCESS', 'GP', 'FM0000001', 1, 1, ['registration'], [True], None, None),
        ('SUCCESS', 'GP', 'FM0000001', 2, 0, ['registration', 'conversion'], [False, True], None, None),
        ('SUCCESS', 'GP', 'FM0000001', 0, 2, ['registration', 'conversion'], [False, True], None, None),
        ('SUCCESS', 'GP', 'FM0000001', 1, 1, ['registration', 'conversion'], [False, True], None, None),
        ('FAIL_NO_PARTNER', 'GP', 'FM0000001', 0, 0, ['registration'], [True], 'NO_PARTNER', '2 partners are required.'),
        ('FAIL_NO_PARTNER', 'GP', 'FM0000001', 1, 0, ['registration'], [True], 'NO_PARTNER', '2 partners are required.'),
        ('FAIL_NO_PARTNER', 'GP', 'FM0000001', 0, 1, ['registration'], [True], 'NO_PARTNER', '2 partners are required.'),
        ('NO_COMPLETING_PARTY', 'GP', 'FM0000001', 2, 0, ['registration'], [False], 'NO_COMPLETING_PARTY', 'A completing party is required.'),
        ('NO_COMPLETING_PARTY', 'GP', 'FM0000001', 0, 2, ['registration'], [False], 'NO_COMPLETING_PARTY', 'A completing party is required.'),
        ('NO_COMPLETING_PARTY', 'GP', 'FM0000001', 1, 1, ['registration'], [False], 'NO_COMPLETING_PARTY', 'A completing party is required.'),
    ])
def test_check_parties(session, test_name, legal_type, identifier, num_persons_roles:int, num_org_roles:int,
                       filing_types: list, filing_has_completing_party: list,
                       expected_code, expected_msg):
    """Assert that business firm parties check functions properly."""

    business = None

    create_business(legal_type=legal_type,
                    identifier=identifier,
                    firm_num_persons_roles=num_persons_roles,
                    firm_num_org_roles=num_org_roles,
                    filing_types=filing_types,
                    filing_has_completing_party=filing_has_completing_party)


    business = Business.find_by_identifier(identifier)
    assert business
    assert business.legal_type == legal_type
    assert business.identifier == identifier

    with patch.object(firms, 'check_address', return_value=[]):
        result = check_parties(legal_type, business)

    if expected_code:
        assert len(result) == 1
        business_warning = result[0]
        assert business_warning['code'] == expected_code
        assert business_warning['message'] == expected_msg
    else:
        assert len(result) == 0


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
def test_check_business(session, test_name, legal_type, identifier, has_office, num_persons_roles:int, num_org_roles:int,
                       filing_types: list, filing_has_completing_party: list, expected_code, expected_msg):
    """Assert that business firm parties check functions properly."""

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
        result = check_business(business)

    if expected_code:
        assert len(result) == 1
        business_warning = result[0]
        assert business_warning['code'] == expected_code
        assert business_warning['message'] == expected_msg
    else:
        assert len(result) == 0


@pytest.mark.parametrize(
    'test_name, legal_type, identifier, expected_code, expected_msg',
    [
        # SP tests
        ('SUCCESS', 'SP', 'FM0000001', None, None),
        ('FAIL_NO_OFFICE', 'SP', 'FM0000001', 'NO_BUSINESS_OFFICE', 'A business office is required.'),
        ('FAIL_NO_MAILING_ADDR', 'SP', 'FM0000001', 'NO_BUSINESS_OFFICE_MAILING_ADDRESS', 'Business office mailing address is required.'),
        ('FAIL_NO_DELIVERY_ADDR', 'SP', 'FM0000001', 'NO_BUSINESS_OFFICE_DELIVERY_ADDRESS', 'Business office delivery address is required.'),

        # GP tests
        ('SUCCESS', 'GP', 'FM0000001', None, None),
        ('FAIL_NO_OFFICE', 'GP', 'FM0000001', 'NO_BUSINESS_OFFICE', 'A business office is required.'),
        ('FAIL_NO_MAILING_ADDR', 'GP', 'FM0000001', 'NO_BUSINESS_OFFICE_MAILING_ADDRESS', 'Business office mailing address is required.'),
        ('FAIL_NO_DELIVERY_ADDR', 'GP', 'FM0000001', 'NO_BUSINESS_OFFICE_DELIVERY_ADDRESS', 'Business office delivery address is required.'),
    ])
def test_check_office(session, test_name, legal_type, identifier, expected_code, expected_msg):
    """Assert that business firm parties check functions properly."""

    business = None
    if test_name == 'SUCCESS':
        create_business(legal_type=legal_type,
                        identifier=identifier,
                        create_office=True,
                        create_office_mailing_address=True,
                        create_office_delivery_address=True)
    elif test_name == 'FAIL_NO_OFFICE':
        create_business(legal_type=legal_type,
                        identifier=identifier,
                        create_office=False)
    elif test_name == 'FAIL_NO_MAILING_ADDR':
        create_business(legal_type=legal_type,
                        identifier=identifier,
                        create_office=True,
                        create_office_mailing_address=False,
                        create_office_delivery_address=True)
    elif test_name == 'FAIL_NO_DELIVERY_ADDR':
        create_business(legal_type=legal_type,
                        identifier=identifier,
                        create_office=True,
                        create_office_mailing_address=True,
                        create_office_delivery_address=False)

    business = Business.find_by_identifier(identifier)
    assert business
    assert business.legal_type == legal_type
    assert business.identifier == identifier

    result = check_office(business)

    if expected_code:
        assert len(result) == 1
        business_warning = result[0]
        assert business_warning['code'] == expected_code
        assert business_warning['message'] == expected_msg
    else:
        assert len(result) == 0


@pytest.mark.parametrize(
    'test_name, legal_type, identifier, expected_code, expected_msg',
    [
        # SP tests
        ('SUCCESS', 'SP', 'FM0000001', None, None),
        ('FAIL_NO_START_DATE', 'SP', 'FM0000001', 'NO_START_DATE', 'A start date is required.'),
        # GP tests
        ('SUCCESS', 'GP', 'FM0000001', None, None),
        ('FAIL_NO_START_DATE', 'GP', 'FM0000001', 'NO_START_DATE', 'A start date is required.'),
    ]
)
def test_check_start_date(session, test_name, legal_type, identifier, expected_code, expected_msg):
    """Assert that business start date check works properly."""

    business = None

    business = create_business(legal_type=legal_type,
                    identifier=identifier)
    if test_name == 'SUCCESS':
        business.start_date = datetime.utcnow()
        business.save()

    business = Business.find_by_identifier(identifier)
    assert business
    assert business.legal_type == legal_type
    assert business.identifier == identifier

    result = check_start_date(business)

    if expected_code:
        assert len(result) == 1
        business_warning = result[0]
        assert business_warning['code'] == expected_code
        assert business_warning['message'] == expected_msg
    else:
        assert len(result) == 0
