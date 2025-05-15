# Copyright © 2022 Province of British Columbia
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

"""Tests to assure the internal end-point is working as expected."""
import copy
import datedelta
from freezegun import freeze_time
import pytest
from datetime import datetime, timezone
from http import HTTPStatus
from unittest.mock import patch
from registry_schemas.example_data import (
    CHANGE_OF_ADDRESS,
    FILING_HEADER,
)

from legal_api.models import Business, Filing, UserRoles
from legal_api.resources.v2 import internal_services
from legal_api.resources.v2.internal_services import ListFilingResource
from tests.unit.models import factory_business, factory_business_mailing_address
from tests.unit.services.utils import create_header


def test_get_future_effective_filing_ids(session, client, jwt):
    """Assert that future effective filings are saved and have the correct status changes."""
    import pytz
    from tests.unit.models import factory_pending_filing
    # setup
    identifier = 'CP7654321'
    b = factory_business(identifier,
                         (datetime.now(timezone.utc) - datedelta.YEAR),
                         None,
                         Business.LegalTypes.BCOMP.value)
    factory_business_mailing_address(b)
    coa = copy.deepcopy(FILING_HEADER)
    coa['filing']['header']['name'] = 'changeOfAddress'
    coa['filing']['changeOfAddress'] = CHANGE_OF_ADDRESS
    coa['filing']['changeOfAddress']['offices']['registeredOffice']['deliveryAddress']['addressCountry'] = 'CA'
    coa['filing']['changeOfAddress']['offices']['registeredOffice']['mailingAddress']['addressCountry'] = 'CA'
    coa['filing']['business']['identifier'] = identifier

    filing = factory_pending_filing(b, coa)
    filing.effective_date = datetime.now(timezone.utc)
    filing.save()
    assert filing.status == Filing.Status.PENDING.value

    filing.payment_completion_date = datetime.now(timezone.utc)
    filing.save()

    assert filing.status == Filing.Status.PAID.value

    # check values that future effective filings job depends on are there
    rv = client.get('/api/v2/internal/filings/future_effective', headers=create_header(jwt, [UserRoles.system]))
    assert rv.status_code == HTTPStatus.OK
    assert rv.json
    assert rv.json[0] == filing.id

    # back date and check
    with freeze_time(filing.effective_date - datedelta.DAY):
        rv = client.get('/api/v2/internal/filings/future_effective', headers=create_header(jwt, [UserRoles.system]))
        assert rv.status_code == HTTPStatus.OK
        assert len(rv.json) == 0


@pytest.mark.parametrize(
    'test_name, expired', [
        ('LIMITED_RESTORATION', True),
        ('LIMITED_RESTORATION_EXPIRED', False)
    ]
)
def test_get_businesses_expired_restoration(session, client, jwt, test_name, expired):
    """Assert that expired restoration can be fetched."""
    identifier = 'BC1234567'
    business = factory_business(identifier=identifier, entity_type=Business.LegalTypes.COMP.value)
    business.restoration_expiry_date = (datetime.now(timezone.utc) +
                                        datedelta.datedelta(days=-1 if expired else 1))
    business.save()
    rv = client.get('/api/v2/internal/expired_restoration', headers=create_header(jwt, [UserRoles.system]))
    if expired:
        assert rv.status_code == HTTPStatus.OK
        assert len(rv.json) == 1
        assert rv.json['businesses'][0]['identifier'] == identifier
        assert rv.json['businesses'][0]['legalType'] == business.legal_type
    else:
        assert rv.status_code == HTTPStatus.OK
        assert len(rv.json['businesses']) == 0


def test_update_bn_move(session, client, jwt):
    """Assert that the endpoint updates tax_id."""
    identifier = 'FM0000001'
    business = factory_business(identifier, entity_type=Business.LegalTypes.SOLE_PROP.value)
    business.tax_id = '993775204BC0001'
    business.save()

    new_bn = '993777399BC0001'
    with patch.object(internal_services, 'publish_to_queue'):
        with patch.object(ListFilingResource, 'create_invoice', return_value=(
                {'isPaymentActionRequired': False}, HTTPStatus.CREATED)):
            rv = client.post('/api/v2/internal/bnmove',
                             headers=create_header(jwt, [UserRoles.system], identifier),
                             json={
                                 'oldBn': business.tax_id,
                                 'newBn': new_bn
                             })
            assert rv.status_code == HTTPStatus.OK
            assert Business.find_by_tax_id(new_bn)


@pytest.mark.parametrize('data', [
    ({}),
    ({'oldBn': '993775204BC0001'}),
    ({'newBn': '993777399BC0001'}),
])
def test_update_bn_move_missing_data(session, client, jwt, data):
    """Assert that the endpoint validates missing data."""
    rv = client.post('/api/v2/internal/bnmove',
                     headers=create_header(jwt, [UserRoles.system]),
                     json=data)
    assert rv.status_code == HTTPStatus.BAD_REQUEST
