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

from legal_api.core import Filing


def test_filing_raw():
    """Assert that raw is empty on a new filing."""
    filing = Filing()

    assert not filing.raw


def test_filing_json():
    """Assert that the json field gets set correctly."""
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
    assert filing.json == filing_submission


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
