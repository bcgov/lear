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
"""Tests to assure the Filing Diff is working as expected."""
import copy

import datedelta

from legal_api.core import Filing
from legal_api.utils.datetime import datetime
from tests.unit.models import (  # noqa:E501,I001
    factory_business,
    factory_business_mailing_address,
    factory_completed_filing,
)


MINIMAL_FILING_JSON = {'filing': {
    'header': {
        'name': 'specialResolution',
        'date': '2019-04-08'
    },
    'business': {
        'foundingDate': '2019-04-08T00:00:00+00:00',
        'identifier': 'CP1234567',
        'legalName': 'legal name - CP1234567',
        'legalType': 'CP'
    },
    'specialResolution': {
        'resolution': 'Be it resolved, that it is resolved to be resolved.'
    }
}}

CORRECTION_FILING_JSON = {'filing': {
    'header': {
        'name': 'correction',
        'date': '2019-04-08'
    },
    'business': {
        'foundingDate': '2019-04-08T00:00:00+00:00',
        'identifier': 'CP1234567',
        'legalName': 'legal name - CP1234567',
        'legalType': 'CP'
    },
    'specialResolution': {
        'resolution': 'Be it resolved, and now it is.'
    },
    'correction': {
        'correctedFilingId': 1,
        'correctedFilingType': 'specialResolution',
        'correctedFilingDate': '2020-04-08',
        'comment': """Sample Comment"""
    }
}}


def test_filing_json_diff():
    """Assert the diff works on a sample filing structure."""
    from legal_api.core.utils import diff_dict, diff_list

    diff = diff_dict(CORRECTION_FILING_JSON,
                     MINIMAL_FILING_JSON,
                     ignore_keys=['header', 'business', 'correction'],
                     diff_list=diff_list)

    ld = [d.json for d in diff] if diff else None

    assert ld == [{
        'newValue': 'Be it resolved, and now it is.',
        'oldValue': 'Be it resolved, that it is resolved to be resolved.',
        'path': '/filing/specialResolution/resolution'}]


def test_diff_of_stored_completed_filings(session):
    """Assert that the filing diff works correctly."""
    identifier = 'CP1234567'
    business = factory_business(identifier,
                                founding_date=(datetime.utcnow() - datedelta.YEAR)
                                )
    factory_business_mailing_address(business)
    json1 = copy.deepcopy(MINIMAL_FILING_JSON)
    original_filing = factory_completed_filing(business, json1)

    json2 = copy.deepcopy(CORRECTION_FILING_JSON)
    json2['filing']['correction']['correctedFilingId'] = str(original_filing.id)
    correction_filing = factory_completed_filing(business, json2)

    filing = Filing.find_by_id(correction_filing.id)
    filing_json = filing.json

    assert filing_json
    assert filing_json['filing']['correction']['diff'] == [
        {
            'newValue': 'Be it resolved, and now it is.',
            'oldValue': 'Be it resolved, that it is resolved to be resolved.',
            'path': '/filing/specialResolution/resolution'
        }]
