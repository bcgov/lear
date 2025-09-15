# Copyright © 2025 Province of British Columbia
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
"""Test Suite for common validations sharing through the different filings."""
import copy
from unittest.mock import patch

import pytest
from registry_schemas.example_data import (
    AMALGAMATION_APPLICATION,
    APPOINT_RECEIVER,
    CHANGE_OF_ADDRESS,
    CHANGE_OF_DIRECTORS,
    CHANGE_OF_OFFICERS,
    CHANGE_OF_REGISTRATION,
    CONTINUATION_IN,
    CORRECTION_INCORPORATION,
    DISSOLUTION,
    FILING_HEADER,
    FIRMS_CONVERSION,
    INCORPORATION,
    INTENT_TO_LIQUIDATE,
    REGISTRATION,
    RESTORATION,
)

from legal_api.services.filings.validations.common_validations import (
    find_updated_keys_for_firms,
    validate_certify_name,
    validate_certified_by,
    validate_offices_addresses,
    validate_parties_addresses,
    validate_staff_payment,
)


CORRECTION = copy.deepcopy(CORRECTION_INCORPORATION['filing']['correction'])


INVALID_ADDRESS_NO_POSTAL_CODE = {
    'streetAddress': 'address line one',
    'addressCity': 'address city',
    'addressCountry': 'CA',
    'postalCode': None,
    'addressRegion': 'BC'
}

VALID_ADDRESS_NO_POSTAL_CODE = {
    'streetAddress': 'address line one',
    'addressCity': 'address city',
    'addressCountry': 'HK',
    'postalCode': None,
    'addressRegion': ''
}


@pytest.mark.parametrize('filing_type, filing_data, office_type', [
    ('amaglamationApplication', AMALGAMATION_APPLICATION, 'registeredOffice'),
    ('changeOfAddress', CHANGE_OF_ADDRESS, 'registeredOffice'),
    ('changeOfRegistration', CHANGE_OF_REGISTRATION, 'businessOffice'),
    ('continuationIn', CONTINUATION_IN, 'registeredOffice'),
    ('conversion', FIRMS_CONVERSION, 'businessOffice'),
    ('correction', CORRECTION, 'registeredOffice'),
    ('incorporationApplication', INCORPORATION, 'registeredOffice'),
    ('registration', REGISTRATION, 'businessOffice'),
    ('restoration', RESTORATION, 'registeredOffice'),
    ('intentToLiquidate', INTENT_TO_LIQUIDATE, 'liquidationOffice')
])
def test_validate_offices_addresses_postal_code(session, filing_type, filing_data, office_type):
    """Test postal code of office address can be validated."""
    filing = copy.deepcopy(FILING_HEADER)
    filing['filing'][filing_type] = copy.deepcopy(filing_data)

    err1 = validate_offices_addresses(filing, filing_type)
    assert err1 == []

    filing['filing'][filing_type]['offices'][office_type]['deliveryAddress'] = INVALID_ADDRESS_NO_POSTAL_CODE
    err2 = validate_offices_addresses(filing, filing_type)
    assert err2
    assert err2[0]['error'] == 'Postal code is required.'

    filing['filing'][filing_type]['offices'][office_type]['deliveryAddress'] = VALID_ADDRESS_NO_POSTAL_CODE
    err3 = validate_offices_addresses(filing, filing_type)
    assert err3 == []
    

