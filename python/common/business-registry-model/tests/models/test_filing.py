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

"""Tests to assure the Filing Model.

Test-Suite to ensure that the Business Model is working as expected.
"""
import copy
import datetime
import json
from http import HTTPStatus

import datedelta
import pytest
import registry_schemas
from flask import current_app
from freezegun import freeze_time
from registry_schemas.example_data import (
    ALTERATION_FILING_TEMPLATE,
    ANNUAL_REPORT,
    CHANGE_OF_DIRECTORS,
    CORRECTION_AR,
    COURT_ORDER,
    FILING_HEADER,
    SPECIAL_RESOLUTION,
)

from business_model.exceptions import BusinessException
from business_model.models import Business, Filing, User
from business_model.models.db import VersioningProxy
from tests import EPOCH_DATETIME
from tests.conftest import not_raises
from tests.models import (
    factory_business,
    factory_business_mailing_address,
    factory_completed_filing,
    factory_filing,
    factory_user,
)


def test_minimal_filing_json(session):
    """Assert that a minimal filing can be created."""
    b = factory_business('CP1234567')

    data = {'filing': 'not a real filing, fail validation'}

    filing = Filing()
    filing.business_id = b.id
    filing.filing_date = datetime.datetime.utcnow()
    filing.filing_data = json.dumps(data)
    filing.save()

    assert filing.source == Filing.Source.LEAR.value
    assert filing.id is not None


def test_filing_orm_delete_allowed_for_in_progress_filing(session):
    """Assert that attempting to delete a filing will raise a BusinessException."""
    from business_model.exceptions import BusinessException

    b = factory_business('CP1234567')

    filing = Filing()
    filing.business_id = b.id
    filing.filing_date = datetime.datetime.utcnow()
    filing.filing_json = ANNUAL_REPORT
    filing.save()

    with not_raises(BusinessException):
        session.delete(filing)
        session.commit()


def test_filing_orm_delete_blocked_if_invoiced(session):
    """Assert that attempting to delete a filing will raise a BusinessException."""
    from business_model.exceptions import BusinessException

    b = factory_business('CP1234567')

    filing = Filing()
    filing.business_id = b.id
    filing.filing_date = datetime.datetime.utcnow()
    filing.filing_json = ANNUAL_REPORT
    filing.payment_token = 'a token'
    filing.save()

    with pytest.raises(BusinessException) as excinfo:
        session.delete(filing)
        session.commit()

    assert excinfo.value.status_code == HTTPStatus.FORBIDDEN
    assert excinfo.value.error == 'Deletion not allowed.'


def test_filing_orm_delete_blocked_if_completed(session):
    """Assert that attempting to delete a filing will raise a BusinessException."""
    from business_model.exceptions import BusinessException

    transaction_id = VersioningProxy.get_transaction_id(session())

    b = factory_business('CP1234567')

    filing = Filing()
    filing.business_id = b.id
    filing.filing_date = datetime.datetime.utcnow()
    filing.filing_json = ANNUAL_REPORT
    filing.payment_token = 'a token'
    filing.payment_completion_date = datetime.datetime.utcnow()
    filing.transaction_id = transaction_id
    filing.save()

    with pytest.raises(BusinessException) as excinfo:
        session.delete(filing)
        session.commit()

    assert excinfo.value.status_code == HTTPStatus.FORBIDDEN
    assert excinfo.value.error == 'Deletion not allowed.'


def test_filing_json(session):
    """Assert that an AR filing can be saved."""
    import copy
    b = factory_business('CP1234567')
    filing = factory_filing(b, ANNUAL_REPORT)

    ar = copy.deepcopy(ANNUAL_REPORT)
    ar['filing']['header']['filingId'] = filing.id
    ar['filing']['header']['colinIds'] = []

    assert filing.id
    assert filing.json['filing']['business'] == ANNUAL_REPORT['filing']['business']
    assert filing.json['filing']['annualReport'] == ANNUAL_REPORT['filing']['annualReport']


def test_filing_missing_name(session):
    """Assert that an AR filing can be saved."""
    import copy
    identifier = 'CP7654321'
    b = factory_business(identifier)
    ar = copy.deepcopy(ANNUAL_REPORT)
    ar['filing']['header'].pop('name', None)

    with pytest.raises(BusinessException) as excinfo:
        factory_filing(b, ar)

    assert excinfo.value.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert excinfo.value.error == 'No filings found.'


