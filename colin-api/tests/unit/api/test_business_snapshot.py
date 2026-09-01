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
from datetime import datetime

import pytest

from colin_api.exceptions import BusinessNotFoundException, PartiesNotFoundException
from colin_api.models import Business, Party, ShareObject
from colin_api.models.shares import Share, ShareClass
from tests.unit import LEAR_ADDRESS, build_business, build_director, bypass_auth


SNAPSHOT_URL = '/api/v1/businesses/BC0870226/snapshot'


def build_share_structure_variant(class_name, currency='CAD', other_currency=None, series_name=None):
    """Return a current ShareObject with the subject class name / currency."""
    share_class = ShareClass()
    share_class.share_id = 0
    share_class.share_name = class_name
    share_class.currency_type = currency
    share_class.other_currency = other_currency
    share_class.has_max_shares = 'N'  # COLIN semantics: 'N' means has a maximum
    share_class.has_par_value = 'Y'
    share_class.has_special_rights = 'Y'
    share_class.par_value_amt = 1.5
    share_class.max_number_shares = 10000
    share_class.series = []
    if series_name:
        series = Share()
        series.share_id = 1
        series.share_name = series_name
        series.has_max_shares = 'Y'
        series.has_special_rights = 'N'
        series.max_number_shares = None
        share_class.series = [series]
    share_struct = ShareObject()
    share_struct.end_event_id = None
    share_struct.share_classes = [share_class]
    return share_struct


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
            'hasFutureEffectiveFiling': False,
            'jurisdiction': 'BC',
            'homeJurisdictionNumber': None,
            'homeCompanyName': None,
            'homeRecognitionDate': None
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
            'name': 'CLASS A Shares',
            'priority': 0,
            'hasMaximumShares': True,
            'maxNumberOfShares': 10000,
            'hasParValue': True,
            'parValue': 1.5,
            'currency': 'OTHER',
            'currencyAdditional': 'BITCOIN',
            'hasRightsOrRestrictions': True,
            'series': [{
                'id': 1,
                'name': 'SERIES 1 Shares',
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


def test_get_snapshot_normalizes_role_dates(client, mocker, authorized, mock_db,
                                            mock_lookups):  # pylint: disable=unused-argument
    """Assert a raw datetime role date (the founding-date fallback) is normalized to YYYY-MM-DD."""
    director = build_director()
    director.roles = [{
        'roleType': 'Director',
        'appointmentDate': datetime(2013, 4, 24, 0, 0),
        'cessationDate': None
    }]
    mocker.patch.object(Party, 'get_current', return_value=[director])

    rv = client.get(SNAPSHOT_URL)

    assert rv.status_code == 200
    assert rv.json['parties'][0]['roles'] == [
        {'roleType': 'Director', 'appointmentDate': '2013-04-24', 'cessationDate': None}
    ]


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


@pytest.mark.parametrize('colin_name, expected_name', [
    ('CLASS A COMMON SHARES', 'CLASS A COMMON Shares'),  # all-caps legacy suffix replaced
    ('preferred shares', 'preferred Shares'),  # lowercase suffix replaced (tombstone migration parity)
    ('Class A Shares', 'Class A Shares'),  # already normalized - unchanged
    ('CLASS B', 'CLASS B Shares'),  # no suffix - appended
])
def test_get_snapshot_normalizes_share_names(client, mocker, authorized, mock_db, mock_lookups,
                                             colin_name, expected_name):  # pylint: disable=unused-argument
    """Assert class and series names get the ' Shares' suffix legal-api requires."""
    mocker.patch.object(ShareObject, 'get_all', return_value=[
        build_share_structure_variant(colin_name, series_name='SERIES 1')])

    rv = client.get(SNAPSHOT_URL)

    assert rv.status_code == 200
    assert rv.json['shareClasses'][0]['name'] == expected_name
    assert rv.json['shareClasses'][0]['series'][0]['name'] == 'SERIES 1 Shares'


@pytest.mark.parametrize('currency, other_currency, expected, expected_additional', [
    ('CAD', None, 'CAD', None),  # real code passes through
    ('OTH', 'CAD', 'CAD', None),  # tombstone migration parity fold
    ('OTH', ' usd ', 'USD', None),  # any valid ISO 4217 code is promoted
    ('OTH', 'BITCOIN', 'OTHER', 'BITCOIN'),  # non-ISO free text stays flagged
    ('OTH', None, 'OTHER', None),
])
def test_get_snapshot_normalizes_currency(client, mocker, authorized, mock_db, mock_lookups,
                                          currency, other_currency, expected,
                                          expected_additional):  # pylint: disable=unused-argument
    """Assert COLIN's OTH currency is folded to an ISO code or OTHER."""
    mocker.patch.object(ShareObject, 'get_all', return_value=[
        build_share_structure_variant('Class A Shares', currency=currency, other_currency=other_currency)])

    rv = client.get(SNAPSHOT_URL)

    assert rv.status_code == 200
    assert rv.json['shareClasses'][0]['currency'] == expected
    assert rv.json['shareClasses'][0]['currencyAdditional'] == expected_additional


def test_get_snapshot_null_good_standing(client, mocker, authorized, mock_db,
                                         mock_lookups):  # pylint: disable=unused-argument
    """Assert COLIN's tri-state good standing passes through as null when unknown."""
    mocker.patch.object(Business, 'find_by_identifier', return_value=build_business(good_standing=None))

    rv = client.get(SNAPSHOT_URL)

    assert rv.status_code == 200
    assert rv.json['business']['goodStanding'] is None


def test_get_snapshot_extraprovincial(client, mocker, authorized, mock_db,
                                      mock_lookups):  # pylint: disable=unused-argument
    """Assert an extraprovincial (A) corp snapshots with its home jurisdiction data."""
    find = mocker.patch.object(Business, 'find_by_identifier', return_value=build_business(
        corp_num='A0077777',
        corp_type='A',
        jurisdiction='ON',
        home_juris_num='1234567',
        home_company_nme='HOME COMPANY INC.',
        home_recogn_dt='1999-01-01T08:00:00-00:00'
    ))

    rv = client.get('/api/v1/businesses/A0077777/snapshot')

    assert rv.status_code == 200
    # no BC-strip on an A identifier
    assert find.call_args.args[0] == 'A0077777'
    assert rv.json['business']['identifier'] == 'A0077777'
    assert rv.json['business']['legalType'] == 'A'
    assert rv.json['business']['jurisdiction'] == 'ON'
    assert rv.json['business']['homeJurisdictionNumber'] == '1234567'
    assert rv.json['business']['homeCompanyName'] == 'HOME COMPANY INC.'
    assert rv.json['business']['homeRecognitionDate'] == '1999-01-01T08:00:00+00:00'


def test_get_snapshot_single_connection_and_scope(client, mocker, authorized, mock_db,
                                                  mock_lookups):  # pylint: disable=unused-argument
    """Assert one pooled session is used and the lookup is restricted to in-scope corp types."""
    find = mocker.patch.object(Business, 'find_by_identifier', return_value=build_business())

    assert client.get(SNAPSHOT_URL).status_code == 200

    # BC prefix stripped, same restriction as auth-info, and the pooled session is shared
    assert find.call_args.args[0] == '0870226'
    assert find.call_args.kwargs['con'] is mock_db.connection
    assert 'corp_types' not in find.call_args.kwargs
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
