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
from datetime import datetime
from http import HTTPStatus
from unittest.mock import patch

from legal_api.errors import Error
from legal_api.models.party import Party
from legal_api.models.party_role import PartyRole
import pytest
from registry_schemas.example_data import (
    AMALGAMATION_APPLICATION,
    CHANGE_OF_ADDRESS,
    CHANGE_OF_DIRECTORS,
    CHANGE_OF_LIQUIDATORS,
    CHANGE_OF_OFFICERS,
    CHANGE_OF_RECEIVERS,
    CHANGE_OF_REGISTRATION,
    CHANGE_OF_REGISTRATION_TEMPLATE,
    CONTINUATION_IN,
    CORRECTION_INCORPORATION,
    DISSOLUTION,
    FILING_HEADER,
    FIRMS_CONVERSION,
    INCORPORATION,
    REGISTRATION,
    RESTORATION,
)

from tests.unit.models import factory_business, factory_party_role

from legal_api.services.filings.validations.common_validations import (
    find_updated_keys_for_firms,
    is_officer_proprietor_replace_valid,
    validate_certify_name,
    validate_certified_by,
    validate_offices_addresses,
    validate_parties_addresses,
    validate_party_name,
    validate_party_role_firms,
    validate_staff_payment,
)


CORRECTION = copy.deepcopy(CORRECTION_INCORPORATION['filing']['correction'])
CHANGE_OF_RECEIVERS['type'] = 'appointReceiver'


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
    ('changeOfLiquidators', CHANGE_OF_LIQUIDATORS, 'liquidationRecordsOffice'),
    ('changeOfRegistration', CHANGE_OF_REGISTRATION, 'businessOffice'),
    ('continuationIn', CONTINUATION_IN, 'registeredOffice'),
    ('conversion', FIRMS_CONVERSION, 'businessOffice'),
    ('correction', CORRECTION, 'registeredOffice'),
    ('incorporationApplication', INCORPORATION, 'registeredOffice'),
    ('registration', REGISTRATION, 'businessOffice'),
    ('restoration', RESTORATION, 'registeredOffice')
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
    ('changeOfDirectors', CHANGE_OF_DIRECTORS, 'directors'),
    ('changeOfLiquidators', CHANGE_OF_LIQUIDATORS, 'relationships'),
    ('changeOfOfficers', CHANGE_OF_OFFICERS, 'relationships'),
    ('changeOfReceivers', CHANGE_OF_RECEIVERS, 'relationships'),
    ('changeOfRegistration', CHANGE_OF_REGISTRATION, 'parties'),
    ('continuationIn', CONTINUATION_IN, 'parties'),
    ('conversion', FIRMS_CONVERSION, 'parties'),
    ('correction', CORRECTION, 'parties'),
    ('dissolution', DISSOLUTION, 'parties'),
    ('incorporationApplication', INCORPORATION, 'parties'),
    ('registration', REGISTRATION, 'parties'),
    ('restoration', RESTORATION, 'parties')
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
# @patch('legal_api.services.filings.validations.common_validations.Party')
@patch('legal_api.services.filings.validations.common_validations.Address')
def test_find_updated_keys_for_firms(mock_address, mock_party_role):
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

@pytest.mark.parametrize('input_value, expected_error', [
    ('John   Doe', False),
    ('   \t   ', False),
    ('', False),
    ('  John Doe', True),
    ('John Doe   ', True),    
])
def test_validate_certified_by(input_value, expected_error):
    """Test that certified by field can be validated."""
    filing = copy.deepcopy(FILING_HEADER)
    filing['filing']['header']['certifiedBy'] = input_value

    errors = validate_certified_by(filing)

    if expected_error:
        assert errors
        assert errors[0]['error'] == 'Certified by field cannot start or end with whitespace.'
        assert errors[0]['path'] == '/filing/header/certifiedBy'
    else:
        assert errors == []

@pytest.mark.parametrize(
    ('party_type', 'organization_name','officer_override', 'expected_errors'),
    [
        (
            'person',
            ' ',
            {'firstName': 'First', 'lastName': 'Last'},
            'director organization name should not be set for person party type'
        ),
        (
            'person',
            '',
            {'firstName': 'First', 'lastName': 'Last'},
            None
        ),
        ('organization', None, {}, 'organization name is required'),
        ('organization', '  ', {}, 'organization name is required'),
        ('organization', ' Org Name', {}, 'director organization name cannot start or end with whitespace'),
        ('organization', 'Org Name', {'firstName':'First'}, 'director first name should not be set for organization party type'),
        ('organization', 'Org Name', {'firstName':' '}, 'director first name should not be set for organization party type'),
        ('organization', 'Org Name', {'middleInitial':'A'}, 'director middle initial should not be set for organization party type'),
        ('organization', 'Org Name', {'middleName':'Middle'}, 'director middle name should not be set for organization party type'),
        ('organization', 'Org Name', {'lastName':'Last'}, 'director last name should not be set for organization party type'),
        ('organization', 'Org Name', {}, None)
    ]
)
def test_validate_party_name(session, party_type, organization_name, officer_override, expected_errors):
    """Test that party name validation works as expected."""
    officer = {
        'partyType': party_type,
        'firstName': '',
        'middleInitial': '',
        'middleName': '',
        'lastName': '',
        'organizationName': organization_name
    }
    officer.update(officer_override)
    party = {
        'officer': officer,
        'roles': [{'roleType': 'director'}]
    }

    errors = validate_party_name(party, '/filing/incorporationApplication/parties/0' , 'BC')

    if expected_errors:
        assert errors
        assert expected_errors in [error['error'] for error in errors]
    else:
        assert errors == []

