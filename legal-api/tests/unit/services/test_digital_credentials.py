# Copyright © 2025 Province of British Columbia
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Tests for the Digital Credentials service.

Test suite to ensure that the Digital Credentials service is working as expected.
"""
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from legal_api.models import DCDefinition, DCBusinessUser, Party, PartyRole
from legal_api.services import digital_credentials
from legal_api.services.digital_credentials import DigitalCredentialsService
from legal_api.services.digital_credentials_helpers import get_digital_credential_data
from legal_api.services.digital_credentials_rules import DigitalCredentialsRulesService
from tests.unit.models import factory_business, factory_completed_filing, factory_user
from tests.unit.services.utils import create_party_role, create_test_user


schema_id = 'test_schema_id'
cred_def_id = 'test_credential_definition_id'


def test_init_app(app, session):
    """Assert that the init app register schema and credential definition."""
    DigitalCredentialsService._fetch_schema = MagicMock(return_value=schema_id)
    DigitalCredentialsService._fetch_credential_definition = MagicMock(
        return_value=cred_def_id)

    digital_credentials.init_app(app)
    definition = DCDefinition.find_by_credential_type(
        DCDefinition.CredentialType.business)
    assert definition.schema_id == schema_id
    assert definition.schema_name == digital_credentials.business_schema_name
    assert definition.schema_version == digital_credentials.business_schema_version
    assert definition.credential_definition_id == cred_def_id
    assert not definition.is_deleted


@pytest.mark.parametrize('test_data, expected', [
    # In this first test the user has a party role
    ({
        'business': {
            'identifier': 'FM1234567',
            'entity_type': 'BEN',
            'founding_date': '2010-01-01',
            'state': 'ACTIVE',
        },
        'business_extra': {
            'legal_name': 'Test Business',
            'tax_id': '000000000000001',
        },
        'parties': [{
            'first_name': 'First',
            'middle_initial': 'Middle',
            'last_name': 'Last',
            'role': 'director'
        }],
        'user': {
            'username': 'test',
            'lastname': 'Last',
            'firstname': 'First',
        },
        'user_extra': {
            'middlename': 'Middle',
        }
    }, [
        {'name': 'credential_id', 'value': ''},
        {'name': 'identifier', 'value': 'FM1234567'},
        {'name': 'business_name', 'value': 'Test Business'},
        {'name': 'business_type', 'value': 'BC Benefit Company'},
        {'name': 'cra_business_number', 'value': '000000000000001'},
        {'name': 'registered_on_dateint', 'value': '20100101'},
        {'name': 'company_status', 'value': 'ACTIVE'},
        {'name': 'family_name', 'value': 'LAST'},
        {'name': 'given_names', 'value': 'FIRST MIDDLE'},
        {'name': 'role', 'value': 'Director'}
    ]),
    ({
        'business': {
            'identifier': 'FM1234567',
            'entity_type': 'SP',
            'founding_date': '2010-01-01',
            'state': 'ACTIVE',
        },
        'business_extra': {
            'legal_name': 'Test Business',
            'tax_id': '000000000000001',
        },
        'parties': [{
            'first_name': 'First',
            'middle_initial': 'Middle',
            'last_name': 'Last',
            'role': 'proprietor'
        }],
        'user': {
            'username': 'test',
            'lastname': 'Last',
            'firstname': 'First',
        },
        'user_extra': {
            'middlename': 'Middle',
        }
    }, [
        {'name': 'credential_id', 'value': ''},
        {'name': 'identifier', 'value': 'FM1234567'},
        {'name': 'business_name', 'value': 'Test Business'},
        {'name': 'business_type', 'value': 'BC Sole Proprietorship'},
        {'name': 'cra_business_number', 'value': '000000000000001'},
        {'name': 'registered_on_dateint', 'value': '20100101'},
        {'name': 'company_status', 'value': 'ACTIVE'},
        {'name': 'family_name', 'value': 'LAST'},
        {'name': 'given_names', 'value': 'FIRST MIDDLE'},
        {'name': 'role', 'value': 'Proprietor'}
    ]),
    # In this second test the user does not have a party role
    ({
        'business': {
            'identifier': 'FM1234567',
            'entity_type': 'BEN',
            'founding_date': '2010-01-01',
            'state': 'ACTIVE',
        },
        'business_extra': {
            'legal_name': 'Test Business',
            'tax_id': '000000000000001',
        },
        'parties': [{
            'first_name': 'First 2',
            'last_name': 'Last 2',
            'role': 'director'
        }],
        'user': {
            'username': 'test',
            'lastname': 'Last',
            'firstname': 'First',
        },
        'user_extra': {
            'middlename': 'Middle',
        }
    }, [
        {'name': 'credential_id', 'value': ''},
        {'name': 'identifier', 'value': 'FM1234567'},
        {'name': 'business_name', 'value': 'Test Business'},
        {'name': 'business_type', 'value': 'BC Benefit Company'},
        {'name': 'cra_business_number', 'value': '000000000000001'},
        {'name': 'registered_on_dateint', 'value': '20100101'},
        {'name': 'company_status', 'value': 'ACTIVE'},
        {'name': 'family_name', 'value': 'LAST'},
        {'name': 'given_names', 'value': 'FIRST MIDDLE'},
        {'name': 'role', 'value': ''}
    ]),
    ({
        'business': {
            'identifier': 'FM1234567',
            'entity_type': 'SP',
            'state': 'HISTORICAL',
        },
        'business_extra': {
            'legal_name': '',
            'tax_id': '',
        },
        'parties': [{
            'first_name': 'First 2',
            'last_name': 'Last 2',
            'role': 'proprietor'
        }],
        'user': {
            'username': 'test',
            'lastname': 'Last',
            'firstname': 'First',
        },
        'user_extra': {
            'middlename': '',
        }
    }, [
        {'name': 'credential_id', 'value': ''},
        {'name': 'identifier', 'value': 'FM1234567'},
        {'name': 'business_name', 'value': ''},
        {'name': 'business_type', 'value': 'BC Sole Proprietorship'},
        {'name': 'cra_business_number', 'value': ''},
        {'name': 'registered_on_dateint', 'value': '19700101'},
        {'name': 'company_status', 'value': 'HISTORICAL'},
        {'name': 'family_name', 'value': 'LAST'},
        {'name': 'given_names', 'value': 'FIRST'},
        {'name': 'role', 'value': ''}
    ])
])
def test_data_helper_user_is_not_completing_party(app, session, test_data, expected):
    """Assert that the data helper returns the correct data when the user is not a completing party."""
    # Arrange
    credential_type = DCDefinition.CredentialType.business

    user = factory_user(**test_data['user'])
    user.middlename = test_data['user_extra']['middlename']
    user.save()

    business = factory_business(**test_data['business'])
    business.legal_name = test_data['business_extra']['legal_name']
    business.tax_id = test_data['business_extra']['tax_id']
    business.save()

    for party in test_data['parties']:
        party_role = PartyRole(role=party['role'])
        party_role.party = Party(
            **{k: v for k, v in party.items() if k != 'role'})
        party_role.business_id = business.id
        party_role.save()

    issued_business_user_credential = DCBusinessUser(
        business_id=business.id, user_id=user.id)
    issued_business_user_credential.save()

    with patch.object(DigitalCredentialsRulesService, 'get_preconditions', return_value=None):
        # Act
        credential_data = get_digital_credential_data(
            user, business, credential_type)

        # Assert
        for item in credential_data:
            if item['name'] == 'credential_id':
                assert item['value'] == f'{issued_business_user_credential.id:08}'
            else:
                assert item in expected


@pytest.mark.parametrize('test_data, expected', [
    # In this first test the user has a party role
    ({
        'business': {
            'identifier': 'FM1234567',
            'entity_type': 'BEN',
            'founding_date': '2010-01-01',
            'state': 'ACTIVE',
        },
        'business_extra': {
            'legal_name': 'Test Business',
            'tax_id': '000000000000001',
        },
        'parties': [{
            'first_name': 'First',
            'middle_initial': 'Middle',
            'last_name': 'Last',
            'role': 'director'
        }],
        'user': {
            'username': 'test',
            'lastname': 'Last',
            'firstname': 'First',
        },
        'user_extra': {
            'middlename': 'Middle',
        }
    }, [
        {'name': 'credential_id', 'value': ''},
        {'name': 'identifier', 'value': 'FM1234567'},
        {'name': 'business_name', 'value': 'Test Business'},
        {'name': 'business_type', 'value': 'BC Benefit Company'},
        {'name': 'cra_business_number', 'value': '000000000000001'},
        {'name': 'registered_on_dateint', 'value': '20100101'},
        {'name': 'company_status', 'value': 'ACTIVE'},
        {'name': 'family_name', 'value': 'LAST'},
        {'name': 'given_names', 'value': 'FIRST MIDDLE'},
        {'name': 'role', 'value': 'Director, Incorporator'}
    ]),
    ({
        'business': {
            'identifier': 'FM1234567',
            'entity_type': 'SP',
            'founding_date': '2010-01-01',
            'state': 'ACTIVE',
        },
        'business_extra': {
            'legal_name': 'Test Business',
            'tax_id': '000000000000001',
        },
        'parties': [{
            'first_name': 'First',
            'middle_initial': 'Middle',
            'last_name': 'Last',
            'role': 'proprietor'
        }],
        'user': {
            'username': 'test',
            'lastname': 'Last',
            'firstname': 'First',
        },
        'user_extra': {
            'middlename': 'Middle',
        }
    }, [
        {'name': 'credential_id', 'value': ''},
        {'name': 'identifier', 'value': 'FM1234567'},
        {'name': 'business_name', 'value': 'Test Business'},
        {'name': 'business_type', 'value': 'BC Sole Proprietorship'},
        {'name': 'cra_business_number', 'value': '000000000000001'},
        {'name': 'registered_on_dateint', 'value': '20100101'},
        {'name': 'company_status', 'value': 'ACTIVE'},
        {'name': 'family_name', 'value': 'LAST'},
        {'name': 'given_names', 'value': 'FIRST MIDDLE'},
        {'name': 'role', 'value': 'Proprietor'}
    ]),
    # In this second test the user does not have a party role
    ({
        'business': {
            'identifier': 'FM1234567',
            'entity_type': 'BEN',
            'founding_date': '2010-01-01',
            'state': 'ACTIVE',
        },
        'business_extra': {
            'legal_name': 'Test Business',
            'tax_id': '000000000000001',
        },
        'parties': [{
            'first_name': 'First 2',
            'last_name': 'Last 2',
            'role': 'director'
        }],
        'user': {
            'username': 'test',
            'lastname': 'Last',
            'firstname': 'First',
        },
        'user_extra': {
            'middlename': 'Middle',
        }
    }, [
        {'name': 'credential_id', 'value': ''},
        {'name': 'identifier', 'value': 'FM1234567'},
        {'name': 'business_name', 'value': 'Test Business'},
        {'name': 'business_type', 'value': 'BC Benefit Company'},
        {'name': 'cra_business_number', 'value': '000000000000001'},
        {'name': 'registered_on_dateint', 'value': '20100101'},
        {'name': 'company_status', 'value': 'ACTIVE'},
        {'name': 'family_name', 'value': 'LAST'},
        {'name': 'given_names', 'value': 'FIRST MIDDLE'},
        {'name': 'role', 'value': 'Incorporator'}
    ]),
    ({
        'business': {
            'identifier': 'FM1234567',
            'entity_type': 'SP',
            'state': 'HISTORICAL',
        },
        'business_extra': {
            'legal_name': '',
            'tax_id': '',
        },
        'parties': [{
            'first_name': 'First 2',
            'last_name': 'Last 2',
            'role': 'proprietor'
        }],
        'user': {
            'username': 'test',
            'lastname': 'Last',
            'firstname': 'First',
        },
        'user_extra': {
            'middlename': '',
        }
    }, [
        {'name': 'credential_id', 'value': ''},
        {'name': 'identifier', 'value': 'FM1234567'},
        {'name': 'business_name', 'value': ''},
        {'name': 'business_type', 'value': 'BC Sole Proprietorship'},
        {'name': 'cra_business_number', 'value': ''},
        {'name': 'registered_on_dateint', 'value': '19700101'},
        {'name': 'company_status', 'value': 'HISTORICAL'},
        {'name': 'family_name', 'value': 'LAST'},
        {'name': 'given_names', 'value': 'FIRST'},
        {'name': 'role', 'value': ''}
    ])
])
def test_data_helper_user_is_completing_party(app, session, test_data, expected):
    """Assert that the data helper returns the correct data when the user is a completing party."""
    # Arrange
    credential_type = DCDefinition.CredentialType.business

    user = factory_user(**test_data['user'])
    user.middlename = test_data['user_extra']['middlename']
    user.save()

    business = factory_business(**test_data['business'])
    business.legal_name = test_data['business_extra']['legal_name']
    business.tax_id = test_data['business_extra']['tax_id']
    business.save()

    # User is also the completing party
    completing_party_role = create_party_role(
        PartyRole.RoleTypes.COMPLETING_PARTY,
        **create_test_user(first_name=test_data['user']['firstname'],
                           last_name=test_data['user']['lastname'],
                           middle_initial=test_data['user_extra']['middlename'])
    )
    filing = factory_completed_filing(
        business=business,
        data_dict={'filing': {'header': {'name': 'registration'}}},
        filing_date=datetime.utcnow(), filing_type='registration'
    )
    filing.filing_party_roles.append(completing_party_role)
    filing.submitter_id = user.id
    filing.save()

    for party in test_data['parties']:
        party_role = PartyRole(role=party['role'])
        party_role.party = Party(
            **{k: v for k, v in party.items() if k != 'role'})
        party_role.business_id = business.id
        party_role.save()

    issued_business_user_credential = DCBusinessUser(
        business_id=business.id, user_id=user.id)
    issued_business_user_credential.save()

    with patch.object(DigitalCredentialsRulesService, 'get_preconditions', return_value=None):
        # Act
        credential_data = get_digital_credential_data(
            user, business, credential_type)

        # Assert
        for item in credential_data:
            if item['name'] == 'credential_id':
                assert item['value'] == f'{issued_business_user_credential.id:08}'
            else:
                assert item in expected


def test_data_helper_role_not_added_if_preconditions_not_met(app, session):
    """Assert that the data helper returns the correct data when preconditions not met."""
    # Arrange
    credential_type = DCDefinition.CredentialType.business

    user = factory_user(
        username='test',
        lastname='Last',
        firstname='First',
    )

    business = factory_business(
        identifier='FM1234567',
        entity_type='BEN',
        founding_date='2010-01-01',
        state='ACTIVE'
    )
    business.legal_name = 'Test Business'
    business.tax_id = '000000000000001'
    business.save()

    party_role = PartyRole(role='director')
    party_role.party = Party(
        first_name='First',
        last_name='Last'
    )
    party_role.business_id = business.id
    party_role.save()

    issued_business_user_credential = DCBusinessUser(
        business_id=business.id, user_id=user.id)
    issued_business_user_credential.save()

    with patch.object(DigitalCredentialsRulesService, 'get_preconditions', return_value=['test']):
        # Act
        credential_data = get_digital_credential_data(
            user, business, credential_type, False)

        # Assert
        assert {'name': 'role', 'value': ''} in credential_data


def test_data_helper_role_added_if_preconditions_met(app, session):
    """Assert that the data helper returns the correct data when preconditions met."""
    # Arrange
    credential_type = DCDefinition.CredentialType.business

    user = factory_user(
        username='test',
        lastname='Last',
        firstname='First',
    )

    business = factory_business(
        identifier='FM1234567',
        entity_type='BEN',
        founding_date='2010-01-01',
        state='ACTIVE'
    )
    business.legal_name = 'Test Business'
    business.tax_id = '000000000000001'
    business.save()

    party_role = PartyRole(role='director')
    party_role.party = Party(
        first_name='First',
        last_name='Last'
    )
    party_role.business_id = business.id
    party_role.save()

    issued_business_user_credential = DCBusinessUser(
        business_id=business.id, user_id=user.id)
    issued_business_user_credential.save()

    with patch.object(DigitalCredentialsRulesService, 'get_preconditions', return_value=['test']):
        # Act
        credential_data = get_digital_credential_data(
            user, business, credential_type, True)

        print(credential_data)

        # Assert
        assert {'name': 'role', 'value': 'Director'} in credential_data
