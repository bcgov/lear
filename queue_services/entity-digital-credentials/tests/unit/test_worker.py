# Copyright © 2023 Province of British Columbia
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
"""Tests for the queue worker are contained here."""

from unittest.mock import patch

import pytest
from legal_api.models import Filing

from entity_digital_credentials.worker import process_digital_credential
from tests.unit import create_business, create_filing


ADMIN_REVOKE = 'bc.registry.admin.revoke'
BUSINESS_NUMBER = 'bc.registry.business.bn'
CHANGE_OF_REGISTRATION = 'bc.registry.business.changeOfRegistration'
DISSOLUTION = 'bc.registry.business.dissolution'
PUT_BACK_ON = 'bc.registry.business.putBackOn'


@pytest.mark.asyncio
@patch('entity_digital_credentials.digital_credentials_processors.admin_revoke.process')
@patch('entity_digital_credentials.digital_credentials_processors.business_number.process')
@patch('entity_digital_credentials.digital_credentials_processors.change_of_registration.process')
@patch('entity_digital_credentials.digital_credentials_processors.dissolution.process')
@patch('entity_digital_credentials.digital_credentials_processors.put_back_on.process')
async def test_processes_not_run(mock_put_back_on, mock_dissolution, mock_change_of_registration,
                                 mock_business_number, mock_admin_revoke, app, session):
    """Assert processors are not called if message type is not supported."""
    # Arrange
    dc_msg = {'type': 'bc.registry.business.test', 'identifier': 'FM0000001'}

    # Act
    await process_digital_credential(dc_msg, flask_app=app)

    # Assert
    mock_admin_revoke.assert_not_called()
    mock_business_number.assert_not_called()
    mock_change_of_registration.assert_not_called()
    mock_dissolution.assert_not_called()
    mock_put_back_on.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize('dc_msg', [{
    'type': ADMIN_REVOKE,
    'identifier': 'FM0000001'
}, {
    'type': BUSINESS_NUMBER,
    'identifier': 'FM0000002'
}])
@patch('entity_digital_credentials.digital_credentials_processors.admin_revoke.process')
@patch('entity_digital_credentials.digital_credentials_processors.business_number.process')
@patch('entity_digital_credentials.digital_credentials_processors.change_of_registration.process')
@patch('entity_digital_credentials.digital_credentials_processors.dissolution.process')
@patch('entity_digital_credentials.digital_credentials_processors.put_back_on.process')
async def test_processes_no_filing_required(mock_put_back_on, mock_dissolution, mock_change_of_registration,
                                            mock_business_number, mock_admin_revoke, dc_msg, app, session):
    """Assert processor runs if given the right message type."""
    # Arrange
    business = create_business(dc_msg['identifier'])

    # Act
    await process_digital_credential(dc_msg, flask_app=app)

    # Assert
    if dc_msg['type'] == ADMIN_REVOKE:
        mock_admin_revoke.assert_called_once()
        assert business.identifier == 'FM0000001'
        mock_admin_revoke.assert_called_with(business)

        # Other processors should not be called
        mock_business_number.assert_not_called()
        mock_change_of_registration.assert_not_called()
        mock_dissolution.assert_not_called()
        mock_put_back_on.assert_not_called()
    elif dc_msg['type'] == BUSINESS_NUMBER:
        mock_business_number.assert_called_once()
        assert business.identifier == 'FM0000002'
        mock_business_number.assert_called_with(business)

        # Other processors should not be called
        mock_admin_revoke.assert_not_called()
        mock_change_of_registration.assert_not_called()
        mock_dissolution.assert_not_called()
        mock_put_back_on.assert_not_called()
    else:
        assert False


