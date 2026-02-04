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
from legal_api.services import flags
from legal_api.services.permissions import PermissionService
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
    EXCLUDED_WORDS_FOR_CLASS,
    EXCLUDED_WORDS_FOR_SERIES,
    find_updated_keys_for_firms,
    is_officer_proprietor_replace_valid,
    validate_certify_name,
    validate_certified_by,
    validate_court_order,
    validate_email,
    validate_offices_addresses,
    validate_parties_addresses,
    validate_party_name,
    validate_party_role_firms,
    validate_series,
    validate_share_structure,
    validate_shares,
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

INVALID_ADDRESS_WHITESPACE = {
    'streetAddress': ' 123 Main St ',
    'streetAddressAdditional': ' Suite 200 ',
    'addressCity': 'Vancouver ',
    'addressRegion': ' BC',
    'postalCode': ' V6B 1A1 ',
    'addressCountry': ' CA'
}

VALID_ADDRESS_WHITESPACE = {
    'streetAddress': '123 Main St',
    'streetAddressAdditional': 'Suite 200  ',
    'addressCity': 'Vancouver',
    'addressRegion': 'BC',
    'postalCode': 'V6B 1A1',
    'addressCountry': 'CA'
}

WHITESPACE_VALIDATED_ADDRESS_FIELDS = (
    'streetAddress',
    'addressCity',
    'addressCountry',
    'postalCode',
)


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
def test_validate_offices_addresses(session, filing_type, filing_data, office_type):
    """Test office addresses can be validated."""
    filing = copy.deepcopy(FILING_HEADER)
    filing['filing'][filing_type] = copy.deepcopy(filing_data)

    err1 = validate_offices_addresses(filing, filing_type)
    assert err1 == []

    # --- Postal code validation ---
    filing['filing'][filing_type]['offices'][office_type]['deliveryAddress'] = INVALID_ADDRESS_NO_POSTAL_CODE
    err2 = validate_offices_addresses(filing, filing_type)
    assert err2
    assert err2[0]['error'] == 'Postal code is required.'

    filing['filing'][filing_type]['offices'][office_type]['deliveryAddress'] = VALID_ADDRESS_NO_POSTAL_CODE
    err3 = validate_offices_addresses(filing, filing_type)
    assert err3 == []

    # --- Whitespace validation ---
    filing['filing'][filing_type]['offices'][office_type]['deliveryAddress'] = VALID_ADDRESS_WHITESPACE
    err3 = validate_offices_addresses(filing, filing_type)
    assert err3 == []

    filing['filing'][filing_type]['offices'][office_type]['deliveryAddress'] = INVALID_ADDRESS_WHITESPACE
    err4 = validate_offices_addresses(filing, filing_type)
    assert err4
    error_fields = {e['path'].split('/')[-1] for e in err4}
    assert error_fields == set(WHITESPACE_VALIDATED_ADDRESS_FIELDS)

    

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
def test_validate_parties_addresses(session, filing_type, filing_data, party_key):
    """Test party addresses can be validated."""
    filing = copy.deepcopy(FILING_HEADER)
    filing['filing'][filing_type] = copy.deepcopy(filing_data)

    err1 = validate_parties_addresses(filing, filing_type, party_key)
    assert err1 == []

    # --- Postal code validation ---
    filing['filing'][filing_type][party_key][0]['deliveryAddress'] = INVALID_ADDRESS_NO_POSTAL_CODE
    err2 = validate_parties_addresses(filing, filing_type, party_key)
    assert err2
    assert err2[0]['error'] == 'Postal code is required.'

    filing['filing'][filing_type][party_key][0]['deliveryAddress'] = VALID_ADDRESS_NO_POSTAL_CODE
    err3 = validate_parties_addresses(filing, filing_type, party_key)
    assert err3 == []

    # --- Whitespace validation ---
    filing['filing'][filing_type][party_key][0]['deliveryAddress'] = VALID_ADDRESS_WHITESPACE
    err3 = validate_parties_addresses(filing, filing_type, party_key)
    assert err3 == []

    filing['filing'][filing_type][party_key][0]['deliveryAddress'] = INVALID_ADDRESS_WHITESPACE
    err4 = validate_parties_addresses(filing, filing_type, party_key)
    assert err4
    error_fields = {e['path'].split('/')[-1] for e in err4}
    assert error_fields == set(WHITESPACE_VALIDATED_ADDRESS_FIELDS)

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

