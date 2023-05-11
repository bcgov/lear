# Copyright © 2019 Province of British Columbia
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

"""Tests to assure the business-filing end-point.

Test-Suite to ensure that the /businesses endpoint is working as expected.
"""
import copy
import datetime
from http import HTTPStatus

from registry_schemas.example_data import ALTERATION_FILING_TEMPLATE

from legal_api.models import Filing, LegalEntity
from legal_api.services.authz import STAFF_ROLE
from tests import integration_namerequests, integration_payment
from tests.unit.models import factory_legal_entity, factory_legal_entity_mailing_address
from tests.unit.services.utils import create_header


@integration_payment
@integration_namerequests
def test_alteration_success_bc_to_ben(client, jwt, session):
    """Assert that a valid BC to BEN alteration can be posted."""
    identifier = 'BC1156638'
    b = factory_legal_entity(identifier, datetime.datetime.utcnow(), None, LegalEntity.EntityTypes.COMP.value)
    factory_legal_entity_mailing_address(b)

    filing = copy.deepcopy(ALTERATION_FILING_TEMPLATE)
    filing['filing']['business']['identifier'] = identifier
    filing['filing']['business']['legalType'] = LegalEntity.EntityTypes.COMP.value
    filing['filing']['alteration']['business']['legalType'] = LegalEntity.EntityTypes.BCOMP.value

    rv = client.post(f'/api/v1/businesses/{identifier}/filings',
                     json=filing,
                     headers=create_header(jwt, [STAFF_ROLE], None))

    assert rv.status_code == HTTPStatus.CREATED
    assert rv.json['filing']['header']['name'] == 'alteration'

    filing = Filing.get_filing_by_payment_token(rv.json['filing']['header']['paymentToken'])
    assert filing
    assert filing.status == Filing.Status.PENDING.value


@integration_payment
@integration_namerequests
def test_alteration_success_ben_to_bc(client, jwt, session):
    """Assert that a valid BEN to BC alteration can be posted."""
    identifier = 'BC1156638'
    b = factory_legal_entity(identifier, datetime.datetime.utcnow(), None, LegalEntity.EntityTypes.BCOMP.value)
    factory_legal_entity_mailing_address(b)

    filing = copy.deepcopy(ALTERATION_FILING_TEMPLATE)
    filing['filing']['business']['identifier'] = identifier
    filing['filing']['business']['legalType'] = LegalEntity.EntityTypes.BCOMP.value
    filing['filing']['alteration']['business']['legalType'] = LegalEntity.EntityTypes.COMP.value

    rv = client.post(f'/api/v1/businesses/{identifier}/filings',
                     json=filing,
                     headers=create_header(jwt, [STAFF_ROLE], None))

    assert rv.status_code == HTTPStatus.CREATED
    assert rv.json['filing']['header']['name'] == 'alteration'

    filing = Filing.get_filing_by_payment_token(rv.json['filing']['header']['paymentToken'])
    assert filing
    assert filing.status == Filing.Status.PENDING.value