def test_filing_dump_json(session):
    """Assert the filing json serialization works correctly."""
    import copy
    identifier = 'CP7654321'
    b = factory_business(identifier)

    # Check base JSON
    filings = factory_filing(b, ANNUAL_REPORT)

    assert filings.json['filing']['business'] == ANNUAL_REPORT['filing']['business']
    assert filings.json['filing']['annualReport'] == ANNUAL_REPORT['filing']['annualReport']

    # Check payment token
    ar = copy.deepcopy(ANNUAL_REPORT)
    token = 'token'
    ar['filing']['header']['paymentToken'] = token
    filings = factory_filing(b, ar)
    assert filings.json['filing']['header']['paymentToken'] == token

    # check submitter
    u = User()
    u.username = 'submitter'
    u.save()
    ar = copy.deepcopy(ANNUAL_REPORT)
    filings = factory_filing(b, ar)
    filings.submitter_id = u.id
    filings.save()
    assert filings.json['filing']['header']['submitter'] == u.username

    # check Exception
    ar = copy.deepcopy(ANNUAL_REPORT)
    filings = factory_filing(b, ar)
    filings.save()
    filings.submitter_id = -1  # some bogus id to throw an error
    with pytest.raises(KeyError):
        filings.json()


def test_filing_save_to_session(session):
    """Assert that the filing is saved to the session but not committed."""
    from sqlalchemy.orm.session import Session
    # b = factory_business('CP1234567')
    # filing = factory_filing(b, ANNUAL_REPORT)

    filing = Filing()

    assert not session.new
    assert not Session.object_session(filing)

    filing.save_to_session()

    assert filing.id is None
    assert session.new
    assert Session.object_session(filing)


def test_add_json_after_payment(session):
    """Assert that the json can be added in the same session that a paymentToken was applied."""
    filing = Filing()
    filing.filing_date = EPOCH_DATETIME

    # sanity check starting value
    assert not filing.status

    filing.payment_token = 'payment token'
    filing.filing_json = ANNUAL_REPORT

    assert filing.json
    assert filing.status == Filing.Status.PENDING.value


def test_add_json_and_payment_after_saved_filing(session):
    """Assert that the json can be added in the same session that a paymentToken was applied."""
    filing = Filing()
    filing.filing_date = EPOCH_DATETIME
    filing.save()

    # sanity check starting value
    assert filing.status == Filing.Status.DRAFT.value

    filing.payment_token = 'payment token'
    filing.filing_json = ANNUAL_REPORT

    assert filing.json
    assert filing.status == Filing.Status.PENDING.value


def test_add_payment_completion_date_after_payment(session):
    """Assert that the json can be added in the same session that a paymentToken was applied."""
    filing = Filing()
    filing.filing_date = EPOCH_DATETIME
    filing.save()

    filing.payment_token = 'payment token'
    filing.filing_json = ANNUAL_REPORT

    # sanity check starting position
    assert filing.json
    assert filing.status == Filing.Status.PENDING.value

    filing.payment_completion_date = EPOCH_DATETIME
    filing.save()
    assert filing.status == Filing.Status.PAID.value


def test_add_invalid_json_after_payment(session):
    """Assert that a filing_json has to be valid if a payment token has been set."""
    import copy
    filing = Filing()
    filing.payment_token = 'payment token'

    ar = copy.deepcopy(ANNUAL_REPORT)
    ar['filing']['header'].pop('date', None)

    with pytest.raises(BusinessException) as excinfo:
        filing.filing_json = ar

    assert excinfo.value.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


def test_updating_payment_token_fails(session):
    """Assert that a payment token cannot be updated."""
    filing = Filing()
    filing.payment_token = 'payment token'
    filing.save()

    with pytest.raises(BusinessException) as excinfo:
        filing.payment_token = 'payment token'

    assert excinfo.value.status_code == HTTPStatus.FORBIDDEN


def test_updating_filing_with_payment_token(session):
    """Assert that a payment token can be applied to an existing filing."""
    from tests.conftest import not_raises
    filing = Filing()
    filing.save()

    with not_raises(BusinessException):
        filing.payment_token = 'payment token'