@pytest.mark.parametrize('test_name, filing_json, filing_type, business_in_lear, business_in_colin, has_permission, results', [
    (
        'organization with identifier in lear',
        {
            'filing': {
                'registration': {
                    'parties': [
                        {
                            'roles': [{'roleType': 'partner'}],
                            'officer': {
                                'partyType': 'organization',
                                'identifier': 'BC1234567',
                                'organizationName': 'Org Name'
                            }
                        }
                    ]
                }
            }
        },
        'registration',
        True,
        False,
        False,
        []
    ),
    (
        'organization with identifier in colin',
        {
            'filing': {
                'registration': {
                    'parties': [
                        {
                            'roles': [{'roleType': 'partner'}],
                            'officer': {
                                'partyType': 'organization',
                                'identifier': 'BC1234567',
                                'organizationName': 'Org Name'
                            }
                        }
                    ]
                }
            }
        },
        'registration',
        False,
        True,
        False,
        []
    ),
    (
        'organization with identifier not found, no permission',
        {
            'filing': {
                'registration': {
                    'parties': [
                        {
                            'roles': [{'roleType': 'partner'}],
                            'officer': {
                                'partyType': 'organization',
                                'identifier': 'BC1234567',
                                'organizationName': 'Org Name'
                            }
                        }
                    ]
                }
            }
        },
        'registration',
        False,
        False,
        False,
        [{'error': 'Permission Denied: You do not have permission to add a business or corporation which is not registered in BC.', 'path': '/filing/registration/parties'}]
    ),
    (
        'organization with identifier not found, has permission',
        {
            'filing': {
                'registration': {
                    'parties': [
                        {
                            'roles': [{'roleType': 'partner'}],
                            'officer': {
                                'partyType': 'organization',
                                'identifier': 'BC1234567',
                                'organizationName': 'Org Name'
                            }
                        }
                    ]
                }
            }
        },
        'registration',
        False,
        False,
        True,
        []
    ),
    (
        'organization without identifier, no permission',
        {
            'filing': {
                'registration': {
                    'parties': [
                        {
                            'roles': [{'roleType': 'partner'}],
                            'officer': {
                                'partyType': 'organization',
                                'identifier': 'BC1234567',
                                'organizationName': 'Org Name'
                            }
                        }
                    ]
                }
            }
        },
        'registration',
        False,
        False,
        False,
        [{'error': 'Permission Denied: You do not have permission to add a business or corporation which is not registered in BC.', 'path': '/filing/registration/parties'}]
    ),
    (
        'person party type',
        {
            'filing': {
                'registration': {
                    'parties': [
                        {
                            'roles': [{'roleType': 'partner'}],
                            'officer': {
                                'partyType': 'person',
                                'firstName': 'First',
                                'lastName': 'Last'
                            }
                        }
                    ]
                }
            }
        },
        'registration',
        False,
        False,
        False,
        []
    ),
])

@patch('legal_api.services.filings.validations.common_validations.colin')
@patch('legal_api.services.filings.validations.common_validations.Business')
@patch('legal_api.services.filings.validations.common_validations.PermissionService')
def test_validate_party_role_firms(mock_permission_service, mock_business, mock_colin, session, test_name, filing_json, filing_type, business_in_lear, business_in_colin, has_permission, results):
    """Test that party name validation works as expected for firms."""
    parties = filing_json['filing'][filing_type].get('parties', [])

    if business_in_lear:
        mock_business.find_by_identifier.return_value = type('Business', (), {})()
    else:
        mock_business.find_by_identifier.return_value = None
    
    mock_response = type('Response', (), {'status_code': HTTPStatus.OK if business_in_colin else HTTPStatus.NOT_FOUND})()
    mock_colin.query_business.return_value = mock_response

    if has_permission:
        mock_permission_service.check_user_permission.return_value = None
    else:
        mock_permission_service.check_user_permission.return_value = Error(
            HTTPStatus.FORBIDDEN,
            [{"message": "Permission Denied: You do not have permission to add a business or corporation which is not registered in BC."}]
        )
    error = validate_party_role_firms(parties, filing_type)
    
    assert len(error) == len(results)
    if results:
        assert error[0].get('path') == f'/filing/{filing_type}/parties'
        assert 'Permission Denied' in error[0].get('error', '')


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

