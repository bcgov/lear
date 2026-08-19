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

"""Tests to assure the business snapshot end-point."""
from colin_api.exceptions import BusinessNotFoundException, PartiesNotFoundException
from colin_api.models import Business, Party, ShareObject
from tests.unit import LEAR_ADDRESS, build_business, bypass_auth


SNAPSHOT_URL = '/api/v1/businesses/BC0870226/snapshot'


def test_get_snapshot(client, mocker, authorized, mock_db, mock_lookups):  # pylint: disable=unused-argument
    """Assert the full LEAR-normalized snapshot is returned."""
    rv = client.get(SNAPSHOT_URL)

    assert rv.status_code == 200
    assert rv.json == {
        'business': {
            'identifier': 'BC0870226',
            'legalName': 'COLIN TEST COMPANY LTD.',
            'legalType': 'BC',
            'state': 'ACTIVE',
            'goodStanding': True,
            'adminFreeze': False,
            'foundingDate': '2000-01-01T08:00:00+00:00',
            'taxId': '791861078BC0001',
            'hasFutureEffectiveFiling': False
        },
        'parties': [{
            'officer': {
                'id': 999,
                'firstName': 'JANE',
                'lastName': 'DOE',
                'middleInitial': '',
                'organizationName': '',
                'partyType': 'person',
                'email': None
            },
            'deliveryAddress': LEAR_ADDRESS,
            'mailingAddress': LEAR_ADDRESS,
            'roles': [{'roleType': 'Director', 'appointmentDate': '2010-05-05', 'cessationDate': None}]
        }],
        'offices': {
            'registeredOffice': {'deliveryAddress': LEAR_ADDRESS, 'mailingAddress': LEAR_ADDRESS},
            'recordsOffice': {'deliveryAddress': LEAR_ADDRESS, 'mailingAddress': LEAR_ADDRESS}
        },
        'shareClasses': [{
            'id': 0,
            'name': 'CLASS A',
            'priority': 0,
            'hasMaximumShares': True,
            'maxNumberOfShares': 10000,
            'hasParValue': True,
            'parValue': 1.5,
            'currency': 'OTH',
            'currencyAdditional': 'BITCOIN',
            'hasRightsOrRestrictions': True,
            'series': [{
                'id': 1,
                'name': 'SERIES 1',
                'priority': 1,
                'hasMaximumShares': False,
                'maxNumberOfShares': None,
                'hasRightsOrRestrictions': False
            }]
        }],
        'resolutions': [{'date': '2020-01-01'}, {'date': '2019-06-15'}]
    }


def test_get_snapshot_maps_historical_state(client, mocker, authorized, mock_db,
                                            mock_lookups):  # pylint: disable=unused-argument
    """Assert a non-active corp (eg. amalgamated or dissolved) reports the LEAR-style HISTORICAL."""
    mocker.patch.object(Business, 'find_by_identifier', return_value=build_business(corp_state_class='HIS'))

    rv = client.get(SNAPSHOT_URL)

    assert rv.status_code == 200
    assert rv.json['business']['state'] == 'HISTORICAL'


def test_get_snapshot_reports_future_effective_filing(client, mocker, authorized, mock_db,
                                                      mock_lookups):  # pylint: disable=unused-argument
    """Assert an outstanding future effective filing is reported."""
    mock_db.cursor.fetchone.return_value = (1,)

    rv = client.get(SNAPSHOT_URL)

    assert rv.status_code == 200
    assert rv.json['business']['hasFutureEffectiveFiling'] is True
    # the count query runs against the bare corp num
    assert mock_db.cursor.execute.call_args.kwargs['corp_num'] == '0870226'
    assert 'effective_dt' in mock_db.cursor.execute.call_args.args[0]


def test_get_snapshot_without_parties(client, mocker, authorized, mock_db,
                                      mock_lookups):  # pylint: disable=unused-argument
    """Assert a corp with no current directors on file still returns a snapshot."""
    mocker.patch.object(Party, 'get_current', side_effect=PartiesNotFoundException(identifier='0870226'))

    rv = client.get(SNAPSHOT_URL)

    assert rv.status_code == 200
    assert rv.json['parties'] == []


def test_get_snapshot_without_share_structure(client, mocker, authorized, mock_db,
                                              mock_lookups):  # pylint: disable=unused-argument
    """Assert a corp with no share structure returns an empty list rather than failing."""
    mocker.patch.object(ShareObject, 'get_all', return_value=None)

    rv = client.get(SNAPSHOT_URL)

    assert rv.status_code == 200
    assert rv.json['shareClasses'] == []


def test_get_snapshot_null_good_standing(client, mocker, authorized, mock_db,
                                         mock_lookups):  # pylint: disable=unused-argument
    """Assert COLIN's tri-state good standing passes through as null when unknown."""
    mocker.patch.object(Business, 'find_by_identifier', return_value=build_business(good_standing=None))

    rv = client.get(SNAPSHOT_URL)

    assert rv.status_code == 200
    assert rv.json['business']['goodStanding'] is None


def test_get_snapshot_single_connection_and_scope(client, mocker, authorized, mock_db,
                                                  mock_lookups):  # pylint: disable=unused-argument
    """Assert one pooled session is used and the lookup is restricted to in-scope corp types."""
    find = mocker.patch.object(Business, 'find_by_identifier', return_value=build_business())

    assert client.get(SNAPSHOT_URL).status_code == 200

    # BC prefix stripped, same restriction as auth-info, and the pooled session is shared
    assert find.call_args.args[0] == '0870226'
    assert find.call_args.kwargs['corp_types'] == ['BC', 'ULC', 'CC']
    assert find.call_args.kwargs['con'] is mock_db.connection
    assert mock_db.connection.cursor.call_count == 1


def test_get_snapshot_no_results(client, mocker, authorized, mock_db,
                                 mock_lookups):  # pylint: disable=unused-argument
    """Assert a business that does not exist in COLIN returns a 404."""
    mocker.patch.object(Business, 'find_by_identifier',
                        side_effect=BusinessNotFoundException(identifier='BC0000000'))

    rv = client.get('/api/v1/businesses/BC0000000/snapshot')

    assert rv.status_code == 404
    assert None is not rv.json['message']


def test_get_snapshot_handles_unexpected_error(client, mocker, authorized, mock_db,
                                               mock_lookups):  # pylint: disable=unused-argument
    """Assert an unexpected failure returns a 500 without leaking internals."""
    mocker.patch.object(Business, 'find_by_identifier', side_effect=Exception('oracle exploded'))

    rv = client.get(SNAPSHOT_URL)

    assert rv.status_code == 500
    assert 'oracle exploded' not in str(rv.json)


def test_get_snapshot_requires_colin_service_role(client, mocker):
    """Assert the endpoint is gated on the colin service role."""
    bypass_auth(mocker, roles_valid=False)

    rv = client.get(SNAPSHOT_URL)

    assert rv.status_code == 401
