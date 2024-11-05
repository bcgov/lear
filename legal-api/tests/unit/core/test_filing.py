# Copyright © 2020 Province of British Columbia
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

"""Tests to assure the Filing Domain is working as expected."""
import datedelta
import pytest
from freezegun import freeze_time
from registry_schemas.example_data import ANNUAL_REPORT

from legal_api.core import Filing
from legal_api.models.user import UserRoles
from tests.unit.models import factory_business, factory_completed_filing, factory_user
from legal_api.utils.datetime import datetime, timezone


def test_filing_raw():
    """Assert that raw is empty on a new filing."""
    filing = Filing()

    assert not filing.raw


def test_filing_type(session):
    """Assert that filing_type is empty on a new filing."""
    identifier = 'CP7654321'
    business = factory_business(identifier)
    factory_completed_filing(business, ANNUAL_REPORT)

    filings = Filing.get_filings_by_status(business.id, [Filing.Status.DRAFT.value, Filing.Status.COMPLETED.value])
    assert filings[0].filing_type == 'annualReport'


def test_filing_json_draft(session):
    """Assert that the json field gets the draft filing correctly."""
    filing = Filing()
    filing_submission = {
        'filing': {
            'header': {
                'name': 'specialResolution',
                'date': '2019-04-08'
            },
            'specialResolution': {
                'resolution': 'Year challenge is hitting oppo for the win.'
            }}}

    filing.json = filing_submission
    filing.save()

    assert filing.json['filing']['header']['name'] == filing_submission['filing']['header']['name']
    assert filing.json['filing']['specialResolution'] == filing_submission['filing']['specialResolution']

def test_technical_filing_json_draft(session):
    """Assert that the technical json field gets the draft filing correctly.

    technical filings should bypass all checks.

    danger Will Robinson
    
    This builds on test_filing_json_draft, so if that is broken, this wont work either.
    """
    # setup
    filing = Filing()
    filing_submission = {
        'filing': {
            'header': {
                'name': 'specialResolution',
                'date': '2019-04-08'
            },
            'specialResolution': {
                'resolution': 'Year challenge is hitting oppo for the win.'
            }}}

    filing.json = filing_submission
    filing.save()
    # sanity check
    assert filing.json['filing']['header']['name'] == filing_submission['filing']['header']['name']
    assert filing.json['filing']['specialResolution'] == filing_submission['filing']['specialResolution']

    # test
    non_compliant_json  = {
        'dope': 'this would fail any validator, but can bypass everything.',
        'dogsLife': "do the humans really know what's best?"}
    filing.storage.tech_correction_json = non_compliant_json
    # over ride the state and skip state setting listeners for this test
    filing._storage.skip_status_listener = True
    filing._storage._status = Filing.Status.PENDING.value
    filing.save()

    # validate
    assert filing.json == non_compliant_json


def test_filing_json_completed(session):
    """Assert that the json field gets the completed filing correctly."""
    identifier = 'CP7654321'
    business = factory_business(identifier)
    factory_completed_filing(business, ANNUAL_REPORT)

    filings = Filing.get_filings_by_status(business.id, [Filing.Status.COMPLETED.value])
    filing = filings[0]

    assert filing.json
    assert filing.json['filing']['header']['status'] == Filing.Status.COMPLETED.value
    assert filing.json['filing']['annualReport']
    assert 'directors' in filing.json['filing']['annualReport']
    assert 'offices' in filing.json['filing']['annualReport']


def test_filing_save(session):
    """Assert that the core filing is saved to the backing store."""
    filing = Filing()
    filing_submission = {
        'filing': {
            'header': {
                'name': 'specialResolution',
                'date': '2019-04-08'
            },
            'specialResolution': {
                'resolution': 'Year challenge is hitting oppo for the win.'
            }}}

    filing.json = filing_submission

    assert not filing.id

    filing.save()

    assert filing.id


def test_is_future_effective(session):
    """Assert that is_future_effective property works as expected."""
    filing = Filing()
    filing_type = 'bogus type'
    filing.storage.filing_json = {'filing': {'header': {'name': filing_type}}}
    filing.storage._payment_token = '12345'
    filing.storage._filing_type = filing_type

    now = datetime(2019, 7, 1)
    with freeze_time(now):
        filing.storage.effective_date = now
        assert not filing.is_future_effective

        filing.storage.payment_completion_date = now
        assert not filing.is_future_effective


def test_set_effective(session):
    """Assert that the core filing is saved to the backing store."""
    now = datetime(2021, 9, 17, 7, 36, 43, 903557, tzinfo=timezone.utc)

    with freeze_time(now):

        payment_date  = now + datedelta.DAY
        legal_type = 'SP'

        filing = Filing()
        filing_type = 'annualReport'
        filing.json = ANNUAL_REPORT
        filing.save()

        filing.storage._payment_token = '12345'
        filing.storage._filing_type = filing_type
        filing.storage.effective_date = now
        filing._storage.skip_status_listener = True
        filing._storage.payment_completion_date = payment_date
        filing._storage.save()

        filing.storage.set_processed(legal_type)

        # assert that the effective date is now, instead of the payment date
        assert filing._storage.effective_date
        assert filing._storage.effective_date.replace(tzinfo=None) == now.replace(tzinfo=None)
        assert not filing.is_future_effective

        future_date = now + datedelta.DAY
        alt_payment_date  = now
        filing._storage.skip_status_listener = True
        filing._storage.payment_completion_date = alt_payment_date
        filing._storage.save()

        filing.storage.set_processed(legal_type)

        # assert that the effective date is the future date
        assert filing._storage.effective_date
        assert filing._storage.effective_date.replace(tzinfo=None) == future_date.replace(tzinfo=None)
        assert filing.is_future_effective

        past_date = now - datedelta.DAY
        filing.storage.effective_date = past_date
        filing._storage.skip_status_listener = True
        filing._storage.payment_completion_date = payment_date
        filing._storage.save()

        legal_type = 'CP'
        filing.storage.set_processed(legal_type)

        # assert that the effective date is unchanged by payment date
        assert filing._storage.effective_date
        assert filing._storage.effective_date == past_date
        assert filing._storage.effective_date.replace(tzinfo=None) != payment_date.replace(tzinfo=None)
        assert not filing.is_future_effective

