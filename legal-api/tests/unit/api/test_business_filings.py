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
from datetime import datetime, date
from http import HTTPStatus

import datedelta
from dateutil.parser import parse
from flask import current_app
from registry_schemas.example_data import ANNUAL_REPORT, CHANGE_OF_ADDRESS, CHANGE_OF_DIRECTORS, FILING_HEADER

from legal_api.resources.business.business_filings import Filing, ListFilingResource
from legal_api.services.authz import BASIC_USER, STAFF_ROLE
from tests import integration_payment
from tests.unit.services.utils import create_header
from tests.unit.models import factory_business_mailing_address, factory_business, factory_completed_filing, factory_filing  # noqa:E501,I001


def test_get_all_business_filings_only_one_in_ledger(session, client, jwt):
    """Assert that the business info can be received in a valid JSONSchema format."""
    import copy
    identifier = 'CP7654321'
    b = factory_business(identifier)
    filings = factory_filing(b, ANNUAL_REPORT)

    ar = copy.deepcopy(ANNUAL_REPORT)
    ar['filing']['header']['filingId'] = filings.id
    ar['filing']['header']['colinId'] = None

    print('test_get_all_business_filings - filing:', filings)

    rv = client.get(f'/api/v1/businesses/{identifier}/filings',
                    headers=create_header(jwt, [STAFF_ROLE], identifier))

    assert rv.status_code == HTTPStatus.OK
    assert len(rv.json.get('filings')) == 0  # The endpoint will return only completed filings


def test_get_all_business_filings_multi_in_ledger(session, client, jwt):
    """Assert that the business info can be received in a valid JSONSchema format."""
    import copy
    from tests import add_years

    ar = copy.deepcopy(ANNUAL_REPORT)
    identifier = 'CP7654321'

    # create business
    b = factory_business(identifier)

    # add 3 filings, add a year onto the AGM date
    for i in range(0, 3):
        ar['filing']['annualReport']['annualGeneralMeetingDate'] = \
            datetime.date(add_years(datetime(2001, 8, 5, 7, 7, 58, 272362), i)).isoformat()
        factory_filing(b, ar)

    rv = client.get(f'/api/v1/businesses/{identifier}/filings',
                    headers=create_header(jwt, [STAFF_ROLE], identifier))

    assert rv.status_code == HTTPStatus.OK
    assert len(rv.json.get('filings')) == 0


def test_get_one_business_filing_by_id(session, client, jwt):
    """Assert that the business info cannot be received in a valid JSONSchema format."""
    import copy
    identifier = 'CP7654321'
    b = factory_business(identifier)
    filings = factory_filing(b, ANNUAL_REPORT)
    ar = copy.deepcopy(ANNUAL_REPORT)
    ar['filing']['header']['filingId'] = filings.id
    ar['filing']['header']['colinId'] = None

    rv = client.get(f'/api/v1/businesses/{identifier}/filings/{filings.id}',
                    headers=create_header(jwt, [STAFF_ROLE], identifier))

    assert rv.status_code == HTTPStatus.OK
    assert rv.json['filing']['annualReport'] == ar['filing']['annualReport']
    assert rv.json['filing']['business'] == ar['filing']['business']


def test_get_404_when_business_invalid_filing_id(session, client, jwt):
    """Assert that the business info cannot be received in a valid JSONSchema format."""
    identifier = 'CP7654321'
    b = factory_business(identifier)
    filings = factory_filing(b, ANNUAL_REPORT)

    print('test_get_one_business_filing - filing:', filings)

    print(f'/api/v1/businesses/{identifier}/filings/{filings.id}')

    rv = client.get(f'/api/v1/businesses/{identifier}/filings/{filings.id + 1}',
                    headers=create_header(jwt, [STAFF_ROLE], identifier))

    assert rv.status_code == HTTPStatus.NOT_FOUND
    assert rv.json == {'message': f'{identifier} no filings found'}


def test_get_404_filing_with_invalid_business(session, client, jwt):
    """Assert that a filing cannot be created against non-existent business."""
    identifier = 'CP7654321'
    filings_id = 1

    rv = client.get(f'/api/v1/businesses/{identifier}/filings/{filings_id}',
                    headers=create_header(jwt, [STAFF_ROLE], identifier))

    assert rv.status_code == HTTPStatus.NOT_FOUND
    assert rv.json == {'message': f'{identifier} not found'}