def test_get_legal_filings():
    """Assert that the legal_filings member returns valid JSON Legal Filing segments."""
    filing = Filing()

    assert not filing.legal_filings()

    filing.filing_json = ANNUAL_REPORT
    legal_filings = filing.legal_filings()

    assert legal_filings
    assert 'annualReport' in legal_filings[0].keys()


def test_get_filing_by_payment_token(session):
    """Assert that a filing can be retrieved by a unique payment token."""
    payment_token = '1000'
    filing = Filing()
    filing.filing_json = ANNUAL_REPORT
    filing.payment_token = payment_token
    filing.save()

    rv = Filing.get_filing_by_payment_token(payment_token)

    assert rv
    assert rv.payment_token == payment_token


def test_get_filings_by_status(session):
    """Assert that a filing can be retrieved by status."""
    transaction_id = VersioningProxy.get_transaction_id(session())
    business = factory_business('CP1234567')
    payment_token = '1000'
    filing = Filing()
    filing.business_id = business.id
    filing.filing_json = ANNUAL_REPORT
    filing.payment_token = payment_token
    filing.transaction_id = transaction_id
    filing.payment_completion_date = datetime.datetime.utcnow()
    filing.save()

    rv = Filing.get_filings_by_status(business.id, [Filing.Status.COMPLETED.value])

    assert rv
    assert rv[0].status == Filing.Status.COMPLETED.value


def test_get_filings_by_status__default_order(session):
    """Assert that a filing can be retrieved.

    by status and is returned in the default order.
    default order is submission_date, and then effective_date.
    """
    # setup
    base_filing = copy.deepcopy(FILING_HEADER)
    base_filing['specialResolution'] = SPECIAL_RESOLUTION
    transaction_id = VersioningProxy.get_transaction_id(session())
    business = factory_business('CP1234567')

    completion_date = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)

    # setup - create multiple filings on the same day & time
    filing_ids = []
    file_counter = -1
    with freeze_time(completion_date):
        for i in range(5):
            payment_token = str(i)
            effective_date = f'200{i}-04-15T00:00:00+00:00'

            base_filing['filing']['header']['effectiveDate'] = effective_date
            filing = Filing()
            filing._filing_date = completion_date
            filing.business_id = business.id
            filing.filing_json = base_filing
            filing.effective_date = datetime.datetime.fromisoformat(effective_date)
            filing.payment_token = payment_token
            filing.transaction_id = transaction_id
            filing.payment_completion_date = completion_date
            filing.save()

            filing_ids.append(filing.id)
            file_counter += 1

    # test
    rv = Filing.get_filings_by_status(business.id, [Filing.Status.COMPLETED.value])

    # check
    assert rv
    # filings should be in newest to oldest effective date order
    for filing in rv:
        assert filing.id == filing_ids[file_counter]
        file_counter -= 1


def test_get_most_recent_filing_by_legal_type_in_json(session):
    """Assert that the most recent legal filing can be retrieved."""
    business = factory_business('CP1234567')
    transaction_id = VersioningProxy.get_transaction_id(session())

    for i in range(1, 5):
        effective_date = f'200{i}-07-01T00:00:00+00:00'
        completion_date = datetime.datetime.fromisoformat(effective_date)

        base_filing = copy.deepcopy(ANNUAL_REPORT)
        cod = copy.deepcopy(CHANGE_OF_DIRECTORS)
        base_filing['filing']['changeOfDirectors'] = cod

        base_filing['filing']['header']['effectiveDate'] = effective_date
        filing = Filing()
        filing._filing_date = completion_date
        filing.business_id = business.id
        filing.filing_json = base_filing
        filing.effective_date = datetime.datetime.fromisoformat(effective_date)
        filing.payment_token = 'token'
        filing.transaction_id = transaction_id
        filing.payment_completion_date = completion_date
        filing.save()

    f = Filing.get_most_recent_legal_filing(business.id, 'changeOfDirectors')
    assert f.effective_date == datetime.datetime.fromisoformat(effective_date)
    assert f.filing_type == 'annualReport'
    assert f.id == filing.id


