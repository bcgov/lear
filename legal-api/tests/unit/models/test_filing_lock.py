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

"""Tests to assure the Filing Lock Model.

Test-Suite to ensure that the file locking is working as expected.
"""
import pytest

from legal_api.exceptions import BusinessException
from legal_api.models import Filing
from tests import EPOCH_DATETIME
from tests.unit.models import AR_FILING


def test_unsaved_filing_lock(session):
    """Assert that an unsaved filing, even with an invoice, is not locked."""
    # not locked
    filing = Filing()
    filing.payment_token = 'payment_token'
    assert not filing.locked


def test_saved_uninvoiced_filing_locked(session):
    """Assert that un-invoiced filing is not locked, even if it is saved."""
    # not locked
    filing = Filing()
    filing.save()
    filing.payment_token = 'payment_token'
    assert not filing.locked


def test_invoiced_filing_is_locked(session):
    """Assert a filing is locked once invoiced and saved."""
    # locked
    filing = Filing()
    filing.payment_token = 'payment_token'
    filing.save()
    assert filing.locked


def test_invoiced_filing_raises_exception_when_changed(session):
    """Assert a BusinessException is raised if a locked filing is altered."""
    # locked
    filing = Filing()
    filing.payment_token = 'payment_token'
    filing.save()
    with pytest.raises(BusinessException):
        filing.payment_token = 'should raise exception'


def test_changing_unsaved_filing_is_unlocked(session):
    """Assert an unlocked, but saved filing, can be changed."""
    # should succeed
    filing = Filing()
    filing.payment_token = 'payment_token'
    filing.filing_date = EPOCH_DATETIME
    filing.filing_json = AR_FILING
    assert not filing.locked
    filing.save()
    assert filing.locked


def test_changing_uninvoiced_saved_filing_is_unlocked(session):
    """Assert that saving an un-invoiced filing is still unlocked."""
    # should succeed
    filing = Filing()
    filing.filing_date = EPOCH_DATETIME
    filing.filing_json = AR_FILING
    assert not filing.locked
    filing.save()
    assert not filing.locked
