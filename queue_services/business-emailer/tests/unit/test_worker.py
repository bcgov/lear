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
"""The Test Suites to ensure that the worker is operating correctly."""
from datetime import datetime
from unittest.mock import patch

import pytest
from simple_cloudevent import SimpleCloudEvent
from business_model.models import Business, Furnishing
from business_emailer.services.namex import NameXService
from business_account.AccountService import AccountService
from business_model.utils.legislation_datetime import LegislationDatetime

from business_emailer.email_processors import (
    ar_reminder_notification,
    correction_notification,
    filing_notification,
    name_request,
    nr_notification,
    special_resolution_notification,
)
from business_emailer.exceptions import EmailException, QueueException
from business_emailer.resources import business_emailer as worker

from tests import MockResponse
from tests.unit import (
    create_business,
    create_furnishing,
    prep_cp_special_resolution_correction_filing,
    prep_cp_special_resolution_filing,
    prep_incorp_filing,
    prep_maintenance_filing,
)

@pytest.mark.parametrize('option', [
    ('PAID'),
    ('COMPLETED'),
])
def test_process_incorp_email(app, session, mocker, option):
    """Assert that an INCORP email msg is processed correctly."""
    # setup filing + business for email
    filing = prep_incorp_filing(session, 'BC1234567', '1', option, 'BC')
    token = '1'
    # test worker
    mocker.patch(
        'business_emailer.email_processors.filing_notification.get_entity_dashboard_url',
        return_value='https://dummyurl.gov.bc.ca')
    with patch.object(AccountService, 'get_bearer_token', return_value=token):
        with patch.object(filing_notification, '_get_pdfs', return_value=[]) as mock_get_pdfs:
            with patch.object(worker, 'send_email', return_value='success') as mock_send_email:
                worker.process_email(
                    SimpleCloudEvent(
                        data={'email': {'filingId': filing.id, 'type': 'incorporationApplication', 'option': option}}
                    )
                )

                assert mock_get_pdfs.call_args[0][0] == option
                assert mock_get_pdfs.call_args[0][1] == token
                if option == 'PAID':
                    assert mock_get_pdfs.call_args[0][2]['identifier'].startswith('T')
                else:
                    assert mock_get_pdfs.call_args[0][2]['identifier'] == 'BC1234567'

                assert mock_get_pdfs.call_args[0][2]['legalType'] == 'BC'
                assert mock_get_pdfs.call_args[0][3] == filing

                if option == 'PAID':
                    assert 'comp_party@email.com' in mock_send_email.call_args[0][0]['recipients']
                    assert mock_send_email.call_args[0][0]['content']['subject'] == \
                           'Confirmation of Filing from the Business Registry'
                else:
                    assert mock_send_email.call_args[0][0]['content']['subject'] == \
                           'Incorporation Documents from the Business Registry'
                assert 'test@test.com' in mock_send_email.call_args[0][0]['recipients']
                assert mock_send_email.call_args[0][0]['content']['body']
                assert mock_send_email.call_args[0][0]['content']['attachments'] == []
                assert mock_send_email.call_args[0][1] == token