def test_get_most_recent_filing_by_legal_type_db_field(session):
    """Assert that the most recent legal filing can be retrieved.

    Create 3 filings, find the 2 one by the type only.
    """
    business = factory_business('CP1234567')
    transaction_id = VersioningProxy.get_transaction_id(session())

    # filing 1
    effective_date = '2001-07-01T00:00:00+00:00'
    completion_date = datetime.datetime.fromisoformat(effective_date)
    base_filing = copy.deepcopy(ANNUAL_REPORT)
    base_filing['filing']['header']['effectiveDate'] = effective_date
    filing1 = Filing()
    filing1._filing_date = completion_date
    filing1.business_id = business.id
    filing1.filing_json = base_filing
    filing1.effective_date = datetime.datetime.fromisoformat(effective_date)
    filing1.payment_token = 'token'
    filing1.transaction_id = transaction_id
    filing1.payment_completion_date = completion_date
    filing1.save()

    # filing 2 <- target
    effective_date = '2002-07-01T00:00:00+00:00'
    completion_date = datetime.datetime.fromisoformat(effective_date)
    base_filing = copy.deepcopy(FILING_HEADER)
    base_filing['filing']['header']['effectiveDate'] = effective_date
    base_filing['filing']['header']['name'] = 'changeOfDirectors'
    base_filing['filing']['header']['availableOnPaperOnly'] = True
    filing2 = Filing()
    filing2._filing_date = completion_date
    filing2.business_id = business.id
    filing2.filing_json = base_filing
    filing2.effective_date = datetime.datetime.fromisoformat(effective_date)
    filing2.payment_token = 'token'
    filing2.transaction_id = transaction_id
    filing2.payment_completion_date = completion_date
    filing2.save()

    # filing 3
    effective_date = '2003-07-01T00:00:00+00:00'
    completion_date = datetime.datetime.fromisoformat(effective_date)
    base_filing = copy.deepcopy(ANNUAL_REPORT)
    base_filing['filing']['header']['effectiveDate'] = effective_date
    filing3 = Filing()
    filing3._filing_date = completion_date
    filing3.business_id = business.id
    filing3.filing_json = base_filing
    filing3.effective_date = datetime.datetime.fromisoformat(effective_date)
    filing3.payment_token = 'token'
    filing3.transaction_id = transaction_id
    filing3.payment_completion_date = completion_date
    filing3.save()

    f = Filing.get_most_recent_legal_filing(business.id, 'changeOfDirectors')
    assert f.filing_type == 'changeOfDirectors'
    assert f.id == filing2.id


# testdata pattern is ({str: environment}, {expected return value})
TEST_FILING_GO_LIVE_DATE = [
    ('filing returned', 10, 'rv is not None', Filing.Status.COMPLETED.value),
    ('no filing returned', -10, 'rv == []', None),
]


@pytest.mark.parametrize('test_type,days,expected,status', TEST_FILING_GO_LIVE_DATE)
def test_get_filings_by_status_before_go_live_date(session, test_type, days, expected, status):
    """Assert that a filing can be retrieved by status."""
    import copy
    transaction_id = VersioningProxy.get_transaction_id(session())
    business = factory_business('CP1234567')
    payment_token = '1000'
    ar = copy.deepcopy(ANNUAL_REPORT)

    conf_go_live_date = current_app.config.get('GO_LIVE_DATE', '2019-08-12')

    go_live_date = datetime.date.fromisoformat(conf_go_live_date)
    filing_date = go_live_date + datetime.timedelta(days=days)

    filing = Filing()
    filing.filing_date = filing_date
    filing.business_id = business.id
    filing.filing_json = ar
    filing.payment_token = payment_token
    filing.transaction_id = transaction_id
    filing.payment_completion_date = datetime.datetime.utcnow()
    filing.save()

    rv = Filing.get_filings_by_status(business.id, [Filing.Status.COMPLETED.value], go_live_date)

    assert eval(expected)  # pylint: disable=eval-used; useful for parameterized tests
    if rv:
        assert rv[0].status == status


