# Copyright © 2022 Province of British Columbia
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
"""Tests for the Minio service.

Test suite to ensure that the Digital Credentials service are working as expected.
"""
from unittest.mock import MagicMock

import pytest
from legal_api.models import DCDefinition, DCIssuedBusinessUserCredential,  PartyRole
from legal_api.services import digital_credentials
from legal_api.services.digital_credentials import DigitalCredentialsHelpers, DigitalCredentialsService
from tests.unit.models import factory_business, factory_user

schema_id = 'test_schema_id'
cred_def_id = 'test_credential_definition_id'

def test_init_app(app, session):
    """Assert that the init app register schema and credential definition."""
    DigitalCredentialsService._fetch_schema = MagicMock(return_value=schema_id)
    DigitalCredentialsService._fetch_credential_definition = MagicMock(return_value=cred_def_id)

    digital_credentials.init_app(app)
    definition = DCDefinition.find_by_credential_type(DCDefinition.CredentialType.business)
    assert definition.schema_id == schema_id
    assert definition.schema_name == digital_credentials.business_schema_name
    assert definition.schema_version == digital_credentials.business_schema_version
    assert definition.credential_definition_id == cred_def_id
    assert not definition.is_deleted


@pytest.mark.parametrize('test_data', [{
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
    'party_roles': [{
        'role': 'proprietor'
    }],
    'user': {
        'username': 'test',
        'lastname': 'Last',
        'firstname': 'First',
    },
    'user_extra': {
        'middlename': 'Middle',
    },
    'expected': [
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
    ]
}, {
    'business': {
        'identifier': 'FM1234567'
    },
    'business_extra': {
        'legal_name': '',
        'tax_id': '',
    },
    'party_roles': [{
        'role': ''
    }],
    'user': {
        'username': 'test'
    },
    'user_extra': {
        'middlename': '',
    },
    'expected': [
        {'name': 'credential_id', 'value': ''},
        {'name': 'identifier', 'value': 'FM1234567'},
        {'name': 'business_name', 'value': ''},
        {'name': 'business_type', 'value': 'BC Cooperative Association'},
        {'name': 'cra_business_number', 'value': ''},
        {'name': 'registered_on_dateint', 'value': '19700101'},
        {'name': 'company_status', 'value': 'ACTIVE'},
        {'name': 'family_name', 'value': ''},
        {'name': 'given_names', 'value': ''},
        {'name': 'role', 'value': ''}
    ]
}])
def test_data_helper(app, session, test_data):
    """Assert that the data helper returns the correct data."""
    # Arrange
    credential_type = DCDefinition.CredentialType.business

    user = factory_user(**test_data['user'])
    user.middlename = test_data['user_extra']['middlename']
    user.save()

    business = factory_business(**test_data['business'])
    business.legal_name = test_data['business_extra']['legal_name']
    business.tax_id = test_data['business_extra']['tax_id']
    business.save()

    for party_role in test_data['party_roles']:
        _party_role = PartyRole(**party_role)
        _party_role.business_id = business.id
        _party_role.save()

    issued_business_user_credential = DCIssuedBusinessUserCredential(business_id=business.id, user_id=user.id)
    issued_business_user_credential.save()

    # Act
    credential_data = DigitalCredentialsHelpers.get_digital_credential_data(business, user, credential_type)

    # Assert
    for item in credential_data:
        if item['name'] == 'credential_id':
            assert item['value'] == f'{issued_business_user_credential.id:08}'
        else:
            assert item in test_data['expected']