@pytest.mark.parametrize('email, is_valid', [
    # Valid email formats
    ('test@example.com', True),
    ('user.name@domain.com', True),
    ('user+tag@example.com', True),
    ('test@subdomain.example.com', True),
    ('test@example.co.uk', True),
    ('user@[192.168.1.1]', True),
    ('no_one@never.get', True),
    ('"quoted"@example.com', True),
    ('user_name@domain.org', True),
    ('test123@test123.com', True),
    ('john.o\'smith@gov.bc.ca', True),
    # Invalid email formats
    ('no_one@never.', False),
    ('invalid', False),
    ('@invalid.com', False),
    ('test@.com', False),
    ('test@', False),
    ('test@domain', False),
    ('test @example.com', False),
    ('test@ example.com', False),
    ('test@@example.com', False),
])
def test_validate_email_format(session, email, is_valid):
    """Test email format validation against various email patterns."""
    filing_json = {
        'filing': {
            'incorporationApplication': {
                'contactPoint': {
                    'email': email
                }
            }
        }
    }

    result = validate_email(filing_json, 'incorporationApplication')

    if is_valid:
        assert result == []
    else:
        assert len(result) == 1
        assert 'Invalid email address format' in result[0]['error']
        assert result[0]['path'] == '/filing/incorporationApplication/contactPoint/email'

@pytest.mark.parametrize('email', [
    # Valid email formats
    (' test@example.com'),
    ('test@example.com '),
    (' test@@example.com'),
    ('test@@example.com '),
])
def test_validate_email_whitespace(session, email):
    """Test whitespace handling in email validation."""
    filing_json = {
        'filing': {
            'incorporationApplication': {
                'contactPoint': {
                    'email': email
                }
            }
        }
    }

    result = validate_email(filing_json, 'incorporationApplication')

    assert len(result) == 1
    assert 'Email cannot start or end with whitespace' in result[0]['error']
    assert result[0]['path'] == '/filing/incorporationApplication/contactPoint/email'        


def test_validate_email_missing_contact_point(session):
    """Test that missing contactPoint does not cause an error."""
    filing_json = {
        'filing': {
            'incorporationApplication': {}
        }
    }

    result = validate_email(filing_json, 'incorporationApplication')
    assert result == []


def test_validate_email_missing_email_field(session):
    """Test that missing email field does not cause an error."""
    filing_json = {
        'filing': {
            'incorporationApplication': {
                'contactPoint': {
                    'phone': '(123) 456-7890'
                }
            }
        }
    }

    result = validate_email(filing_json, 'incorporationApplication')
    assert result == []


@pytest.mark.parametrize('has_permission, expected_error_msg', [
    (True, None),
    (False, 'Permission Denied'),
])
def test_validate_court_order_with_flag_on(session, has_permission, expected_error_msg):
    """
    Test court order validation with flag ON
    """
    court_order = {
        'fileNumber': 'Valid file number',
        'orderDate': '2021-01-30T09:56:01+01:00',
        'effectOfOrder': 'planOfArrangement'
    }

    permission_error = Error(
        HTTPStatus.FORBIDDEN,
        [{'message': 'Permission Denied - You do not have permissions add court order details in this filing.'}]
    ) if not has_permission else None

    with (
        patch.object(flags, 'is_on', return_value=True),
        patch.object(PermissionService, 'check_user_permission', return_value=permission_error)
    ):
        result = validate_court_order('/filing/alteration/courtOrder', court_order)

    if has_permission:
        assert result is None
    else:
        assert isinstance(result, list)
        assert len(result) == 1
        assert expected_error_msg in result[0]['error']
        assert result[0]['path'] == '/filing/alteration/courtOrder'