def test_post_fail_if_given_filing_id(session, client, jwt):
    """Assert that a filing cannot be created against a given filing_id."""
    identifier = 'CP7654321'
    b = factory_business(identifier)
    filings = factory_filing(b, ANNUAL_REPORT)

    rv = client.post(f'/api/v1/businesses/{identifier}/filings/{filings.id}',
                     json=ANNUAL_REPORT,
                     headers=create_header(jwt, [STAFF_ROLE], identifier)
                     )

    assert rv.status_code == HTTPStatus.FORBIDDEN
    assert rv.json['errors'][0] == {'message':
                                    f'Illegal to attempt to create a duplicate filing for {identifier}.'}


def test_post_filing_no_business(session, client, jwt):
    """Assert that a filing cannot be created against non-existent business."""
    identifier = 'CP7654321'

    rv = client.post(f'/api/v1/businesses/{identifier}/filings',
                     json=ANNUAL_REPORT,
                     headers=create_header(jwt, [STAFF_ROLE], identifier)
                     )

    assert rv.status_code == HTTPStatus.BAD_REQUEST
    assert rv.json['errors'][0] == {'error': 'A valid business and filing are required.'}


def test_post_empty_annual_report_to_a_business(session, client, jwt):
    """Assert that an empty filing cannot be posted."""
    identifier = 'CP7654321'
    factory_business(identifier)

    rv = client.post(f'/api/v1/businesses/{identifier}/filings',
                     json=None,
                     headers=create_header(jwt, [STAFF_ROLE], identifier)
                     )

    assert rv.status_code == HTTPStatus.BAD_REQUEST
    assert rv.json['errors'][0] == {'message': f'No filing json data in body of post for {identifier}.'}


def test_post_authorized_draft_ar(session, client, jwt):
    """Assert that a unpaid filing can be posted."""
    identifier = 'CP7654321'
    factory_business(identifier)

    rv = client.post(f'/api/v1/businesses/{identifier}/filings?draft=true',
                     json=ANNUAL_REPORT,
                     headers=create_header(jwt, [STAFF_ROLE], identifier)
                     )

    assert rv.status_code == HTTPStatus.CREATED


def test_post_not_authorized_draft_ar(session, client, jwt):
    """Assert that a unpaid filing can be posted."""
    identifier = 'CP7654321'
    factory_business(identifier)

    rv = client.post(f'/api/v1/businesses/{identifier}/filings?draft=true',
                     json=ANNUAL_REPORT,
                     headers=create_header(jwt, [BASIC_USER], 'WRONGUSER')
                     )

    assert rv.status_code == HTTPStatus.UNAUTHORIZED


def test_post_draft_ar(session, client, jwt):
    """Assert that a unpaid filing can be posted."""
    identifier = 'CP7654321'
    factory_business(identifier)

    rv = client.post(f'/api/v1/businesses/{identifier}/filings?draft=true',
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
                     founding_date=(datetime.utcnow() - datedelta.YEAR)
                     )
    ar = copy.deepcopy(ANNUAL_REPORT)
    ar['filing']['annualReport']['annualReportDate'] = datetime.utcnow().date().isoformat()
    ar['filing']['annualReport']['annualGeneralMeetingDate'] = datetime.utcnow().date().isoformat()

    rv = client.post(f'/api/v1/businesses/{identifier}/filings?only_validate=true',
                     json=ar,
                     headers=create_header(jwt, [STAFF_ROLE], identifier)
                     )

    assert rv.status_code == HTTPStatus.OK
    assert not rv.json.get('errors')


def test_post_validate_ar_using_last_ar_date(session, client, jwt):
    """Assert that a unpaid filing can be posted."""
    identifier = 'CP7654321'
    factory_business(identifier,
                     last_ar_date=(datetime.utcnow() - datedelta.YEAR),  # last ar date = last year
                     founding_date=(datetime.utcnow() - datedelta.YEAR - datedelta.YEAR)  # founding date = 2 years ago
                     )
    ar = copy.deepcopy(ANNUAL_REPORT)
    ar['filing']['annualReport']['annualReportDate'] = datetime.utcnow().date().isoformat()
    ar['filing']['annualReport']['annualGeneralMeetingDate'] = datetime.utcnow().date().isoformat()

    rv = client.post(f'/api/v1/businesses/{identifier}/filings?only_validate=true',
                     json=ar,
                     headers=create_header(jwt, [STAFF_ROLE], identifier)
                     )

    assert rv.status_code == HTTPStatus.OK
    assert not rv.json.get('errors')


def test_post_only_validate_error_ar(session, client, jwt):
    """Assert that a unpaid filing can be posted."""
    import copy
    identifier = 'CP7654321'
    factory_business(identifier)

    ar = copy.deepcopy(ANNUAL_REPORT)
    ar['filing']['header'].pop('name')

    rv = client.post(f'/api/v1/businesses/{identifier}/filings?only_validate=true',
                     json=ar,
                     headers=create_header(jwt, [STAFF_ROLE], identifier)
                     )

    assert rv.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert rv.json.get('errors')
    assert rv.json['errors'][0]['error'] == "'name' is a required property"