@pytest.mark.parametrize(['status', 'filing_type'], [
    ('PAID', 'annualReport'),
    ('PAID', 'changeOfAddress'),
    ('PAID', 'changeOfDirectors'),
    ('COMPLETED', 'changeOfAddress'),
    ('COMPLETED', 'changeOfDirectors')
])
def test_maintenance_notification(app, session, status, filing_type):
    """Assert that the legal name is changed."""
    # setup filing + business for email
    filing = prep_maintenance_filing(session, 'BC1234567', '1', status, filing_type)
    token = 'token'
    # test worker
    with patch.object(AccountService, 'get_bearer_token', return_value=token):
        with patch.object(filing_notification, '_get_pdfs', return_value=[]) as mock_get_pdfs:
            with patch.object(filing_notification, 'get_recipients', return_value='test@test.com') \
                as mock_get_recipients:
                with patch.object(worker, 'send_email', return_value='success') as mock_send_email:
                    worker.process_email(
                        SimpleCloudEvent(
                            data={'email': {'filingId': filing.id, 'type': f'{filing_type}', 'option': status}}
                        )
                    )

                    assert mock_get_pdfs.call_args[0][0] == status
                    assert mock_get_pdfs.call_args[0][1] == token

                    assert mock_get_pdfs.call_args[0][2]['identifier'] == 'BC1234567'
                    assert mock_get_pdfs.call_args[0][2]['legalType'] == Business.LegalTypes.BCOMP.value
                    assert mock_get_pdfs.call_args[0][2]['legalName'] == 'test business'

                    assert mock_get_pdfs.call_args[0][3] == filing
                    assert mock_get_recipients.call_args[0][0] == status
                    assert mock_get_recipients.call_args[0][1] == filing.filing_json
                    assert mock_get_recipients.call_args[0][2] == token

                    assert mock_send_email.call_args[0][0]['content']['subject']
                    assert 'test@test.com' in mock_send_email.call_args[0][0]['recipients']
                    assert mock_send_email.call_args[0][0]['content']['body']
                    assert mock_send_email.call_args[0][0]['content']['attachments'] == []
                    assert mock_send_email.call_args[0][1] == token


@pytest.mark.parametrize(['status', 'filing_type', 'identifier'], [
    ('COMPLETED', 'annualReport', 'BC1234567'),
    ('PAID', 'changeOfAddress', 'CP1234567'),
    ('PAID', 'changeOfDirectors', 'CP1234567'),
    ('COMPLETED', 'changeOfAddress', 'CP1234567'),
    ('COMPLETED', 'changeOfDirectors', 'CP1234567')
])
def test_skips_notification(app, session, status, filing_type, identifier):
    """Assert that the legal name is changed."""
    # setup filing + business for email
    filing = prep_maintenance_filing(session, identifier, '1', status, filing_type)
    token = 'token'
    # test processor
    with patch.object(AccountService, 'get_bearer_token', return_value=token):
        with patch.object(filing_notification, '_get_pdfs', return_value=[]):
            with patch.object(worker, 'send_email', return_value='success') as mock_send_email:
                worker.process_email(
                    SimpleCloudEvent(
                        data={'email': {'filingId': filing.id, 'type': f'{filing_type}', 'option': status}}
                    )
                )

                assert not mock_send_email.call_args


def test_process_mras_email(app, session):
    """Assert that an MRAS email msg is processed correctly."""
    # setup filing + business for email
    filing = prep_incorp_filing(session, 'BC1234567', '1', 'mras')
    token = '1'
    # run worker
    with patch.object(AccountService, 'get_bearer_token', return_value=token):
        with patch.object(worker, 'send_email', return_value='success') as mock_send_email:
            worker.process_email(
                SimpleCloudEvent(
                    data={'email': {'filingId': filing.id, 'type': 'incorporationApplication', 'option': 'mras'}}
                )
            )

            # check vals
            assert mock_send_email.call_args[0][0]['content']['subject'] == 'BC Business Registry Partner Information'
            assert mock_send_email.call_args[0][0]['recipients'] == 'test@test.com'
            assert mock_send_email.call_args[0][0]['content']['body']
            assert mock_send_email.call_args[0][0]['content']['attachments'] == []
            assert mock_send_email.call_args[0][1] == token