@pytest.mark.parametrize('share_class_name, expected_valid', [
    # Valid names - end with " Shares"
    ('Class A Shares', True),
    ('Common Shares', True),
    ('Preferred Shares', True),
    ('Class B Non-Voting Shares', True),
    ('Series 1 Preferred Shares', True),
    ('Voting Shares', True),
    ('Non-Voting Shares', True),
    # Invalid names - don't end with " Shares"
    ('Class A', False),
    ('Common', False),
    ('Preferred Stock', False),
    ('SharesClass', False),
    ('', False),  # empty name handled separately
])
def test_share_class_name_must_end_with_shares(session, share_class_name, expected_valid):
    """Test that share class names must end with ' Shares'."""
    share_class = {
        'name': share_class_name,
        'hasMaximumShares': False,
        'hasParValue': False,
        'hasRightsOrRestrictions': False,
        'series': []
    }
    memoize_names = []

    result = validate_shares(share_class, memoize_names, 'incorporationApplication', 0, 'BEN')

    suffix_errors = [e for e in result if "must end with ' Shares'" in e.get('error', '')]

    if expected_valid:
        assert len(suffix_errors) == 0
    else:
        if share_class_name.strip():  # only check suffix error if name is not empty
            assert len(suffix_errors) == 1
            assert f"Share class name '{share_class_name}' must end with ' Shares'." in suffix_errors[0]['error']


@pytest.mark.parametrize('share_class_name, expected_valid', [
    # Valid names - no reserved words before " Shares" suffix
    ('Class A Shares', True),
    ('Common Shares', True),
    ('Preferred Shares', True),
    ('Class B Non-Voting Shares', True),
    ('Voting Shares', True),
    # Invalid names - contain reserved word "share" (case insensitive)
    ('Share Class A Shares', False),
    ('My Share Shares', False),
    ('SHARE Type Shares', False),
    # Invalid names - contain reserved word "shares" (case insensitive)
    ('Shares Class Shares', False),
    ('Multiple Shares Type Shares', False),
    # Invalid names - contain reserved word "value" (case insensitive)
    ('Value Class Shares', False),
    ('Par Value Shares', False),
    ('VALUE Type Shares', False),
    ('No Par Value Shares', False),
])
def test_share_class_name_reserved_words(session, share_class_name, expected_valid):
    """Test that share class names cannot contain reserved words."""
    share_class = {
        'name': share_class_name,
        'hasMaximumShares': False,
        'hasParValue': False,
        'hasRightsOrRestrictions': False,
        'series': []
    }
    memoize_names = []

    result = validate_shares(share_class, memoize_names, 'incorporationApplication', 0, 'BEN')

    reserved_word_errors = [e for e in result if "cannot contain the words" in e.get('error', '')]

    if expected_valid:
        assert len(reserved_word_errors) == 0
    else:
        assert len(reserved_word_errors) == 1
        assert "Share class name cannot contain the words 'share', 'shares', or 'value'." in reserved_word_errors[0]['error']


@pytest.mark.parametrize('share_class_name', [
    '',
    '   ',
    '\t',
    '\n',
])
def test_share_class_name_empty(session, share_class_name):
    """Test that empty share class names are rejected."""
    share_class = {
        'name': share_class_name,
        'hasMaximumShares': False,
        'hasParValue': False,
        'hasRightsOrRestrictions': False,
        'series': []
    }
    memoize_names = []

    result = validate_shares(share_class, memoize_names, 'incorporationApplication', 0, 'BEN')

    assert len(result) >= 1
    assert any('Share class name is required' in e.get('error', '') for e in result)


@pytest.mark.parametrize('share_class_name', [
    ' Class A Shares',
    'Class A Shares ',
    ' Class A Shares ',
    '\tClass A Shares',
    'Class A Shares\n',
])
def test_share_class_name_whitespace(session, share_class_name):
    """Test that share class names with leading/trailing whitespace are rejected."""
    share_class = {
        'name': share_class_name,
        'hasMaximumShares': False,
        'hasParValue': False,
        'hasRightsOrRestrictions': False,
        'series': []
    }
    memoize_names = []

    result = validate_shares(share_class, memoize_names, 'incorporationApplication', 0, 'BEN')

    assert len(result) >= 1
    assert any('cannot start or end with whitespace' in e.get('error', '') for e in result)