@pytest.mark.asyncio
@pytest.mark.parametrize('dc_msg', [{
    'type': CHANGE_OF_REGISTRATION,
    'identifier': 'FM0000001',
    'data': {'filing': {'header': {'filingId': None}}}
}, {
    'type': DISSOLUTION,
    'identifier': 'FM0000002',
    'data': {'filing': {'header': {'filingId': None}}}
}, {
    'type': PUT_BACK_ON,
    'identifier': 'FM0000003',
    'data': {'filing': {'header': {'filingId': None}}}
}])
@patch('entity_digital_credentials.digital_credentials_processors.admin_revoke.process')
@patch('entity_digital_credentials.digital_credentials_processors.business_number.process')
@patch('entity_digital_credentials.digital_credentials_processors.change_of_registration.process')
@patch('entity_digital_credentials.digital_credentials_processors.dissolution.process')
@patch('entity_digital_credentials.digital_credentials_processors.put_back_on.process')
async def test_processes_filing_required(mock_put_back_on, mock_dissolution, mock_change_of_registration,
                                         mock_business_number, mock_admin_revoke, dc_msg, app, session):
    """Assert processor runs if given the right message type."""
    # Arrange
    business = create_business(dc_msg['identifier'])
    filing_type = dc_msg['type'].replace('bc.registry.business.', '')
    filing = create_filing(session, business.id, None, filing_type, Filing.Status.COMPLETED.value)
    dc_msg['data']['filing']['header']['filingId'] = filing.id

    # Act
    await process_digital_credential(dc_msg, flask_app=app)

    # Assert
    if dc_msg['type'] == CHANGE_OF_REGISTRATION:
        mock_change_of_registration.assert_called_once()
        assert business.identifier == 'FM0000001'
        mock_change_of_registration.assert_called_with(business, filing)

        # Other processors should not be called
        mock_admin_revoke.assert_not_called()
        mock_business_number.assert_not_called()
        mock_dissolution.assert_not_called()
        mock_put_back_on.assert_not_called()
    elif dc_msg['type'] == DISSOLUTION:
        mock_dissolution.assert_called_once()
        assert business.identifier == 'FM0000002'
        mock_dissolution.assert_called_with(business, 'test')

        # Other processors should not be called
        mock_admin_revoke.assert_not_called()
        mock_business_number.assert_not_called()
        mock_change_of_registration.assert_not_called()
        mock_put_back_on.assert_not_called()
    elif dc_msg['type'] == PUT_BACK_ON:
        mock_put_back_on.assert_called_once()
        assert business.identifier == 'FM0000003'
        mock_put_back_on.assert_called_with(business)

        # Other processors should not be called
        mock_admin_revoke.assert_not_called()
        mock_business_number.assert_not_called()
        mock_change_of_registration.assert_not_called()
        mock_dissolution.assert_not_called()
    else:
        assert False


@pytest.mark.asyncio
@pytest.mark.parametrize('dc_msg', [{
    'type': CHANGE_OF_REGISTRATION,
    'identifier': 'FM0000001'
}, {
    'type': CHANGE_OF_REGISTRATION,
    'identifier': 'FM0000001',
    'data': {}
}, {
    'type': CHANGE_OF_REGISTRATION,
    'identifier': 'FM0000001',
    'data': {'filing': {}}
}, {
    'type': CHANGE_OF_REGISTRATION,
    'identifier': 'FM0000001',
    'data': {'filing': {'header': {}}}
}])
async def test_process_failure_filing_required(app, session, dc_msg):
    """Assert processor throws QueueException if filing data not in message."""
    # Arrange
    from entity_queue_common.service_utils import QueueException

    # Act
    with pytest.raises(QueueException) as excinfo:
        await process_digital_credential(dc_msg, flask_app=app)

    # Assert
    assert 'Digital credential message is missing data.' in str(excinfo)


@pytest.mark.asyncio
async def test_process_failure_no_identifier_no_filing_required(app, session):
    """Assert processor throws QueueException if no idenfiier in message."""
    # Arrange
    from entity_queue_common.service_utils import QueueException
    dc_msg = {'type': ADMIN_REVOKE}

    # Act
    with pytest.raises(QueueException) as excinfo:
        await process_digital_credential(dc_msg, flask_app=app)

    # Assert
    assert 'Digital credential message is missing identifier' in str(excinfo)


@pytest.mark.asyncio
async def test_process_failure_no_business_no_filing_required(app, session):
    """Assert processor throws Exception if idenfiier in message but business not found."""
    # Arrange
    identifier = 'FM0000001'
    dc_msg = {'type': ADMIN_REVOKE, 'identifier': identifier}

    # Act
    with pytest.raises(Exception) as excinfo:
        await process_digital_credential(dc_msg, flask_app=app)

    # Assert
    assert f'Business with identifier: {identifier} not found.' in str(excinfo)
