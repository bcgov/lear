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
from registry_schemas.example_data import ANNUAL_REPORT

from business_model.exceptions import BusinessException
from business_model.models import Filing
from tests import EPOCH_DATETIME
from tests.conftest import not_raises


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
    filing.filing_json = ANNUAL_REPORT
    assert not filing.locked
    filing.save()
    assert filing.locked


def test_changing_uninvoiced_saved_filing_is_unlocked(session):
    """Assert that saving an un-invoiced filing is still unlocked."""
    # should succeed
    filing = Filing()
    filing.filing_date = EPOCH_DATETIME
    filing.filing_json = ANNUAL_REPORT
    assert not filing.locked
    filing.save()
    assert not filing.locked


@pytest.mark.parametrize('test_name, deletion_lock', [
    ('with_deletion_lock', True),
    ('without_deletion_lock', False),
])
def test_filing_deletion_lock(session, test_name, deletion_lock):
    """Assert that a filing can be deleted."""
    filing = Filing()
    filing.deletion_locked = deletion_lock
    filing.save()

    if deletion_lock:
        assert filing.locked
        with pytest.raises(BusinessException):
            filing.delete()
    else:
        assert not filing.locked
        with not_raises(BusinessException):
            filing.delete()