def test_share_class_name_duplicate(session):
    """Test that duplicate share class names are rejected."""
    share_class = {
        'name': 'Class A Shares',
        'hasMaximumShares': False,
        'hasParValue': False,
        'hasRightsOrRestrictions': False,
        'series': []
    }
    memoize_names = ['Class A Shares']  # Already used

    result = validate_shares(share_class, memoize_names, 'incorporationApplication', 0, 'BEN')

    assert len(result) >= 1
    assert any('already used in a share class or series' in e.get('error', '') for e in result)


@pytest.mark.parametrize('reserved_word', EXCLUDED_WORDS_FOR_CLASS)
def test_share_class_name_each_reserved_word(session, reserved_word):
    """Test that each reserved word is properly rejected in share class names."""
    share_class_name = f'{reserved_word.capitalize()} Type Shares'
    share_class = {
        'name': share_class_name,
        'hasMaximumShares': False,
        'hasParValue': False,
        'hasRightsOrRestrictions': False,
        'series': []
    }
    memoize_names = []

    result = validate_shares(share_class, memoize_names, 'incorporationApplication', 0, 'BEN')

    reserved_word_errors = [e for e in result if "cannot contain the words" in e.get('error', '')]
    assert len(reserved_word_errors) == 1


@pytest.mark.parametrize('share_class_name', [
    'SHARE Type Shares',
    'share Type Shares',
    'Share Type Shares',
    'ShArE Type Shares',
    'VALUE Class Shares',
    'value Class Shares',
    'Value Class Shares',
])
def test_share_class_name_reserved_word_case_insensitive(session, share_class_name):
    """Test that reserved word checking is case insensitive."""
    share_class = {
        'name': share_class_name,
        'hasMaximumShares': False,
        'hasParValue': False,
        'hasRightsOrRestrictions': False,
        'series': []
    }
    memoize_names = []

    result = validate_shares(share_class, memoize_names, 'incorporationApplication', 0, 'BEN')

    reserved_word_errors = [e for e in result if "cannot contain the words" in e.get('error', '')]
    assert len(reserved_word_errors) == 1, f"Failed for: {share_class_name}"


@pytest.mark.parametrize('series_name, expected_valid', [
    # Valid names - end with " Shares" and no reserved words
    ('Series A Shares', True),
    ('Series 1 Shares', True),
    ('Preferred Shares', True),
    ('Class A Series 1 Shares', True),
    ('Convertible Shares', True),
    ('Non-Voting Shares', True),
    # Invalid names - don't end with " Shares"
    ('Series A', False),
    ('Series 1', False),
    ('Preferred', False),
])
def test_series_name_must_end_with_shares(session, series_name, expected_valid):
    """Test that series names must end with ' Shares'."""
    share_class = {
        'name': 'Class A Shares',
        'hasMaximumShares': False,
        'hasParValue': False,
        'hasRightsOrRestrictions': True,
        'series': [{
            'name': series_name,
            'hasMaximumShares': False
        }]
    }
    memoize_names = ['Class A Shares']

    result = validate_series(share_class, memoize_names, 'incorporationApplication', 0)

    suffix_errors = [e for e in result if "must end with ' Shares'" in e.get('error', '')]

    if expected_valid:
        assert len(suffix_errors) == 0
    else:
        assert len(suffix_errors) == 1
        assert f"Share series name '{series_name}' must end with ' Shares'." in suffix_errors[0]['error']


