# Copyright © 2026 Province of British Columbia
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

"""Tests to assure the business auth-info end-point.

Test-Suite to ensure that the /businesses/<identifier>/auth-info endpoint used by auth
to create and refresh entities for COLIN businesses is working as expected.

The Oracle connection is mocked out, so these run without access to COLIN. The wider
business lookup (find_by_identifier) is stubbed - what is exercised here is the endpoint's
own behaviour: the corp password query, the corp type restriction, response shape and
error mapping.
"""
from colin_api.exceptions import BusinessNotFoundException
from colin_api.models import Business
from tests.unit import build_business, bypass_auth


AUTH_INFO_URL = '/api/v1/businesses/BC0870226/auth-info'
PASS_CODE = '111111111'


def test_get_auth_info(client, mocker, authorized, mock_db):  # pylint: disable=unused-argument
    """Assert the auth info needed by auth is returned for a COLIN corp."""
    mocker.patch.object(Business, 'find_by_identifier', return_value=build_business())
    # the corp password row - conftest's mock_db defaults fetchone to a count-style (0,)
    mock_db.cursor.fetchone.return_value = (PASS_CODE,)

    rv = client.get(AUTH_INFO_URL)

    assert rv.status_code == 200
    assert rv.json == {
        'identifier': '0870226',
        'legalName': 'COLIN TEST COMPANY LTD.',
        'legalType': 'BC',
        'status': 'ACTIVE',
        'goodStanding': True,
        'businessNumber': '791861078BC0001',
        'adminFreeze': False,
        'email': 'registered.office@test.com',
        'passCode': PASS_CODE
    }


def test_get_auth_info_maps_historical_state(client, mocker, authorized, mock_db):  # pylint: disable=unused-argument
    """Assert a non-active corp (eg. amalgamated or dissolved) reports the LEAR-style HISTORICAL."""
    mocker.patch.object(Business, 'find_by_identifier', return_value=build_business(corp_state_class='HIS'))

    rv = client.get(AUTH_INFO_URL)

    assert rv.status_code == 200
    assert rv.json['status'] == 'HISTORICAL'


def test_get_auth_info_strips_bc_prefix(client, mocker, authorized, mock_db):  # pylint: disable=unused-argument
    """Assert the BC prefix is stripped, since COLIN stores the bare corp number."""
    find = mocker.patch.object(Business, 'find_by_identifier', return_value=build_business())

    assert client.get(AUTH_INFO_URL).status_code == 200

    assert find.call_args.args[0] == '0870226'
    # the corp password lookup uses the bare corp num too
    assert mock_db.cursor.execute.call_args.kwargs['corp_num'] == '0870226'


def test_get_auth_info_restricted_to_in_scope_corp_types(client, mocker, authorized,
                                                         mock_db):  # pylint: disable=unused-argument
    """Assert only BC/ULC/CC are looked up.

    The response carries a credential, so the surface is limited to the corp types that can
    be affiliated from COLIN while not loaded in LEAR.
    """
    find = mocker.patch.object(Business, 'find_by_identifier', return_value=build_business())

    client.get(AUTH_INFO_URL)

    assert find.call_args.kwargs['corp_types'] == ['BC', 'ULC', 'CC']


def test_get_auth_info_queries_corp_password(client, mocker, authorized, mock_db):  # pylint: disable=unused-argument
    """Assert the passcode is read from the corporation corp_password column."""
    mocker.patch.object(Business, 'find_by_identifier', return_value=build_business())

    client.get(AUTH_INFO_URL)

    assert 'corp_password' in mock_db.cursor.execute.call_args.args[0].lower()


def test_get_auth_info_reuses_single_connection(client, mocker, authorized,
                                                mock_db):  # pylint: disable=unused-argument
    """Assert one pooled session is used for both lookups.

    DB.connection acquires a session from a pool capped at 10, so the business lookup and
    the passcode lookup must share one.
    """
    find = mocker.patch.object(Business, 'find_by_identifier', return_value=build_business())

    client.get(AUTH_INFO_URL)

    # both the business lookup and the passcode cursor come off the same connection
    assert find.call_args.kwargs['con'] is mock_db.connection
    assert mock_db.connection.cursor.call_count == 1


def test_get_auth_info_normalizes_admin_freeze(client, mocker, authorized,
                                               mock_db):  # pylint: disable=unused-argument
    """Assert COLIN's 'True'/'False' string is returned as a real boolean."""
    mocker.patch.object(Business, 'find_by_identifier', return_value=build_business(admin_freeze='True'))

    rv = client.get(AUTH_INFO_URL)

    assert rv.status_code == 200
    assert rv.json['adminFreeze'] is True


def test_get_auth_info_without_passcode(client, mocker, authorized, mock_db):  # pylint: disable=unused-argument
    """Assert a business with no corp password returns a null passcode rather than failing."""
    mocker.patch.object(Business, 'find_by_identifier', return_value=build_business())
    mock_db.cursor.fetchone.return_value = None

    rv = client.get(AUTH_INFO_URL)

    assert rv.status_code == 200
    assert rv.json['passCode'] is None


def test_get_auth_info_no_results(client, mocker, authorized, mock_db):  # pylint: disable=unused-argument
    """Assert a business that does not exist in COLIN returns a 404."""
    mocker.patch.object(Business, 'find_by_identifier',
                        side_effect=BusinessNotFoundException(identifier='BC0000000'))

    rv = client.get('/api/v1/businesses/BC0000000/auth-info')

    assert rv.status_code == 404
    assert None is not rv.json['message']


def test_get_auth_info_handles_unexpected_error(client, mocker, authorized,
                                                mock_db):  # pylint: disable=unused-argument
    """Assert an unexpected failure returns a 500 without leaking the payload."""
    mocker.patch.object(Business, 'find_by_identifier', side_effect=Exception('oracle exploded'))

    rv = client.get(AUTH_INFO_URL)

    assert rv.status_code == 500
    assert 'oracle exploded' not in str(rv.json)


def test_get_auth_info_requires_colin_service_role(client, mocker):
    """Assert the endpoint is gated on the colin service role."""
    bypass_auth(mocker, roles_valid=False)

    rv = client.get(AUTH_INFO_URL)

    assert rv.status_code == 401