@pytest.mark.parametrize('test_name, filing_json, filing_type, results', [
    (
        'partner',
        {
            'filing': {
                'registration': {
                    'parties': [
                        {
                            'roles': [{'roleType': 'partner'}],
                            'officer': {
                                'firstName': 'First',
                                'lastName': 'Last',
                                'organizationName': ''
                            }
                        }
                    ]
                }
            }
        },
        'registration',
        False
    ),
    (
        'proprietor',
        {
            'filing': {
                'registration': {
                    'parties': [
                        {
                            'roles': [{'roleType': 'proprietor'}],
                            'officer': {
                                'firstName': 'First',
                                'lastName': 'Last',
                                'organizationName': ''
                            }
                        }
                    ]
                }
            }
        },
        'registration',
        False
    ),
    (
        'firm with org name',
        {
            'filing': {
                'registration': {
                    'parties': [
                        {
                            'roles': [{'roleType': 'partner'}],
                            'officer': {
                                'firstName': '',
                                'lastName': '',
                                'organizationName': 'Firm Name'
                            }
                        }
                    ]
                }
            }
        },
        'registration',
        False
    )
])

@patch('legal_api.services.filings.validations.common_validations.PermissionService')
def test_validate_party_role_firms(mock_permission_service, session, test_name, filing_json, filing_type, has_permission, results):
    """Test that party name validation works as expected for firms."""
    parties = filing_json['filing'][filing_type].get('parties', [])

    if has_permission:
        mock_permission_service.check_user_permission.return_value = None
    else:
        mock_permission_service.check_user_permission.return_value = Error(
            HTTPStatus.FORBIDDEN,
            [{"message": "Permission Denied: You do not have permission to add {role_type} to firm in registration filing."}]
        )
    error = validate_party_role_firms(parties, filing_type)
    if isinstance(results, int):
        if results > 0:
            assert error[0].get('path') == f'/filing/{filing_type}/parties'
        else:
            assert error == []
    assert error is results 


@pytest.mark.parametrize('test_name, legal_type, existing_identifier, filing_identifier, expected_result', [
    (
        'not sole proprietor',
        'GP',
        'BC1234567',
        'BC7654321',
        False # no validation needed
    ),
    (
        'no existing proprietor',
        'SP',
        None,
        'BC7654321',
        False # no existing proprietor to compare
    ),
    (
        'same proprietor',
        'SP',
        'BC1234567',
        'BC1234567',
        False # same proprietor, valid
    ),
    (
        'different proprietor',
        'SP',
        'BC1234567',
        'BC7654321',
        True # different proprietor, invalid
    )
])
def test_is_officer_proprietor_replace_valid(session, test_name, legal_type, existing_identifier, filing_identifier, expected_result):
    """Test that party name validation works as expected for firms."""
    business = factory_business(identifier='BC1234567', entity_type=legal_type)

    if existing_identifier:
        party = Party(
            party_type=Party.PartyTypes.ORGANIZATION.value,
            organization_name='Proprietor Name',
            identifier=existing_identifier,
            )
        party.save()
        party_role = PartyRole(
            role=PartyRole.RoleTypes.PROPRIETOR.value,
            appointment_date=datetime.now().date(),
            cessation_date=None,
            business_id=business.id,
            party_id=party.id )
        party_role.save()


        filing_json = copy.deepcopy(CHANGE_OF_REGISTRATION_TEMPLATE)

        filing_json['filing']['changeOfRegistration']['parties'][0]['roles'] = [{'roleType': 'proprietor'}]

        if filing_identifier is not None:
            filing_json['filing']['changeOfRegistration']['parties'][0]['officer']['identifier'] = filing_identifier
        else:
            filing_json['filing']['changeOfRegistration']['parties'][0]['officer'].pop(['identifier'], None)
        result = is_officer_proprietor_replace_valid(business, filing_json, 'changeOfRegistration')
        assert result is expected_result