@pytest.mark.parametrize('series_name, expected_valid', [
    # Valid names - no reserved words (with " Shares" suffix)
    ('Series A Shares', True),
    ('Series 1 Shares', True),
    ('Preferred Shares', True),
    ('Class A Series 1 Shares', True),
    ('Convertible Shares', True),
    ('Non-Voting Shares', True),
    # Invalid names - contain reserved word "share" (with " Shares" suffix)
    ('Share Series A Shares', False),
    ('Series Share 1 Shares', False),
    ('My Share Shares', False),
    # Invalid names - contain reserved word "shares" (with " Shares" suffix)
    ('Shares Series Shares', False),
    ('Series Shares Type Shares', False),
    ('Multiple Shares Shares', False),
])
def test_series_name_reserved_words(session, series_name, expected_valid):
    """Test that series names cannot contain reserved words."""
    share_class = {
        'name': 'Class A Shares',
        'hasMaximumShares': False,
        'hasParValue': False,
        'hasRightsOrRestrictions': True,
        'series': [{
            'name': series_name,
            'hasMaximumShares': False
        }]
    }
    memoize_names = ['Class A Shares']

    result = validate_series(share_class, memoize_names, 'incorporationApplication', 0)

    reserved_word_errors = [e for e in result if "cannot contain the words 'share' or 'shares'" in e.get('error', '')]

    if expected_valid:
        assert len(reserved_word_errors) == 0
    else:
        assert len(reserved_word_errors) == 1


@pytest.mark.parametrize('series_name', [
    '',
    '   ',
    '\t',
    '\n',
])
def test_series_name_empty(session, series_name):
    """Test that empty series names are rejected."""
    share_class = {
        'name': 'Class A Shares',
        'hasMaximumShares': False,
        'hasParValue': False,
        'hasRightsOrRestrictions': True,
        'series': [{
            'name': series_name,
            'hasMaximumShares': False
        }]
    }
    memoize_names = ['Class A Shares']

    result = validate_series(share_class, memoize_names, 'incorporationApplication', 0)

    assert len(result) >= 1
    assert any('Share series name is required' in e.get('error', '') for e in result)


@pytest.mark.parametrize('series_name', [
    ' Series A',
    'Series A ',
    ' Series A ',
    '\tSeries A',
    'Series A\n',
])
def test_series_name_whitespace(session, series_name):
    """Test that series names with leading/trailing whitespace are rejected."""
    share_class = {
        'name': 'Class A Shares',
        'hasMaximumShares': False,
        'hasParValue': False,
        'hasRightsOrRestrictions': True,
        'series': [{
            'name': series_name,
            'hasMaximumShares': False
        }]
    }
    memoize_names = ['Class A Shares']

    result = validate_series(share_class, memoize_names, 'incorporationApplication', 0)

    assert len(result) >= 1
    assert any('cannot start or end with whitespace' in e.get('error', '') for e in result)


def test_series_name_duplicate(session):
    """Test that duplicate series names are rejected."""
    share_class = {
        'name': 'Class A Shares',
        'hasMaximumShares': False,
        'hasParValue': False,
        'hasRightsOrRestrictions': True,
        'series': [{
            'name': 'Series A Shares',
            'hasMaximumShares': False
        }]
    }
    memoize_names = ['Class A Shares', 'Series A Shares']  # Series A Shares already used

    result = validate_series(share_class, memoize_names, 'incorporationApplication', 0)

    assert len(result) >= 1
    assert any('already used in a share class or series' in e.get('error', '') for e in result)


@pytest.mark.parametrize('reserved_word', EXCLUDED_WORDS_FOR_SERIES)
def test_series_name_each_reserved_word(session, reserved_word):
    """Test that each reserved word is properly rejected in series names."""
    series_name = f'{reserved_word.capitalize()} Series Shares'
    share_class = {
        'name': 'Class A Shares',
        'hasMaximumShares': False,
        'hasParValue': False,
        'hasRightsOrRestrictions': True,
        'series': [{
            'name': series_name,
            'hasMaximumShares': False
        }]
    }
    memoize_names = ['Class A Shares']

    result = validate_series(share_class, memoize_names, 'incorporationApplication', 0)

    reserved_word_errors = [e for e in result if "cannot contain the words 'share' or 'shares'" in e.get('error', '')]
    assert len(reserved_word_errors) == 1


@pytest.mark.parametrize('series_name', [
    'SHARE Series Shares',
    'share Series Shares',
    'Share Series Shares',
    'ShArE Series Shares',
    'SHARES Series Shares',
    'shares Series Shares',
    'Shares Series Shares',
])
def test_series_name_reserved_word_case_insensitive(session, series_name):
    """Test that reserved word checking is case insensitive for series names."""
    share_class = {
        'name': 'Class A Shares',
        'hasMaximumShares': False,
        'hasParValue': False,
        'hasRightsOrRestrictions': True,
        'series': [{
            'name': series_name,
            'hasMaximumShares': False
        }]
    }
    memoize_names = ['Class A Shares']

    result = validate_series(share_class, memoize_names, 'incorporationApplication', 0)

    reserved_word_errors = [e for e in result if "cannot contain the words 'share' or 'shares'" in e.get('error', '')]
    assert len(reserved_word_errors) == 1, f"Failed for: {series_name}"