@pytest.mark.parametrize(['option', 'submitter_role'], [
    ('PAID', 'staff'),
    ('COMPLETED', None),
])
def test_process_special_resolution_email(app, session, option, submitter_role):
    """Assert that an special resolution email msg is processed correctly."""
    filing = prep_cp_special_resolution_filing('CP1234567', '1', 'CP', 'TEST', submitter_role=submitter_role)
    token = '1'
    get_pdf_function = 'get_paid_pdfs' if option == 'PAID' else 'get_completed_pdfs'
    # test worker
    with patch.object(AccountService, 'get_bearer_token', return_value=token):
        with patch.object(special_resolution_notification, get_pdf_function, return_value=[]) as mock_get_pdfs:
            with patch.object(special_resolution_notification, 'get_recipient_from_auth',
                              return_value='recipient@email.com'):
                with patch.object(special_resolution_notification, 'get_user_email_from_auth',
                                  return_value='user@email.com'):
                    with patch.object(worker, 'send_email', return_value='success') as mock_send_email:
                        worker.process_email(
                            SimpleCloudEvent(
                                data={'email': {'filingId': filing.id, 'type': 'specialResolution', 'option': option}}
                            )
                        )

                        assert mock_get_pdfs.call_args[0][0] == token
                        assert mock_get_pdfs.call_args[0][1]['identifier'] == 'CP1234567'
                        assert mock_get_pdfs.call_args[0][2] == filing

                        if option == 'PAID':
                            assert mock_send_email.call_args[0][0]['content']['subject'] == \
                                   'TEST - Confirmation of Special Resolution from the Business Registry'
                        else:
                            assert mock_send_email.call_args[0][0]['content']['subject'] == \
                                   'TEST - Special Resolution Documents from the Business Registry'
                        assert 'recipient@email.com' in mock_send_email.call_args[0][0]['recipients']
                        if submitter_role:
                            assert f'{submitter_role}@email.com' in mock_send_email.call_args[0][0]['recipients']
                        else:
                            assert 'user@email.com' in mock_send_email.call_args[0][0]['recipients']
                        assert mock_send_email.call_args[0][0]['content']['body']
                        assert mock_send_email.call_args[0][0]['content']['attachments'] == []
                        assert mock_send_email.call_args[0][1] == token


@pytest.mark.parametrize('option', [
    ('PAID'),
    ('COMPLETED'),
])
def test_process_correction_cp_sr_email(app, session, option):
    """Assert that a correction email msg is processed correctly."""
    identifier = 'CP1234567'
    original_filing = prep_cp_special_resolution_filing(identifier, '1', 'CP', 'TEST', submitter_role=None)
    token = '1'
    business = Business.find_by_identifier(identifier)
    filing = prep_cp_special_resolution_correction_filing(session, business, original_filing.id,
                                                          '1', option, 'specialResolution')
    # test worker
    with patch.object(AccountService, 'get_bearer_token', return_value=token):
        with patch.object(correction_notification, '_get_pdfs', return_value=[]):
            with patch.object(worker, 'send_email', return_value='success') as mock_send_email:
                worker.process_email(
                    SimpleCloudEvent(
                        data={'email': {'filingId': filing.id, 'type': 'correction', 'option': option}}
                    )
                )

                if option == 'PAID':
                    assert mock_send_email.call_args[0][0]['content']['subject'] == \
                           'TEST - Confirmation of correction'
                else:
                    assert mock_send_email.call_args[0][0]['content']['subject'] == \
                           'TEST - Correction Documents from the Business Registry'
                assert 'cp_sr@test.com' in mock_send_email.call_args[0][0]['recipients']
                assert mock_send_email.call_args[0][0]['content']['body']
                assert mock_send_email.call_args[0][0]['content']['attachments'] == []
                assert mock_send_email.call_args[0][1] == token