@pytest.mark.parametrize('filing_type, filing_data, party_key', [
    ('amaglamationApplication', AMALGAMATION_APPLICATION, 'parties'),
    ('appointReceiver', APPOINT_RECEIVER, 'parties'),
    ('changeOfDirectors', CHANGE_OF_DIRECTORS, 'directors'),
    ('changeOfOfficers', CHANGE_OF_OFFICERS, 'relationships'),
    ('changeOfRegistration', CHANGE_OF_REGISTRATION, 'parties'),
    ('continuationIn', CONTINUATION_IN, 'parties'),
    ('conversion', FIRMS_CONVERSION, 'parties'),
    ('correction', CORRECTION, 'parties'),
    ('dissolution', DISSOLUTION, 'parties'),
    ('incorporationApplication', INCORPORATION, 'parties'),
    ('registration', REGISTRATION, 'parties'),
    ('restoration', RESTORATION, 'parties'),
    ('intentToLiquidate', INTENT_TO_LIQUIDATE, 'parties')
])
def test_validate_parties_addresses_postal_code(session, filing_type, filing_data, party_key):
    """Test postal code of party address can be validated."""
    filing = copy.deepcopy(FILING_HEADER)
    filing['filing'][filing_type] = copy.deepcopy(filing_data)

    err1 = validate_parties_addresses(filing, filing_type, party_key)
    assert err1 == []

    filing['filing'][filing_type][party_key][0]['deliveryAddress'] = INVALID_ADDRESS_NO_POSTAL_CODE
    err2 = validate_parties_addresses(filing, filing_type, party_key)
    assert err2
    assert err2[0]['error'] == 'Postal code is required.'

    filing['filing'][filing_type][party_key][0]['deliveryAddress'] = VALID_ADDRESS_NO_POSTAL_CODE
    err3 = validate_parties_addresses(filing, filing_type, party_key)
    assert err3 == []

@pytest.mark.parametrize('payment_type, expected', [
    ({}, False),
    ({'routingSlipNumber': '123'}, True),
    ({'bcolAccountNumber': '12345'}, True),
    ({'datNumber': '1234567'}, True),
    ({'waiveFees': True}, True),
    ({'priority': False}, True),
])
def test_validate_staff_payment(session, payment_type, expected):
    """Test staff payment validation."""
    filing = {
        'filing': {
            'header': {
                **payment_type
                }
        }
    }
    result = validate_staff_payment(filing)
    assert result == expected

@pytest.mark.parametrize(('certified_value', 'expected'), [
    ('First Last', False),
    ('Forst Last', True),
    ('NOT_SET', True),
    ('First  Last', True)
])
def test_validate_certify(session, monkeypatch, certified_value, expected):
    """Test certify name validation when no JWT is present."""
    filing = copy.deepcopy(FILING_HEADER)
    if certified_value != 'NOT_SET':
        filing['filing']['header']['certifiedBy'] = certified_value
    with patch('legal_api.services.filings.validations.common_validations.g') as mock_g:
        mock_g.jwt_oidc_token_info = {'name': 'First Last'}
        result = validate_certify_name(filing)
        assert result == expected