def test_series_allows_value_word(session):
    """Test that series names CAN contain 'value' (only restricted for classes)."""
    share_class = {
        'name': 'Class A Shares',
        'hasMaximumShares': False,
        'hasParValue': False,
        'hasRightsOrRestrictions': True,
        'series': [{
            'name': 'Value Series Shares',
            'hasMaximumShares': False
        }]
    }
    memoize_names = ['Class A Shares']

    result = validate_series(share_class, memoize_names, 'incorporationApplication', 0)

    reserved_word_errors = [e for e in result if "cannot contain" in e.get('error', '')]
    assert len(reserved_word_errors) == 0


def test_valid_share_structure(session):
    """Test a completely valid share structure."""
    filing_json = {
        'filing': {
            'incorporationApplication': {
                'shareStructure': {
                    'shareClasses': [{
                        'name': 'Class A Shares',
                        'hasMaximumShares': True,
                        'maxNumberOfShares': 10000,
                        'hasParValue': False,
                        'hasRightsOrRestrictions': True,
                        'series': [{
                            'name': 'Series 1 Shares',
                            'hasMaximumShares': True,
                            'maxNumberOfShares': 5000
                        }]
                    }, {
                        'name': 'Class B Shares',
                        'hasMaximumShares': False,
                        'hasParValue': True,
                        'parValue': 1.00,
                        'currency': 'CAD',
                        'hasRightsOrRestrictions': False,
                        'series': []
                    }]
                }
            }
        }
    }

    result = validate_share_structure(filing_json, 'incorporationApplication', 'BEN')

    assert result is None


def test_share_structure_with_invalid_class_name_no_shares_suffix(session):
    """Test share structure with class name missing ' Shares' suffix."""
    filing_json = {
        'filing': {
            'incorporationApplication': {
                'shareStructure': {
                    'shareClasses': [{
                        'name': 'Class A',
                        'hasMaximumShares': False,
                        'hasParValue': False,
                        'hasRightsOrRestrictions': False,
                        'series': []
                    }]
                }
            }
        }
    }

    result = validate_share_structure(filing_json, 'incorporationApplication', 'BEN')

    assert result is not None
    assert any("must end with ' Shares'" in e.get('error', '') for e in result)


def test_share_structure_with_reserved_word_in_class_name(session):
    """Test share structure with reserved word in class name."""
    filing_json = {
        'filing': {
            'incorporationApplication': {
                'shareStructure': {
                    'shareClasses': [{
                        'name': 'Share Class Shares',
                        'hasMaximumShares': False,
                        'hasParValue': False,
                        'hasRightsOrRestrictions': False,
                        'series': []
                    }]
                }
            }
        }
    }

    result = validate_share_structure(filing_json, 'incorporationApplication', 'BEN')

    assert result is not None
    assert any("cannot contain the words 'share', 'shares', or 'value'" in e.get('error', '') for e in result)


def test_share_structure_with_reserved_word_in_series_name(session):
    """Test share structure with reserved word in series name."""
    filing_json = {
        'filing': {
            'incorporationApplication': {
                'shareStructure': {
                    'shareClasses': [{
                        'name': 'Class A Shares',
                        'hasMaximumShares': False,
                        'hasParValue': False,
                        'hasRightsOrRestrictions': True,
                        'series': [{
                            'name': 'Share Series 1 Shares',
                            'hasMaximumShares': False
                        }]
                    }]
                }
            }
        }
    }

    result = validate_share_structure(filing_json, 'incorporationApplication', 'BEN')

    assert result is not None
    assert any("cannot contain the words 'share' or 'shares'" in e.get('error', '') for e in result)