def test_process_ar_reminder_email(app, session):
    """Assert that the ar reminder notification can be processed."""
    # setup filing + business for email
    app.env = 'development'

    filing = prep_incorp_filing(session, 'BC1234567', '1', 'COMPLETED')
    business = Business.find_by_internal_id(filing.business_id)
    business.legal_type = 'BC'
    business.legal_name = 'test business'
    token = 'token'
    # test processor
    with patch.object(AccountService, 'get_bearer_token', return_value=token):
        with patch.object(ar_reminder_notification, 'get_recipient_from_auth', return_value='test@test.com'):
            with patch.object(worker, 'send_email', return_value='success') as mock_send_email:
                worker.process_email(
                    SimpleCloudEvent(
                        data={
                            'email': {
                                'businessId': filing.business_id,
                                'type': 'annualReport',
                                'option': 'reminder',
                                'arFee': '100',
                                'arYear': '2021'
                            }
                        }
                    )
                )

                call_args = mock_send_email.call_args
                assert call_args[0][0]['content']['subject'] == 'test business 2021 Annual Report Reminder'
                assert call_args[0][0]['recipients'] == 'test@test.com'
                assert call_args[0][0]['content']['body']
                assert 'Dye & Durham' not in call_args[0][0]['content']['body']
                assert call_args[0][0]['content']['attachments'] == []
                assert call_args[0][1] == token


def test_process_bn_email(app, session):
    """Assert that a BN email msg is processed correctly."""
    # setup filing + business for email
    identifier = 'BC1234567'
    filing = prep_incorp_filing(session, identifier, '1', 'bn')
    business = Business.find_by_identifier(identifier)
    # sanity check
    assert filing.id
    assert business.id
    token = '1'
    # run worker
    with patch.object(AccountService, 'get_bearer_token', return_value=token):
        with patch.object(worker, 'send_email', return_value='success') as mock_send_email:
            worker.process_email(
                SimpleCloudEvent(
                    data={'email': {'filingId': None, 'type': 'businessNumber', 'option': 'bn', 'identifier': 'BC1234567'}}
                )
            )
            # check email values
            assert 'comp_party@email.com' in mock_send_email.call_args[0][0]['recipients']
            assert 'test@test.com' in mock_send_email.call_args[0][0]['recipients']
            assert mock_send_email.call_args[0][0]['content']['subject'] == \
                   f'{business.legal_name} - Business Number Information'
            assert mock_send_email.call_args[0][0]['content']['body']
            assert mock_send_email.call_args[0][0]['content']['attachments'] == []


default_legal_name = 'TEST COMP'
default_names_array = [{'name': default_legal_name, 'state': 'NE'}]


@pytest.mark.parametrize(['option', 'nr_number', 'subject', 'expiration_date', 'refund_value',
                          'expected_legal_name', 'names'], [
                             ('before-expiry', 'NR 1234567', 'Expiring Soon', '2021-07-20T00:00:00+00:00', None,
                              'TEST2 Company Name',
                              [{'name': 'TEST Company Name', 'state': 'NE'},
                               {'name': 'TEST2 Company Name', 'state': 'APPROVED'}]),
                             ('before-expiry', 'NR 1234567', 'Expiring Soon', '2021-07-20T00:00:00+00:00', None,
                              'TEST3 Company Name',
                              [{'name': 'TEST3 Company Name', 'state': 'CONDITION'},
                               {'name': 'TEST4 Company Name', 'state': 'NE'}]),
                             ('expired', 'NR 1234567', 'Expired', None, None, 'TEST4 Company Name',
                              [{'name': 'TEST5 Company Name', 'state': 'NE'},
                               {'name': 'TEST4 Company Name', 'state': 'APPROVED'}]),
                             ('renewal', 'NR 1234567', 'Confirmation of Renewal', '2021-07-20T00:00:00+00:00', None,
                              None, default_names_array),
                             (
                             'upgrade', 'NR 1234567', 'Confirmation of Upgrade', None, None, None, default_names_array),
                             ('refund', 'NR 1234567', 'Refund request confirmation', None, '123.45', None,
                              default_names_array)
                         ])
