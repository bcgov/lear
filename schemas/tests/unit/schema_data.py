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
"""Test Suite data used across many tests.

Test array used in multiple pytests, and several filings that can be used in tests.
"""
# testdata pattern is ({str: environment}, {expected return value})
TEST_SCHEMAS_DATA = [
    ('address.json'),
    ('annual_report.json'),
    ('business.json'),
    ('change_of_address.json'),
    ('filing.json'),
    ('directors.json'),
    ('change_of_directors.json'),
    ('task.json'),
    ('todo.json'),
]

TEST_AR = {
    'filing': {
        'header': {
            'name': 'annualReport',
            'date': '2019-04-08',
            'filingId': 1
        },
        'business': {
            'cacheId': 1,
            'foundingDate': '2007-04-08',
            'identifier': 'CP1234567',
            'lastLedgerTimestamp': '2019-04-15T20:05:49.068272+00:00',
            'lastPreBobFilingTimestamp': '2019-04-15T20:05:49.068272+00:00',
            'legalName': 'legal name - CP1234567'
        },
        'annualReport': {
            'annualGeneralMeetingDate': '2019-04-08',
            'certifiedBy': 'full name',
            'email': 'no_one@never.get'
        }
    }
}
