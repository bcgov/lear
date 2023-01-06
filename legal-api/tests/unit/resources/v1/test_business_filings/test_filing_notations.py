# Copyright © 2021 Province of British Columbia
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

from registry_schemas.example_data import (
    COURT_ORDER_FILING_TEMPLATE,
    REGISTRARS_NOTATION_FILING_TEMPLATE,
    REGISTRARS_ORDER_FILING_TEMPLATE,
)

from legal_api.models import Business, Filing
from legal_api.services.authz import STAFF_ROLE
from tests import integration_payment
from tests.unit.models import factory_business, factory_business_mailing_address
from tests.unit.services.utils import create_header


@integration_payment
def test_filing_court_order(client, jwt, session):
    """Assert that a valid court order filing can be posted."""
    identifier = 'BC1156638'
    b = factory_business(identifier, datetime.datetime.utcnow(), None, Business.LegalTypes.COMP.value)
    factory_business_mailing_address(b)

    filing = copy.deepcopy(COURT_ORDER_FILING_TEMPLATE)
    filing['filing']['business']['identifier'] = identifier

    rv = client.post(f'/api/v1/businesses/{identifier}/filings',
                     json=filing,
                     headers=create_header(jwt, [STAFF_ROLE], None))

    assert rv.status_code == HTTPStatus.CREATED
    assert rv.json['filing']['header']['name'] == 'courtOrder'

    filing = Filing.get_filing_by_payment_token(rv.json['filing']['header']['paymentToken'])
    assert filing
    assert filing.status == Filing.Status.PENDING.value


def test_filing_court_order_validation(client, jwt, session):
    """Assert that a court order filing can be validated."""
    identifier = 'BC1156638'
    b = factory_business(identifier, datetime.datetime.utcnow(), None, Business.LegalTypes.COMP.value)
    factory_business_mailing_address(b)

    filing = copy.deepcopy(COURT_ORDER_FILING_TEMPLATE)
    filing['filing']['business']['identifier'] = identifier
    filing['filing']['courtOrder']['fileNumber'] = ''

    rv = client.post(f'/api/v1/businesses/{identifier}/filings',
                     json=filing,
                     headers=create_header(jwt, [STAFF_ROLE], None))

    assert rv.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    filing = copy.deepcopy(COURT_ORDER_FILING_TEMPLATE)
    filing['filing']['business']['identifier'] = identifier
    filing['filing']['courtOrder']['orderDetails'] = ''
    filing['filing']['courtOrder']['effectOfOrder'] = ''
    del filing['filing']['courtOrder']['fileKey']

    rv = client.post(f'/api/v1/businesses/{identifier}/filings',
                     json=filing,
                     headers=create_header(jwt, [STAFF_ROLE], None))

    assert rv.status_code == HTTPStatus.BAD_REQUEST
    assert rv.json['errors'] == [{'error': 'Court Order is required (in orderDetails/fileKey).',
                                  'path': '/filing/courtOrder'}]

    filing = copy.deepcopy(COURT_ORDER_FILING_TEMPLATE)
    filing['filing']['business']['identifier'] = identifier
    filing['filing']['courtOrder']['effectOfOrder'] = 'invalid'
    del filing['filing']['courtOrder']['fileKey']

    rv = client.post(f'/api/v1/businesses/{identifier}/filings',
                     json=filing,
                     headers=create_header(jwt, [STAFF_ROLE], None))

    assert rv.status_code == HTTPStatus.BAD_REQUEST
    assert rv.json['errors'] == [{'error': 'Invalid effectOfOrder.', 'path': '/filing/courtOrder/effectOfOrder'}]


@integration_payment
def test_filing_registrars_notation(client, jwt, session):
    """Assert that a valid registrars notation filing can be posted."""
    identifier = 'BC1156638'
    b = factory_business(identifier, datetime.datetime.utcnow(), None, Business.LegalTypes.COMP.value)
    factory_business_mailing_address(b)

    filing = copy.deepcopy(REGISTRARS_NOTATION_FILING_TEMPLATE)
    filing['filing']['business']['identifier'] = identifier

    rv = client.post(f'/api/v1/businesses/{identifier}/filings',
                     json=filing,
                     headers=create_header(jwt, [STAFF_ROLE], None))

    assert rv.status_code == HTTPStatus.CREATED
    assert rv.json['filing']['header']['name'] == 'registrarsNotation'

    filing = Filing.get_filing_by_payment_token(rv.json['filing']['header']['paymentToken'])
    assert filing
    assert filing.status == Filing.Status.PENDING.value

    filing = copy.deepcopy(REGISTRARS_NOTATION_FILING_TEMPLATE)
    filing['filing']['business']['identifier'] = identifier
    filing['filing']['registrarsNotation']['effectOfOrder'] = ''
    filing['filing']['registrarsNotation']['fileNumber'] = ''

    rv = client.post(f'/api/v1/businesses/{identifier}/filings',
                     json=filing,
                     headers=create_header(jwt, [STAFF_ROLE], None))
    assert rv.status_code == HTTPStatus.CREATED