def test_nr_notification(app, session, option, nr_number, subject, expiration_date, refund_value,
                         expected_legal_name, names):
    """Assert that the nr notification can be processed."""
    nr_json = {
        'expirationDate': expiration_date,
        'names': names,
        'legalType': 'BC',
        'applicants': {
            'emailAddress': 'test@test.com'
        }
    }
    nr_response = MockResponse(nr_json, 200)
    token = 'token'

    # run worker
    with patch.object(AccountService, 'get_bearer_token', return_value=token):
        with patch.object(NameXService, 'query_nr_number', return_value=nr_response) \
            as mock_query_nr_number:
            with patch.object(worker, 'send_email', return_value='success') as mock_send_email:
                worker.process_email(
                    SimpleCloudEvent(
                        id='123456789',
                        type='bc.registry.names.request',
                        source=f'/requests/{nr_number}',
                        data={
                            'identifier': nr_number,
                            'request': {
                                'nrNum': nr_number,
                                'option': option,
                                'refundValue': refund_value
                            }
                        }
                    )
                )

                call_args = mock_send_email.call_args
                assert call_args[0][0]['content']['subject'] == f'{nr_number} - {subject}'
                assert call_args[0][0]['recipients'] == 'test@test.com'
                assert call_args[0][0]['content']['body']
                if option == nr_notification.Option.REFUND.value:
                    assert f'${refund_value} CAD' in call_args[0][0]['content']['body']
                assert call_args[0][0]['content']['attachments'] == []
                assert mock_query_nr_number.call_args[0][0] == nr_number
                assert call_args[0][1] == token

                if option == nr_notification.Option.BEFORE_EXPIRY.value:
                    assert nr_number in call_args[0][0]['content']['body']
                    assert expected_legal_name in call_args[0][0]['content']['body']
                    exp_date = datetime.fromisoformat(expiration_date)
                    exp_date_tz = LegislationDatetime.as_legislation_timezone(exp_date)
                    assert_expiration_date = LegislationDatetime.format_as_report_string(exp_date_tz)
                    assert assert_expiration_date in call_args[0][0]['content']['body']

                if option == nr_notification.Option.EXPIRED.value:
                    assert nr_number in call_args[0][0]['content']['body']
                    assert expected_legal_name in call_args[0][0]['content']['body']


def test_nr_receipt_notification(app, session):
    """Assert that the nr payment notification can be processed."""
    nr_number = 'NR 1234567'
    email_address = 'test@test.com'
    nr_id = 12345
    nr_json = {
        'applicants': {
            'emailAddress': email_address
        },
        'id': nr_id
    }
    nr_response = MockResponse(nr_json, 200)
    token = 'token'
    payment_token = '1234'
    pdfs = ['test']

    # run worker
    with patch.object(AccountService, 'get_bearer_token', return_value=token):
        with patch.object(NameXService, 'query_nr_number', return_value=nr_response) \
            as mock_query_nr_number:
            with patch.object(name_request, 'get_nr_bearer_token', return_value=token):
                with patch.object(name_request, '_get_pdfs', return_value=pdfs) as mock_pdf:
                    with patch.object(worker, 'send_email', return_value='success') as mock_send_email:
                        worker.process_email(
                            SimpleCloudEvent(
                                id='123456789',
                                type='bc.registry.names.request',
                                source=f'/requests/{nr_number}',
                                data={
                                    'identifier': nr_number,
                                    'request': {
                                        'header': {'nrNum': nr_number},
                                        'paymentToken': payment_token,
                                        'statusCode': 'DRAFT'  # not used
                                    }
                                }
                            )
                        )

                        assert mock_pdf.call_args[0][0] == nr_id
                        assert mock_pdf.call_args[0][1] == payment_token
                        assert mock_query_nr_number.call_args[0][0] == nr_number
                        call_args = mock_send_email.call_args
                        assert call_args[0][0]['content']['subject'] == f'{nr_number} - Receipt from Corporate Registry'
                        assert call_args[0][0]['recipients'] == email_address
                        assert call_args[0][0]['content']['body']
                        assert call_args[0][0]['content']['attachments'] == pdfs
                        assert call_args[0][1] == token


