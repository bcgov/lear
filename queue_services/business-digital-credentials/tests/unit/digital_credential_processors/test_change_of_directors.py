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
"""Tests for the change of directors processor are contained here."""

from unittest.mock import MagicMock, patch

from business_model.models import DCRevocationReason

from business_digital_credentials.digital_credential_processors import change_of_directors
from tests.unit import create_business, create_filing, create_user


@patch.object(change_of_directors, 'get_all_digital_credentials_for_business', return_value=[])
@patch.object(change_of_directors, 'revoke_digital_credential')
def test_processor_does_not_run_if_no_issued_credential(mock_revoke_digital_credential,
                                                              mock_get_all_digital_credentials_for_business,
                                                              app, session):
    """Assert that the processor does not run if the current business has no issued credentials."""
    business = create_business(identifier='BC0000001', legal_type='BEN')
    filing = create_filing(filing_json={
        'filing': {
            'header': {
                'name': 'changeOfDirectors',
                'filingId': None
            },
            'changeOfDirectors': {
                'directors': []
            }
        }}, business_id=business.id)

    change_of_directors.process(business, filing)

    mock_get_all_digital_credentials_for_business.assert_called_once_with(
        business=business)
    mock_revoke_digital_credential.assert_not_called()


@patch.object(change_of_directors, 'get_all_digital_credentials_for_business')
@patch.object(change_of_directors, 'revoke_digital_credential')
def test_processor_does_not_run_if_not_ben(mock_revoke_digital_credential,
                                          mock_get_all_digital_credentials_for_business,
                                          app, session):
    """Assert that the processor does not run if business is not a BEN."""
    business = create_business(identifier='FM0000001', legal_type='GP')
    filing = create_filing(filing_json={
        'filing': {
            'header': {
                'name': 'changeOfDirectors',
                'filingId': None
            },
            'changeOfDirectors': {
                'directors': []
            }
        }}, business_id=business.id)

    change_of_directors.process(business, filing)

    mock_get_all_digital_credentials_for_business.assert_not_called()
    mock_revoke_digital_credential.assert_not_called()


@patch.object(change_of_directors, 'get_all_digital_credentials_for_business')
@patch.object(change_of_directors, 'revoke_digital_credential')
def test_processor_skips_credential_with_no_user(mock_revoke_digital_credential,
                                                mock_get_all_digital_credentials_for_business,
                                                app, session):
    """Assert that the processor skips credentials with no associated user."""
    business = create_business(identifier='BC0000001', legal_type='BEN')
    filing = create_filing(filing_json={
        'filing': {
            'header': {
                'name': 'changeOfDirectors',
                'filingId': None
            },
            'changeOfDirectors': {
                'directors': []
            }
        }}, business_id=business.id)
    
    # Create mock credential with no connection/business_user/user
    mock_credential = MagicMock()
    mock_credential.id = 1
    mock_credential.connection = None
    mock_get_all_digital_credentials_for_business.return_value = [mock_credential]

    change_of_directors.process(business, filing)

    mock_get_all_digital_credentials_for_business.assert_called_once_with(business=business)
    mock_revoke_digital_credential.assert_not_called()


@patch.object(change_of_directors, 'get_all_digital_credentials_for_business')
@patch.object(change_of_directors, 'revoke_digital_credential')
def test_processor_revokes_credential_when_director_ceased(mock_revoke_digital_credential,
                                                          mock_get_all_digital_credentials_for_business,
                                                          app, session):
    """Assert that the processor revokes credential when matching director has ceased action."""
    business = create_business(identifier='BC0000001', legal_type='BEN')
    filing = create_filing(filing_json={
        'filing': {
            'header': {
                'name': 'changeOfDirectors',
                'filingId': None
            },
            'changeOfDirectors': {
                'directors': [
                    {
                        'id': 1,
                        'actions': ['ceased'],
                        'officer': {
                            'firstName': 'John',
                            'lastName': 'Doe',
                            'id': 12345
                        }
                    }
                ]
            }
        }}, business_id=business.id)
    
    user = create_user(firstname='John', lastname='Doe')
    mock_credential = MagicMock()
    mock_credential.id = 1
    mock_credential.connection.business_user.user = user
    mock_get_all_digital_credentials_for_business.return_value = [mock_credential]

    change_of_directors.process(business, filing)

    mock_get_all_digital_credentials_for_business.assert_called_once_with(business=business)
    mock_revoke_digital_credential.assert_called_once_with(
        credential=mock_credential,
        reason=DCRevocationReason.CHANGE_OF_DIRECTORS
    )


