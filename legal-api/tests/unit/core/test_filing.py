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
from registry_schemas.example_data import ANNUAL_REPORT

from legal_api.core import Filing
from tests.unit.models import factory_business, factory_completed_filing


def test_filing_raw():
    """Assert that raw is empty on a new filing."""
    filing = Filing()

    assert not filing.raw


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

    assert filing.json == filing_submission
    assert filing.storage.status == Filing.Status.DRAFT.value


def test_filing_json_completed(session):
    """Assert that the json field gets the completed filing correctly."""
    identifier = 'CP7654321'
    business = factory_business(identifier)
    factory_completed_filing(business, ANNUAL_REPORT)

    filings = Filing().get_filings_by_status(business.id, [Filing.Status.COMPLETED.value])
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
