# Copyright (c) 2025, Province of British Columbia
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# 
# 1. Redistributions of source code must retain the above copyright notice, this
#    list of conditions and the following disclaimer.
# 
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
# 
# 3. Neither the name of the copyright holder nor the names of its
#    contributors may be used to endorse or promote products derived from
#    this software without specific prior written permission.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""Tests to assure the BusinessAccountSettings Model."""
from http import HTTPStatus

import pytest

from legal_api.exceptions import BusinessException
from legal_api.models import BusinessAccountSettings
from tests.unit.models import factory_business


def test_business_account_settings_minimal(session):
    """Assert that a minimal BusinessAccountSettings can be created."""
    business = factory_business('BC1234567')
    settings = BusinessAccountSettings(business_id=business.id)
    settings.save()

    assert settings.id is not None


def test_business_account_settings_json(session):
    """Assert BusinessAccountSettings json property."""
    business_identifier = 'BC1234567'
    account_id = 1
    email = 'fake@email.com'
    phone = '123456789'
    phone_extension = '1'
    ar_reminder = False
    business = factory_business(business_identifier)
    settings = BusinessAccountSettings(business_id=business.id,
                                       account_id=account_id,
                                       email=email,
                                       phone=phone,
                                       phone_extension=phone_extension,
                                       ar_reminder=ar_reminder)
    settings.save()
    
    assert settings.id

    json = settings.json
    assert json['businessIdentifier'] == business_identifier
    assert json['accountId'] == account_id
    assert json['email'] == email
    assert json['phone'] == phone
    assert json['phoneExtension'] == phone_extension
    assert json['arReminder'] == ar_reminder


@pytest.mark.parametrize('test_name,prev_data,new_data,expected_json',[
  ('Add new default', None, {}, {'email': None, 'phone': None, 'phoneExtension': None, 'arReminder': True}),
  ('Add new with email', None, {'email': 'test@e.com'}, {'email': 'test@e.com', 'phone': None, 'phoneExtension': None, 'arReminder': True}),
  ('Add new with all', None, {'email': 'test@e.com', 'phone': '1234', 'phoneExtension': '1', 'arReminder': False}, {'email': 'test@e.com', 'phone': '1234', 'phoneExtension': '1', 'arReminder': False}),
  ('Update existing email', {'email': 'unchanged@e.com', 'phone': '12345', 'arReminder': False}, {'email': 'updated@e.com'}, {'email': 'updated@e.com', 'phone': '12345', 'phoneExtension': None, 'arReminder': False}),
  ('Update existing email and ar reminder', {'email': 'unchanged@e.com', 'phone': '12345', 'arReminder': False}, {'email': 'updated@e.com', 'arReminder': True}, {'email': 'updated@e.com', 'phone': '12345', 'phoneExtension': None, 'arReminder': True})
])
def test_business_account_settings_create_or_replace(session, test_name, prev_data, new_data, expected_json):
    """Assert creating and updating business account settings records."""
    business_identifier = 'BC1234567'
    account_id = 1
    expected_json['businessIdentifier'] = business_identifier
    expected_json['accountId'] = account_id

    business = factory_business(business_identifier)
    if prev_data:
        prev_settings = BusinessAccountSettings.create_or_update(business.id, account_id, prev_data)
        assert prev_settings.id
    
    # update with new data
    settings = BusinessAccountSettings.create_or_update(business.id, account_id, new_data)
    assert settings.id
    if prev_data:
        assert prev_settings and prev_settings.id == settings.id
    # verify changes
    assert settings.json == expected_json


def test_business_account_settings_delete(session):
    """Assert that business account settings for a specific account can be deleted."""
    account_id = 1
    business = factory_business('BC1234567')
    settings = BusinessAccountSettings.create_or_update(business.id, account_id, {})
    settings.save()

    assert settings.id

    BusinessAccountSettings.delete(business.id, account_id)
    assert not BusinessAccountSettings.find_by_id(settings.id)


def test_business_account_settings_block_default_delete(session):
    """Assert that attempting to delete the default business settings will raise a BusinessException."""
    business = factory_business('BC1234567')
    settings = BusinessAccountSettings(business_id=business.id)
    settings.save()

    with pytest.raises(BusinessException) as excinfo:
        BusinessAccountSettings.delete(business.id, None)

    assert excinfo.value.status_code == HTTPStatus.FORBIDDEN
    assert excinfo.value.error == 'Cannot delete the default business settings.'