@patch('legal_api.services.filings.validations.common_validations.PartyRole')
@patch('legal_api.services.filings.validations.common_validations.Party')
@patch('legal_api.services.filings.validations.common_validations.Address')
def test_find_updated_keys_for_firms(mock_address, mock_party, mock_party_role):
    """Test find updated keys for firms."""
    business = type('Business', (), {'id': 1, 'legal_type': 'GP'})()

    mock_party_role.RoleTypes.PROPRIETOR.value = 'proprietor'
    mock_party_role.RoleTypes.PARTNER.value = 'partner'

    mock_role1 = type('PartyRole', (), {'party_id': 1})()
    mock_role2 = type('PartyRole', (), {'party_id': 2})()
    mock_party_role.get_parties_by_role.return_value = [mock_role1, mock_role2]

    mock_db_party1 = type('Party', (), {
        'email': 'john@example.com',
        'first_name': 'John',
        'middle_initial': 'A',
        'last_name': 'Doe',
        'organization_name': '',
        'mailing_address_id': 1,
        'delivery_address_id': 1
    })()
    
    mock_db_party2 = type('Party', (), {
        'email': 'jane@example.com',
        'first_name': 'Jane',
        'middle_initial': 'B',
        'last_name': 'Smith',
        'organization_name': '',
        'mailing_address_id': 2,
        'delivery_address_id': 2
    })()
    
    mock_role1.party = mock_db_party1
    mock_role2.party = mock_db_party2
    
    mock_address1 = type('Address', (), {
        'street': '123 Main St',
        'city': 'Vancouver',
        'region': 'BC',
        'postal_code': 'V6B 1A1',
        'country': 'CA',
        'delivery_instructions': '',
        'street_additional': ''
    })()
    
    mock_address2 = type('Address', (), {
        'street': '456 Oak Ave',
        'city': 'Vancouver',
        'region': 'BC',
        'postal_code': 'V6B 1A1',
        'country': 'CA',
        'delivery_instructions': '',
        'street_additional': ''
    })()
    
    def mock_address_find_by_id(address_id):
        if address_id == 1:
            return mock_address1
        elif address_id == 2:
            return mock_address2
        return None
    
    mock_address.find_by_id = mock_address_find_by_id
    
    filing_json = {
        'filing': {
            'changeOfRegistration': {
                'parties': [
                    {
                        'roles': [{'roleType': 'partner'}],
                        'officer': {
                            'id': 1,
                            'email': 'john.new@example.com',
                            'firstName': 'John',
                            'middleName': 'A',
                            'lastName': 'Doe',
                            'organizationName': ''
                        },
                        'mailingAddress': {
                            'streetAddress': '123 Main St',
                            'addressCity': 'Vancouver',
                            'addressRegion': 'BC',
                            'postalCode': 'V6B 1A1',
                            'addressCountry': 'CA',
                            'deliveryInstructions': '',
                            'streetAddressAdditional': ''
                        },
                        'deliveryAddress': {
                            'street': '456 Oak Ave',
                            'city': 'Vancouver',
                            'region': 'BC',
                            'postal_code': 'V6B 1A1',
                            'country': 'CA',
                            'delivery_instructions': '',
                            'street_additional': ''
                        }
                    },
                    {
                        'roles': [{'roleType': 'partner'}],
                        'officer': {
                            'email': 'newpartner@example.com',
                            'firstName': 'New',
                            'middleName': 'C',
                            'lastName': 'Partner',
                            'organizationName': ''
                        },
                        'mailingAddress': {
                            'streetAddress': '123 Main St',
                            'addressCity': 'Vancouver',
                            'addressRegion': 'BC',
                            'postalCode': 'V6B 1A1',
                            'addressCountry': 'CA',
                            'deliveryInstructions': '',
                            'streetAddressAdditional': ''
                        },
                        'deliveryAddress': {
                            'street': '456 Oak Ave',
                            'city': 'Vancouver',
                            'region': 'BC',
                            'postal_code': 'V6B 1A1',
                            'country': 'CA',
                            'delivery_instructions': '',
                            'street_additional': ''
                        }
                    }
                ]
            }
        }
    }
    
    result = find_updated_keys_for_firms(business, filing_json, 'changeOfRegistration')

    assert len(result) == 1

    edited_result = next((r for r in result if 'email_changed' in r), None)
    assert edited_result['email_changed'] == True
    assert edited_result['name_changed'] == False
    assert edited_result['address_changed'] == False
    assert edited_result['delivery_address_changed'] == True
@pytest.mark.parametrize('input_value, expected_value, expect_error', [
    ('John   Doe', 'John Doe', False),
    ('   \t   ', '', True),
    ('', '', False),
    (None, None, False),
])
def test_validate_and_normalize_certified_by(input_value, expected_value, expect_error):
    """Test that certified by field can be validated."""
    filing = copy.deepcopy(FILING_HEADER)
    filing['filing']['header']['certifiedBy'] = input_value

    errors = validate_certified_by(filing)

    if expect_error:
        assert errors
        assert errors[0]['error'] == 'Certified By field cannot be only whitespace.'
        assert errors[0]['path'] == '/filing/header/certifiedBy'
    else:
        assert errors == []

    assert filing['filing']['header']['certifiedBy'] == expected_value