@patch.object(change_of_directors, 'get_all_digital_credentials_for_business')
@patch.object(change_of_directors, 'revoke_digital_credential')
def test_processor_revokes_credential_when_director_ceased_case_insensitive(mock_revoke_digital_credential,
                                                                           mock_get_all_digital_credentials_for_business,
                                                                           app, session):
    """Assert that the processor revokes credential when matching director has CEASED action (case insensitive)."""
    business = create_business(identifier='BC0000001', legal_type='BEN')
    filing = create_filing(filing_json={
        'filing': {
            'header': {
                'name': 'changeOfDirectors',
                'filingId': None
            },
            'changeOfDirectors': {
                'directors': [
                    {
                        'id': 1,
                        'actions': ['CEASED'],  # uppercase
                        'officer': {
                            'firstName': 'John',
                            'lastName': 'Doe',
                            'id': 12345
                        }
                    }
                ]
            }
        }}, business_id=business.id)
    
    user = create_user(firstname='John', lastname='Doe')
    mock_credential = MagicMock()
    mock_credential.id = 1
    mock_credential.connection.business_user.user = user
    mock_get_all_digital_credentials_for_business.return_value = [mock_credential]

    change_of_directors.process(business, filing)

    mock_get_all_digital_credentials_for_business.assert_called_once_with(business=business)
    mock_revoke_digital_credential.assert_called_once_with(
        credential=mock_credential,
        reason=DCRevocationReason.CHANGE_OF_DIRECTORS
    )


@patch.object(change_of_directors, 'get_all_digital_credentials_for_business')
@patch.object(change_of_directors, 'revoke_digital_credential')
def test_processor_does_not_revoke_when_director_not_ceased(mock_revoke_digital_credential,
                                                           mock_get_all_digital_credentials_for_business,
                                                           app, session):
    """Assert that the processor does not revoke credential when matching director does not have ceased action."""
    business = create_business(identifier='BC0000001', legal_type='BEN')
    filing = create_filing(filing_json={
        'filing': {
            'header': {
                'name': 'changeOfDirectors',
                'filingId': None
            },
            'changeOfDirectors': {
                'directors': [
                    {
                        'id': 1,
                        'actions': ['appointed'],
                        'officer': {
                            'firstName': 'John',
                            'lastName': 'Doe',
                            'id': 12345
                        }
                    }
                ]
            }
        }}, business_id=business.id)
    
    user = create_user(firstname='John', lastname='Doe')
    mock_credential = MagicMock()
    mock_credential.id = 1
    mock_credential.connection.business_user.user = user
    mock_get_all_digital_credentials_for_business.return_value = [mock_credential]

    change_of_directors.process(business, filing)

    mock_get_all_digital_credentials_for_business.assert_called_once_with(business=business)
    mock_revoke_digital_credential.assert_not_called()


@patch.object(change_of_directors, 'get_all_digital_credentials_for_business')
@patch.object(change_of_directors, 'revoke_digital_credential')
def test_processor_does_not_revoke_when_user_not_in_directors(mock_revoke_digital_credential,
                                                             mock_get_all_digital_credentials_for_business,
                                                             app, session):
    """Assert that the processor does not revoke credential when user is not in directors list."""
    business = create_business(identifier='BC0000001', legal_type='BEN')
    filing = create_filing(filing_json={
        'filing': {
            'header': {
                'name': 'changeOfDirectors',
                'filingId': None
            },
            'changeOfDirectors': {
                'directors': [
                    {
                        'id': 1,
                        'actions': ['ceased'],
                        'officer': {
                            'firstName': 'Jane',
                            'lastName': 'Smith',
                            'id': 12345
                        }
                    }
                ]
            }
        }}, business_id=business.id)
    
    user = create_user(firstname='John', lastname='Doe')
    mock_credential = MagicMock()
    mock_credential.id = 1
    mock_credential.connection.business_user.user = user
    mock_get_all_digital_credentials_for_business.return_value = [mock_credential]

    change_of_directors.process(business, filing)

    mock_get_all_digital_credentials_for_business.assert_called_once_with(business=business)
    mock_revoke_digital_credential.assert_not_called()


@patch.object(change_of_directors, 'get_all_digital_credentials_for_business')
@patch.object(change_of_directors, 'revoke_digital_credential')
def test_processor_handles_multiple_directors_and_credentials(mock_revoke_digital_credential,
                                                             mock_get_all_digital_credentials_for_business,
                                                             app, session):
    """Assert that the processor handles multiple directors and credentials correctly."""
    business = create_business(identifier='BC0000001', legal_type='BEN')
    filing = create_filing(filing_json={
        'filing': {
            'header': {
                'name': 'changeOfDirectors',
                'filingId': None
            },
            'changeOfDirectors': {
                'directors': [
                    {
                        'id': 1,
                        'actions': ['ceased'],
                        'officer': {
                            'firstName': 'John',
                            'lastName': 'Doe',
                            'id': 12345
                        }
                    },
                    {
                        'id': 2,
                        'actions': ['appointed'],
                        'officer': {
                            'firstName': 'Jane',
                            'lastName': 'Smith',
                            'id': 67890
                        }
                    }
                ]
            }
        }}, business_id=business.id)
    
    user1 = create_user(firstname='John', lastname='Doe')
    user2 = create_user(firstname='Jane', lastname='Smith')
    
    mock_credential1 = MagicMock()
    mock_credential1.id = 1
    mock_credential1.connection.business_user.user = user1
    
    mock_credential2 = MagicMock()
    mock_credential2.id = 2
    mock_credential2.connection.business_user.user = user2
    
    mock_get_all_digital_credentials_for_business.return_value = [mock_credential1, mock_credential2]

    change_of_directors.process(business, filing)

    mock_get_all_digital_credentials_for_business.assert_called_once_with(business=business)
    # Only John Doe's credential should be revoked (ceased), not Jane Smith's (appointed)
    mock_revoke_digital_credential.assert_called_once_with(
        credential=mock_credential1,
        reason=DCRevocationReason.CHANGE_OF_DIRECTORS
    )