def test_get_completed_filings_for_colin(session):
    """Assert that the get_completed_filings_for_colin returns completed filings with no colin ids set."""
    from business_model.models import Filing
    from business_model.models.colin_event_id import ColinEventId
    from tests.models import factory_completed_filing
    # setup
    identifier = 'CP0045467'
    b = factory_business(identifier)
    filing = factory_completed_filing(b, ANNUAL_REPORT)
    assert filing.status == Filing.Status.COMPLETED.value
    colin_event_id = ColinEventId()
    colin_event_id.colin_event_id = 1234678987
    filing.colin_event_ids.append(colin_event_id)
    filing.save()
    filings = Filing.get_completed_filings_for_colin()

    # test method
    # assert doesn't return completed filing with colin_event_ids set
    assert len(filings) == 0
    # assert returns completed filings with colin_event_id not set
    filing.colin_event_ids.clear()
    filing.save()
    filings = Filing.get_completed_filings_for_colin()
    assert len(filings) == 1
    assert filing.id == filings[0].json['filing']['header']['filingId']
    assert filings[0].json['filing']['header']['colinIds'] == []
    # assert doesn't return non completed filings
    filing.transaction_id = None
    filing.save()
    assert filing.status != Filing.Status.COMPLETED.value
    filings = Filing.get_completed_filings_for_colin()
    assert len(filings) == 0


def test_get_most_recent_filing(session):
    """Assert that the most recent completed filing of a specified type is returned."""
    from business_model.models import Filing
    from tests.models import factory_completed_filing
    # setup
    identifier = 'CP7654321'
    b = factory_business(identifier)
    ar = copy.deepcopy(ANNUAL_REPORT)
    base_ar_date = datetime.datetime(2001, 8, 5, 7, 7, 58, 272362, tzinfo=datetime.timezone.utc)
    filings = []
    for i in range(5):
        filing_date = base_ar_date + datedelta.datedelta(years=i)
        ar['filing']['annualReport']['annualGeneralMeetingDate'] = \
            filing_date.date().isoformat()
        filing = factory_completed_filing(b, ar, filing_date)
        filings.append(filing)
    # test
    filing = Filing.get_most_recent_filing(b.id, Filing.FILINGS['annualReport']['name'])

    # assert that we get the last filing
    assert filings[4] == filing


def test_save_filing_with_colin_id(session):
    """Assert that saving a filing from the coops-updater-job user is set to paid and source is colin."""
    from business_model.models import Filing
    # setup
    filing = Filing()
    filing.filing_json = ANNUAL_REPORT
    filing.source = Filing.Source.COLIN.value
    filing.save()

    # test
    assert filing.source == Filing.Source.COLIN.value
    assert filing.status == Filing.Status.PAID.value


def test_save_filing_colin_only(session):
    """Assert that the in colin only flag is retrieved and saved."""
    from business_model.models import Filing
    # setup
    filing = Filing()
    filing.filing_json = FILING_HEADER
    filing.save()

    # test
    assert filing.json['filing']['header']['inColinOnly'] is False
    assert filing.colin_only == False


def test_uncorrected_filing(session):
    """Assert that a uncorrected filing is unaffected."""
    from business_model.models import Filing
    # setup
    filing = Filing()
    filing.filing_json = ANNUAL_REPORT
    filing.save()

    # test
    assert filing.json['filing']['header']['isCorrected'] is False


def test_is_corrected_filing(session):
    """Assert that corrected filing has the isCorrected flag set.

    Assert linkage is set from parent to child and otherway.
    """
    from business_model.models import Filing
    # setup
    filing1 = Filing()
    filing1.filing_json = ANNUAL_REPORT
    filing1.save()

    b = factory_business('CP1234567')
    filing2 = factory_completed_filing(b, CORRECTION_AR)

    filing1.parent_filing = filing2
    filing1.save()

    # test
    assert filing1.json['filing']['header']['isCorrected'] is True
    assert filing1.json['filing']['header']['isCorrectionPending'] is False
    assert filing2.json['filing']['header']['affectedFilings'] is not None

    assert filing2.json['filing']['header']['affectedFilings'][0] == filing1.id