def test_share_structure_multiple_errors(session):
    """Test share structure validation catches multiple errors."""
    filing_json = {
        'filing': {
            'incorporationApplication': {
                'shareStructure': {
                    'shareClasses': [{
                        'name': 'Value Class',  # Missing " Shares" and contains "value"
                        'hasMaximumShares': False,
                        'hasParValue': False,
                        'hasRightsOrRestrictions': True,
                        'series': [{
                            'name': 'Shares Series Shares',  # Contains "shares"
                            'hasMaximumShares': False
                        }]
                    }]
                }
            }
        }
    }

    result = validate_share_structure(filing_json, 'incorporationApplication', 'BEN')

    assert result is not None
    assert len(result) >= 2  # At least errors for class name and series name


def test_share_structure_duplicate_names_between_class_and_series(session):
    """Test that a series cannot have the same name as a class."""
    filing_json = {
        'filing': {
            'incorporationApplication': {
                'shareStructure': {
                    'shareClasses': [{
                        'name': 'Class A Shares',
                        'hasMaximumShares': False,
                        'hasParValue': False,
                        'hasRightsOrRestrictions': True,
                        'series': [{
                            'name': 'Class A Shares',  # Same as class name
                            'hasMaximumShares': False
                        }]
                    }]
                }
            }
        }
    }

    result = validate_share_structure(filing_json, 'incorporationApplication', 'BEN')

    assert result is not None
    assert any('already used' in e.get('error', '') for e in result)


def test_share_structure_empty_share_classes_for_ia(session):
    """Test that incorporation application requires at least one share class."""
    filing_json = {
        'filing': {
            'incorporationApplication': {
                'shareStructure': {
                    'shareClasses': []
                }
            }
        }
    }

    result = validate_share_structure(filing_json, 'incorporationApplication', 'BEN')

    assert result is not None
    assert len(result) == 1
    assert result[0]['error'] == 'A company must have least one Class of Shares.'
    assert result[0]['path'] == '/filing/incorporationApplication/shareStructure/shareClasses'


def test_share_structure_empty_share_classes_allowed_for_non_ia(session):
    """Test that empty share classes are allowed for non-IA filings (e.g., alteration)."""
    filing_json = {
        'filing': {
            'alteration': {
                'shareStructure': {
                    'shareClasses': []
                }
            }
        }
    }

    result = validate_share_structure(filing_json, 'alteration', 'BEN')

    assert result is None

@pytest.mark.parametrize("max_shares,expected_error", [
    (None, "must provide value for maximum number of shares"),
    ("1000", "Must be a whole number"),
    (10.5, "Must be a whole number"),
    (True, "Must be a whole number"),
    (0, "Number must be greater than 0"),
    (-5, "Number must be greater than 0"),
    (10**16, "Number must be less than 16 digits"),
])
def test_share_class_max_number_of_shares_validation(session, max_shares, expected_error):
    share_class = {
        'name': 'Class A Shares',
        'hasMaximumShares': True,
        'maxNumberOfShares': max_shares,
        'hasParValue': False,
        'hasRightsOrRestrictions': False,
        'series': []
    }
    memoize_names = []
    result = validate_shares(share_class, memoize_names, 'incorporationApplication', 0, 'BEN')
    assert any(expected_error in e.get('error', '') for e in result)

@pytest.mark.parametrize("max_shares,expected_error", [
    (None, "must provide value for maximum number of shares"),
    ("1000", "Must be a whole number"),
    (10.5, "Must be a whole number"),
    (True, "Must be a whole number"),
    (0, "Number must be greater than 0"),
    (-5, "Number must be greater than 0"),
    (10**16, "Number must be less than 16 digits"),
])
def test_share_series_max_number_of_shares_validation(session, max_shares, expected_error):
    share_class = {
        'name': 'Class A Shares',
        'hasMaximumShares': True,
        'maxNumberOfShares': 10000,
        'hasParValue': False,
        'hasRightsOrRestrictions': True,
        'series': [{
            'name': 'Series 1 Shares',
            'hasMaximumShares': True,
            'maxNumberOfShares': max_shares
        }]
    }
    memoize_names = ['Class A Shares']
    result = validate_series(share_class, memoize_names, 'incorporationApplication', 0)
    assert any(expected_error in e.get('error', '') for e in result)