@patch.object(change_of_directors, 'revoke_digital_credential')
@patch.object(change_of_directors, 'get_all_digital_credentials_for_business')
def test_processor_continues_processing_after_credential_error(mock_get_all_digital_credentials_for_business,
                                                              mock_revoke_digital_credential,
                                                              app, session):
    """Assert that the processor continues processing other credentials after one fails."""
    
    business = create_business(identifier='BC0000001', legal_type='BEN')
    filing = create_filing(filing_json={
        'filing': {
            'header': {
                'name': 'changeOfDirectors',
                'filingId': None
            },
            'changeOfDirectors': {
                'directors': [
                    {
                        'id': 1,
                        'actions': ['ceased'],
                        'officer': {'firstName': 'John', 'lastName': 'Doe'}
                    },
                    {
                        'id': 2,
                        'actions': ['ceased'],
                        'officer': {'firstName': 'Jane', 'lastName': 'Smith'}
                    }
                ]
            }
        }}, business_id=business.id)
    
    user1 = create_user(firstname='John', lastname='Doe')
    user2 = create_user(firstname='Jane', lastname='Smith')
    
    mock_credential1 = MagicMock()
    mock_credential1.id = 1
    mock_credential1.connection.business_user.user = user1
    
    mock_credential2 = MagicMock()
    mock_credential2.id = 2
    mock_credential2.connection.business_user.user = user2
    
    mock_get_all_digital_credentials_for_business.return_value = [mock_credential1, mock_credential2]
    
    # Make the first credential processing fail
    def side_effect(*args, **kwargs):
        if kwargs.get('credential') is mock_credential1:
            raise Exception("Test error")
        return None
    
    mock_revoke_digital_credential.side_effect = side_effect

    change_of_directors.process(business, filing)

    mock_get_all_digital_credentials_for_business.assert_called_once_with(business=business)
    
    # Both credentials should be attempted to be revoked, even though first one fails
    assert mock_revoke_digital_credential.call_count == 2


@patch.object(change_of_directors, 'get_all_digital_credentials_for_business')
@patch.object(change_of_directors, 'revoke_digital_credential')
def test_processor_does_not_revoke_when_actions_empty_array(mock_revoke_digital_credential,
                                                           mock_get_all_digital_credentials_for_business,
                                                           app, session):
    """Assert that the processor does not revoke credential when director has empty actions array."""
    business = create_business(identifier='BC0000001', legal_type='BEN')
    filing = create_filing(filing_json={
        'filing': {
            'header': {
                'name': 'changeOfDirectors',
                'filingId': None
            },
            'changeOfDirectors': {
                'directors': [
                    {
                        'id': 1,
                        'actions': [],  # empty array
                        'officer': {
                            'firstName': 'John',
                            'lastName': 'Doe',
                            'id': 12345
                        }
                    }
                ]
            }
        }}, business_id=business.id)
    
    user = create_user(firstname='John', lastname='Doe')
    mock_credential = MagicMock()
    mock_credential.id = 1
    mock_credential.connection.business_user.user = user
    mock_get_all_digital_credentials_for_business.return_value = [mock_credential]

    change_of_directors.process(business, filing)

    mock_get_all_digital_credentials_for_business.assert_called_once_with(business=business)
    mock_revoke_digital_credential.assert_not_called()


@patch.object(change_of_directors, 'get_all_digital_credentials_for_business')
@patch.object(change_of_directors, 'revoke_digital_credential')
def test_processor_does_not_revoke_when_actions_missing(mock_revoke_digital_credential,
                                                       mock_get_all_digital_credentials_for_business,
                                                       app, session):
    """Assert that the processor does not revoke credential when director has no actions field."""
    business = create_business(identifier='BC0000001', legal_type='BEN')
    filing = create_filing(filing_json={
        'filing': {
            'header': {
                'name': 'changeOfDirectors',
                'filingId': None
            },
            'changeOfDirectors': {
                'directors': [
                    {
                        'id': 1,
                        # actions field is missing entirely
                        'officer': {
                            'firstName': 'John',
                            'lastName': 'Doe',
                            'id': 12345
                        }
                    }
                ]
            }
        }}, business_id=business.id)
    
    user = create_user(firstname='John', lastname='Doe')
    mock_credential = MagicMock()
    mock_credential.id = 1
    mock_credential.connection.business_user.user = user
    mock_get_all_digital_credentials_for_business.return_value = [mock_credential]

    change_of_directors.process(business, filing)

    mock_get_all_digital_credentials_for_business.assert_called_once_with(business=business)
    mock_revoke_digital_credential.assert_not_called()