def test_is_pending_correction_filing(session):
    """Assert that a filing has the isPendingCorrection flag set if the correction is pending approval.

    Assert linkage is set from parent to child and otherway.
    """
    from business_model.models import Filing
    # setup
    filing1 = Filing()
    filing1.filing_json = ANNUAL_REPORT
    filing1.save()

    b = factory_business('CP1234567')
    filing2 = factory_completed_filing(b, CORRECTION_AR)
    filing2._status = 'PENDING_CORRECTION'
    filing2.skip_status_listener = True
    filing2.save()

    filing1.parent_filing = filing2
    filing1.save()

    # test
    assert filing1.json['filing']['header']['isCorrected'] is False
    assert filing1.json['filing']['header']['isCorrectionPending'] is True
    assert filing2.json['filing']['header']['affectedFilings'] is not None

    assert filing2.json['filing']['header']['affectedFilings'][0] == filing1.id


def test_linked_not_correction(session):
    """Assert that if a filing has a parent that is not a correction, the isCorrected flag is not set."""
    from business_model.models import Filing
    # setup
    filing1 = Filing()
    filing1.filing_json = ANNUAL_REPORT
    filing1.save()

    f = copy.deepcopy(FILING_HEADER)
    f['filing']['changeOfDirectors'] = CHANGE_OF_DIRECTORS
    filing2 = Filing()
    filing2.filing_json = f
    filing2.save()

    filing1.parent_filing = filing2
    filing1.save()

    # test
    assert filing1.json['filing']['header']['isCorrected'] is False
    assert filing2.json['filing']['header']['affectedFilings'] is not None


def test_alteration_filing_with_court_order(session):
    """Assert that an alteration filing with court order can be created."""
    identifier = 'BC1156638'
    b = factory_business(identifier, datetime.datetime.utcnow(), None, Business.LegalTypes.COMP.value)
    factory_business_mailing_address(b)
    filing = factory_filing(b, ALTERATION_FILING_TEMPLATE)
    filing.court_order_file_number = COURT_ORDER['fileNumber']
    filing.court_order_date = COURT_ORDER['orderDate']
    filing.court_order_effect_of_order = COURT_ORDER['effectOfOrder']
    filing.filing_json = ALTERATION_FILING_TEMPLATE
    filing.save()
    assert filing.id is not None
    assert filing.json['filing']['alteration']['courtOrder']['fileNumber'] == COURT_ORDER['fileNumber']
    assert filing.json['filing']['alteration']['courtOrder']['orderDate'] == COURT_ORDER['orderDate']
    assert filing.json['filing']['alteration']['courtOrder']['effectOfOrder'] == COURT_ORDER['effectOfOrder']

    assert registry_schemas.validate(filing.json, 'alteration')


@pytest.mark.parametrize('invalid_court_order', [
    {
        'fileNumber': '123456789012345678901',  # long fileNumber
        'orderDate': '2021-01-30T09:56:01+01:00',
        'effectOfOrder': 'planOfArrangement'
    },
    {
        'fileNumber': 'Valid file number',
        'orderDate': 'a2021-01-30T09:56:01',  # Invalid date
        'effectOfOrder': 'planOfArrangement'
    },
    {
        'fileNumber': 'Valid File Number',
        'orderDate': '2021-01-30T09:56:01+01:00',
        'effectOfOrder': ('a' * 501)  # long effectOfOrder
    }
])
def test_validate_invalid_court_orders(session, invalid_court_order):
    """Assert not valid court orders."""
    identifier = 'BC1156677'
    b = factory_business(identifier, datetime.datetime.utcnow(), None, Business.LegalTypes.COMP.value)
    factory_business_mailing_address(b)
    filing = factory_filing(b, ALTERATION_FILING_TEMPLATE)
    filing.court_order_file_number = invalid_court_order['fileNumber']
    filing.court_order_date = invalid_court_order['orderDate']
    filing.court_order_effect_of_order = invalid_court_order['effectOfOrder']

    # TODO: rescope the error after upgraing frameworks
    # with pytest.raises(DataError, Exception, ProgrammingError) as excinfo:
    with pytest.raises(Exception) as excinfo:
        filing.save()

    assert excinfo

# @pytest.mark.parametrize('test_name, json1, json2, expected', TEST_JSON_DIFF)


def test_submitter_info(session):
    user = factory_user('idir/staff-person')
    filing = Filing()
    filing.submitter_roles = 'STAFF'
    filing.submitter_id = user.id
    filing.save()

    assert filing.id