def test_filing_registrars_notation_validation(client, jwt, session):
    """Assert that a registrars notation filing can be validated."""
    identifier = 'BC1156638'
    b = factory_business(identifier, datetime.datetime.utcnow(), None, Business.LegalTypes.COMP.value)
    factory_business_mailing_address(b)

    filing = copy.deepcopy(REGISTRARS_NOTATION_FILING_TEMPLATE)
    filing['filing']['business']['identifier'] = identifier
    filing['filing']['registrarsNotation']['orderDetails'] = ''

    rv = client.post(f'/api/v1/businesses/{identifier}/filings',
                     json=filing,
                     headers=create_header(jwt, [STAFF_ROLE], None))
    assert rv.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    filing = copy.deepcopy(REGISTRARS_NOTATION_FILING_TEMPLATE)
    filing['filing']['business']['identifier'] = identifier
    filing['filing']['registrarsNotation']['effectOfOrder'] = 'planOfArrangement'
    filing['filing']['registrarsNotation']['fileNumber'] = ''

    rv = client.post(f'/api/v1/businesses/{identifier}/filings',
                     json=filing,
                     headers=create_header(jwt, [STAFF_ROLE], None))
    assert rv.status_code == HTTPStatus.BAD_REQUEST
    assert rv.json['errors'] == [{
        'error': 'Court Order Number is required when this filing is pursuant to a Plan of Arrangement.',
        'path': '/filing/registrarsNotation/fileNumber'}]

    filing = copy.deepcopy(REGISTRARS_NOTATION_FILING_TEMPLATE)
    filing['filing']['business']['identifier'] = identifier
    filing['filing']['registrarsNotation']['effectOfOrder'] = 'invalid'

    rv = client.post(f'/api/v1/businesses/{identifier}/filings',
                     json=filing,
                     headers=create_header(jwt, [STAFF_ROLE], None))
    assert rv.status_code == HTTPStatus.BAD_REQUEST
    assert rv.json['errors'] == [{'error': 'Invalid effectOfOrder.',
                                  'path': '/filing/registrarsNotation/effectOfOrder'}]


@integration_payment
def test_filing_registrars_order(client, jwt, session):
    """Assert that a valid registrars order filing can be posted."""
    identifier = 'BC1156638'
    b = factory_business(identifier, datetime.datetime.utcnow(), None, Business.LegalTypes.COMP.value)
    factory_business_mailing_address(b)

    filing = copy.deepcopy(REGISTRARS_ORDER_FILING_TEMPLATE)
    filing['filing']['business']['identifier'] = identifier

    rv = client.post(f'/api/v1/businesses/{identifier}/filings',
                     json=filing,
                     headers=create_header(jwt, [STAFF_ROLE], None))

    assert rv.status_code == HTTPStatus.CREATED
    assert rv.json['filing']['header']['name'] == 'registrarsOrder'

    filing = Filing.get_filing_by_payment_token(rv.json['filing']['header']['paymentToken'])
    assert filing
    assert filing.status == Filing.Status.PENDING.value

    filing = copy.deepcopy(REGISTRARS_ORDER_FILING_TEMPLATE)
    filing['filing']['business']['identifier'] = identifier
    filing['filing']['registrarsOrder']['effectOfOrder'] = ''
    filing['filing']['registrarsOrder']['fileNumber'] = ''

    rv = client.post(f'/api/v1/businesses/{identifier}/filings',
                     json=filing,
                     headers=create_header(jwt, [STAFF_ROLE], None))
    assert rv.status_code == HTTPStatus.CREATED


def test_filing_registrars_order_validation(client, jwt, session):
    """Assert that a registrars order filing can be validated."""
    identifier = 'BC1156638'
    b = factory_business(identifier, datetime.datetime.utcnow(), None, Business.LegalTypes.COMP.value)
    factory_business_mailing_address(b)

    filing = copy.deepcopy(REGISTRARS_ORDER_FILING_TEMPLATE)
    filing['filing']['business']['identifier'] = identifier
    filing['filing']['registrarsOrder']['orderDetails'] = ''

    rv = client.post(f'/api/v1/businesses/{identifier}/filings',
                     json=filing,
                     headers=create_header(jwt, [STAFF_ROLE], None))

    assert rv.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    filing = copy.deepcopy(REGISTRARS_ORDER_FILING_TEMPLATE)
    filing['filing']['business']['identifier'] = identifier
    filing['filing']['registrarsOrder']['effectOfOrder'] = 'planOfArrangement'
    filing['filing']['registrarsOrder']['fileNumber'] = ''

    rv = client.post(f'/api/v1/businesses/{identifier}/filings',
                     json=filing,
                     headers=create_header(jwt, [STAFF_ROLE], None))

    assert rv.status_code == HTTPStatus.BAD_REQUEST
    assert rv.json['errors'] == [{
        'error': 'Court Order Number is required when this filing is pursuant to a Plan of Arrangement.',
        'path': '/filing/registrarsOrder/fileNumber'}]

    filing = copy.deepcopy(REGISTRARS_ORDER_FILING_TEMPLATE)
    filing['filing']['business']['identifier'] = identifier
    filing['filing']['registrarsOrder']['effectOfOrder'] = 'invalid'

    rv = client.post(f'/api/v1/businesses/{identifier}/filings',
                     json=filing,
                     headers=create_header(jwt, [STAFF_ROLE], None))

    assert rv.status_code == HTTPStatus.BAD_REQUEST
    assert rv.json['errors'] == [{'error': 'Invalid effectOfOrder.', 'path': '/filing/registrarsOrder/effectOfOrder'}]