def test_post_only_validate_ar_invalid_routing_slip(session, client, jwt):
    """Assert that a unpaid filing can be posted."""
    import copy
    identifier = 'CP7654321'
    factory_business(identifier)

    ar = copy.deepcopy(ANNUAL_REPORT)
    ar['filing']['header']['routingSlipNumber'] = '1231313329988888'

    rv = client.post(f'/api/v1/businesses/{identifier}/filings?only_validate=true',
                     json=ar,
                     headers=create_header(jwt, [STAFF_ROLE], identifier)
                     )

    assert rv.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert rv.json.get('errors')
    assert rv.json['errors'][0]['error'] == "'1231313329988888' is too long"

    ar['filing']['header']['routingSlipNumber'] = '1'

    rv = client.post(f'/api/v1/businesses/{identifier}/filings?only_validate=true',
                     json=ar,
                     headers=create_header(jwt, [STAFF_ROLE], identifier)
                     )

    assert rv.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert rv.json.get('errors')


def test_post_validate_ar_valid_routing_slip(session, client, jwt):
    """Assert that a unpaid filing can be posted."""
    identifier = 'CP7654321'
    factory_business(identifier,
                     last_ar_date=(datetime.utcnow() - datedelta.YEAR),  # last ar date = last year
                     founding_date=(datetime.utcnow() - datedelta.YEAR - datedelta.YEAR)  # founding date = 2 years ago
                     )
    ar = copy.deepcopy(ANNUAL_REPORT)
    ar['filing']['annualReport']['annualReportDate'] = datetime.utcnow().date().isoformat()
    ar['filing']['annualReport']['annualGeneralMeetingDate'] = datetime.utcnow().date().isoformat()
    ar['filing']['header']['routingSlipNumber'] = '123131332'

    rv = client.post(f'/api/v1/businesses/{identifier}/filings?only_validate=true',
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

    rv = client.post(f'/api/v1/businesses/{identifier}/filings',
                     json=ar,
                     headers=create_header(jwt, [STAFF_ROLE], identifier)
                     )

    # check return
    assert rv.status_code == HTTPStatus.CREATED
    assert not rv.json.get('errors')
    assert rv.json['filing']['header']['filingId']
    assert rv.json['filing']['header']['paymentToken']
    assert rv.json['filing']['header']['paymentToken'] == '153'

    # check stored filing
    filing = Filing.get_filing_by_payment_token(rv.json['filing']['header']['paymentToken'])
    assert filing
    assert filing.status == Filing.Status.PENDING.value


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

    rv = client.post(f'/api/v1/businesses/{identifier}/filings',
                     json=ar,
                     headers=create_header(jwt, [STAFF_ROLE], identifier)
                     )

    # check return
    assert rv.status_code == HTTPStatus.CREATED
    assert not rv.json.get('errors')
    assert rv.json['filing']['header']['filingId']
    assert rv.json['filing']['header']['paymentToken']
    assert rv.json['filing']['header']['paymentToken'] == '153'

    # check stored filing
    filing = Filing.get_filing_by_payment_token(rv.json['filing']['header']['paymentToken'])
    assert filing
    assert filing.status == Filing.Status.PENDING.value


def test_post_valid_ar_failed_payment(monkeypatch, session, client, jwt):
    """Assert that a unpaid filing can be posted."""
    identifier = 'CP7654321'
    business = factory_business(identifier,
                                founding_date=(datetime.utcnow() - datedelta.YEAR)
                                )
    factory_business_mailing_address(business)
    ar = copy.deepcopy(ANNUAL_REPORT)
    ar['filing']['annualReport']['annualReportDate'] = datetime.utcnow().date().isoformat()
    ar['filing']['annualReport']['annualGeneralMeetingDate'] = datetime.utcnow().date().isoformat()

    old_svc = current_app.config.get('PAYMENT_SVC_URL')
    current_app.config['PAYMENT_SVC_URL'] = 'http://nowhere.localdomain'

    rv = client.post(f'/api/v1/businesses/{identifier}/filings',
                     json=ar,
                     headers=create_header(jwt, [STAFF_ROLE], identifier)
                     )

    current_app.config['PAYMENT_SVC_URL'] = old_svc
    assert rv.status_code == HTTPStatus.PAYMENT_REQUIRED
    assert rv.json.get('errors')
    assert rv.json['errors'][0]['message'] == 'unable to create invoice for payment.'


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

    rv = client.put(f'/api/v1/businesses/{identifier}/filings/{filings.id}',
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


def test_update_draft_ar(session, client, jwt):
    """Assert that a valid filing can be updated to a paid filing."""
    import copy
    identifier = 'CP7654321'
    b = factory_business(identifier)
    filings = factory_filing(b, ANNUAL_REPORT)
    ar = copy.deepcopy(ANNUAL_REPORT)

    rv = client.put(f'/api/v1/businesses/{identifier}/filings/{filings.id}?draft=true',
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

    rv = client.delete(f'/api/v1/businesses/{identifier}/filings/{filings.id}',
                       headers=headers
                       )

    assert rv.status_code == HTTPStatus.OK


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

    rv = client.delete(f'/api/v1/businesses/{identifier}/filings/{filings.id}',
                       headers=create_header(jwt, [STAFF_ROLE], identifier)
                       )

    assert rv.status_code == HTTPStatus.FORBIDDEN


def test_delete_filing_no_filing_id(client, jwt):
    """Assert that a call without an ID is a BAD_REQUEST."""
    identifier = 'CP7654321'
    rv = client.delete(f'/api/v1/businesses/{identifier}/filings',
                       headers=create_header(jwt, [STAFF_ROLE], identifier)
                       )

    assert rv.status_code == HTTPStatus.BAD_REQUEST


def test_delete_filing_missing_filing_id(client, jwt):
    """Assert that trying to delete a non-existant filing returns a 404."""
    identifier = 'CP7654321'
    rv = client.delete(f'/api/v1/businesses/{identifier}/filings/bob',
                       headers=create_header(jwt, [STAFF_ROLE], identifier)
                       )

    assert rv.status_code == HTTPStatus.NOT_FOUND


def test_delete_filing_not_authorized(session, client, jwt):
    """Assert that a users is authorized to delete a filing."""
    identifier = 'CP7654321'
    b = factory_business(identifier)
    filings = factory_filing(b, ANNUAL_REPORT)
    headers = create_header(jwt, ['BAD ROLE'], identifier)

    rv = client.delete(f'/api/v1/businesses/{identifier}/filings/{filings.id}', headers=headers)

    assert rv.status_code == HTTPStatus.UNAUTHORIZED


def test_update_block_ar_update_to_a_paid_filing(session, client, jwt):
    """Assert that a valid filing can NOT be updated once it has been paid."""
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

    rv = client.put(f'/api/v1/businesses/{identifier}/filings/{filings.id}',
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
                                founding_date=(datetime.utcnow() - datedelta.YEAR)
                                )
    factory_business_mailing_address(business)
    ar = copy.deepcopy(ANNUAL_REPORT)
    ar['filing']['annualReport']['annualReportDate'] = datetime.utcnow().date().isoformat()
    ar['filing']['annualReport']['annualGeneralMeetingDate'] = datetime.utcnow().date().isoformat()

    filings = factory_filing(business, ar)

    rv = client.put(f'/api/v1/businesses/{identifier}/filings/{filings.id+1}',
                    json=ar,
                    headers=create_header(jwt, [STAFF_ROLE], identifier)
                    )

    assert rv.status_code == HTTPStatus.NOT_FOUND
    assert rv.json['errors'][0] == {'message': f'{identifier} no filings found'}


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

    rv = client.put(f'/api/v1/businesses/{identifier}/filings/{filings.id+1}',
                    json=ar,
                    headers=create_header(jwt, [STAFF_ROLE], identifier)
                    )

    assert rv.status_code == HTTPStatus.BAD_REQUEST
    assert rv.json['errors'][0] == {'error': 'A valid business and filing are required.'}


def test_update_ar_with_missing_json_body_fails(session, client, jwt):
    """Assert that updating a filing with no JSON body fails."""
    identifier = 'CP7654321'
    b = factory_business(identifier)
    filings = factory_filing(b, ANNUAL_REPORT)

    rv = client.put(f'/api/v1/businesses/{identifier}/filings/{filings.id+1}',
                    json=None,
                    headers=create_header(jwt, [STAFF_ROLE], identifier)
                    )

    assert rv.status_code == HTTPStatus.BAD_REQUEST
    assert rv.json['errors'][0] == {'message': f'No filing json data in body of post for {identifier}.'}


def test_file_ar_no_agm_coop(session, client, jwt):
    """Assert that filing AR as COOP with no AGM date fails."""
    identifier = 'CP7654399'
    b = factory_business(identifier, (datetime.utcnow() - datedelta.YEAR))
    factory_business_mailing_address(b)
    ar = copy.deepcopy(ANNUAL_REPORT)
    ar['filing']['annualReport']['annualReportDate'] = datetime.utcnow().date().isoformat()
    ar['filing']['header']['date'] = datetime.utcnow().date().isoformat()
    ar['filing']['annualReport']['annualGeneralMeetingDate'] = None
    ar['filing']['header']['date'] = datetime.utcnow().date().isoformat()
    rv = client.post(f'/api/v1/businesses/{identifier}/filings',
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
    ar['filing']['header']['date'] = datetime.utcnow().date().isoformat()
    rv = client.post(f'/api/v1/businesses/{identifier}/filings',
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


def test_get_correct_fee_codes(session):
    """Assert fee codes are properly assigned to filings before sending to payment."""
    import copy

    # set filings
    ar = ANNUAL_REPORT
    coa = copy.deepcopy(FILING_HEADER)
    coa['filing']['header']['name'] = 'changeOfAddress'
    coa['filing']['changeOfAddress'] = CHANGE_OF_ADDRESS
    cod = copy.deepcopy(FILING_HEADER)
    cod['filing']['header']['name'] = 'changeOfDirectors'
    cod['filing']['changeOfDirectors'] = copy.deepcopy(CHANGE_OF_DIRECTORS)
    assert len(cod['filing']['changeOfDirectors']['directors']) > 1
    cod['filing']['changeOfDirectors']['directors'][0]['actions'] = ['ceased', 'nameChanged']
    cod['filing']['changeOfDirectors']['directors'][1]['actions'] = ['nameChanged', 'addressChanged']
    free_cod = copy.deepcopy(FILING_HEADER)
    free_cod['filing']['header']['name'] = 'changeOfDirectors'
    free_cod['filing']['changeOfDirectors'] = copy.deepcopy(CHANGE_OF_DIRECTORS)
    for director in free_cod['filing']['changeOfDirectors']['directors']:
        if not all(action in ['nameChanged', 'addressChanged'] for action in director.get('actions', [])):
            director['actions'] = ['nameChanged', 'addressChanged']

    # get fee codes
    ar_fee_code = ListFilingResource._get_filing_types(ar)[0]['filingTypeCode']
    coa_fee_code = ListFilingResource._get_filing_types(coa)[0]['filingTypeCode']
    cod_fee_code = ListFilingResource._get_filing_types(cod)[0]['filingTypeCode']
    free_cod_fee_code = ListFilingResource._get_filing_types(free_cod)[0]['filingTypeCode']

    # test fee codes
    assert ar_fee_code == Filing.FILINGS['annualReport'].get('code')
    assert coa_fee_code == Filing.FILINGS['changeOfAddress'].get('code')
    assert cod_fee_code == Filing.FILINGS['changeOfDirectors'].get('code')
    assert free_cod_fee_code == 'OTFDR'


def test_coa_future_effective(session, client, jwt):
    """Assert future effective changes do not affect Coops, and that
    BCORP change of address if future-effective."""
     
    import pytz

    coa = copy.deepcopy(FILING_HEADER)
    coa['filing']['header']['name'] = 'changeOfAddress'
    coa['filing']['changeOfAddress'] = CHANGE_OF_ADDRESS
    coa['filing']['changeOfAddress']['deliveryAddress']['addressCountry'] = 'CA'
    coa['filing']['changeOfAddress']['mailingAddress']['addressCountry'] = 'CA'
    identifier = 'CP1234567'
    b = factory_business(identifier, (datetime.utcnow()-datedelta.YEAR), None)
    factory_business_mailing_address(b)
    rv = client.post(f'/api/v1/businesses/{identifier}/filings',
                 json=coa,
                 headers=create_header(jwt, [STAFF_ROLE], identifier)
                 )
    assert rv.status_code == HTTPStatus.CREATED
    assert 'effectiveDate' not in rv.json['filing']['header']

    identifier = 'CP7654321'
    bc = factory_business(identifier, (datetime.utcnow()-datedelta.YEAR), None, 'BC')
    factory_business_mailing_address(bc)
    coa['filing']['business']['identifier'] = identifier

    rv = client.post(f'/api/v1/businesses/{identifier}/filings',
                 json=coa,
                 headers=create_header(jwt, [STAFF_ROLE], identifier)
                 )
    
    assert rv.status_code == HTTPStatus.CREATED
    assert 'effectiveDate' in rv.json['filing']['header']
    effective_date = parse(rv.json['filing']['header']['effectiveDate'])
    valid_date = datetime.combine \
        (date.today() + datedelta.datedelta(days=1), \
            datetime.min.time())
    assert effective_date == pytz.UTC.localize(valid_date)