@pytest.mark.parametrize('email_msg', [
    ({}),
    ({
        'recipients': '',
        'requestBy': 'test@test.ca',
        'content': {
            'subject': 'test',
            'body': 'test',
            'attachments': []
        }}),
    ({
        'recipients': '',
        'requestBy': 'test@test.ca',
        'content': {}}),
    ({
        'recipients': '',
        'requestBy': 'test@test.ca',
        'content': {
            'subject': 'test',
            'body': {},
            'attachments': []
        }}),
    ({
        'requestBy': 'test@test.ca',
        'content': {
            'subject': 'test',
            'body': 'test',
            'attachments': []
        }}),
    ({
        'recipients': 'test@test.ca',
        'requestBy': 'test@test.ca'}),
    ({
        'recipients': 'test@test.ca',
        'requestBy': 'test@test.ca',
        'content': {
            'subject': 'test',
            'attachments': []
        }})
])
def test_send_email_with_incomplete_payload(app, session, email_msg):
    """Assert that the email not have body can not be processed."""
    # TEST
    with pytest.raises(QueueException) as excinfo:
        worker.send_email(email_msg, None)

    assert 'Unsuccessful sending email' in str(excinfo)


@pytest.mark.parametrize(['test_name', 'exception', 'furnishing_name', 'expected_furnishing_status'], [
    ('Will be failed with invalid furnishing_name', None, 'INVALID_NAME', 'QUEUED'),
    ('Will be processed with valid furnishing_name', None, 'DISSOLUTION_COMMENCEMENT_NO_AR', 'PROCESSED'),
    ('Will be processed with valid furnishing_name', None, 'DISSOLUTION_COMMENCEMENT_NO_TR', 'PROCESSED'),
    ('Will be processed with valid furnishing_name', None, 'DISSOLUTION_COMMENCEMENT_NO_AR_XPRO', 'PROCESSED'),
    ('Will be processed with valid furnishing_name', None, 'DISSOLUTION_COMMENCEMENT_NO_TR_XPRO', 'PROCESSED'),
    ('When email is failed', EmailException, 'DISSOLUTION_COMMENCEMENT_NO_AR', 'FAILED')
])
def test_involuntary_dissolution_stage_1_notification(app, db, session, mocker, test_name,
                                                      exception, furnishing_name, expected_furnishing_status):
    """Assert that the stage 1 notifications can be processed."""
    business_identifier = 'BC1234567'
    business = create_business(business_identifier, 'BC', 'Test Business')
    furnishing = create_furnishing(session, business=business)

    mocker.patch(
        'business_emailer.email_processors.involuntary_dissolution_stage_1_notification.get_jurisdictions',
        return_value=[])
    mocker.patch(
        'business_emailer.email_processors.involuntary_dissolution_stage_1_notification._get_pdfs',
        return_value=[]
    )
    message_payload = SimpleCloudEvent(
        id='16fd2111-8baf-433b-82eb-8c7fada84ccc',
        type='bc.registry.dissolution',
        source='furnishingsJob',
        data={
            'furnishing': {
                'type': 'INVOLUNTARY_DISSOLUTION',
                'furnishingId': furnishing.id,
                'furnishingName': furnishing_name
            }
        }
    )

    # run worker
    with patch.object(AccountService, 'get_bearer_token', return_value=1):
        with patch.object(worker, 'send_email', return_value='success', side_effect=exception) as mock_send_email:
            session.expunge_all()
            if exception:
                with pytest.raises(exception):
                    worker.process_email(message_payload)
            else:
                worker.process_email(message_payload)

            call_args = mock_send_email.call_args
            if furnishing_name == 'INVALID_NAME':
                assert call_args is None
            else:
                assert call_args[0][0]['content']['subject'] == f'Attention {business_identifier} - Test Business'
                assert call_args[0][0]['recipients'] == 'test@test.com'
                assert call_args[0][0]['content']['body']

            updated_furnishing = Furnishing.find_by_id(furnishing.id)
            assert updated_furnishing.status.name == expected_furnishing_status
            if expected_furnishing_status == 'FAILED':
                assert updated_furnishing.notes == 'Failure to send email'
