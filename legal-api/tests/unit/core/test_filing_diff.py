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
from legal_api.utils.datetime import datetime, date

import datedelta
from legal_api.core import Filing
from tests.unit.models import (  # noqa:E501,I001
    factory_business,
    factory_business_mailing_address,
    factory_completed_filing,
    factory_filing,
)


def test_no_filing_diff():
    """Assert that the filing diff works correctly."""
    filing = Filing()

    diff = filing.diff()

    assert not diff


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
    from legal_api.core.utils import diff_dict, diff_list_with_id

    diff = diff_dict(CORRECTION_FILING_JSON, MINIMAL_FILING_JSON, ignore_keys=['header', 'business', 'correction'], diff_list=diff_list_with_id)

    ld = [d.json for d in diff] if diff else None

    assert ld == [{
        'newValue': 'Be it resolved, and now it is.',
        'oldValue': 'Be it resolved, that it is resolved to be resolved.',
        'path': '/filing/specialResolution/resolution'}]


def test_no_filing_diff():
    """Assert that the filing diff works correctly."""
    import copy
    identifier = 'CP1234567'
    business = factory_business(identifier,
                                founding_date=(datetime.utcnow() - datedelta.YEAR)
                                )
    factory_business_mailing_address(business)
    json1 = copy.deepcopy(MINIMAL_FILING_JSON)
    original_filing = factory_completed_filing(business, json1)

    try:
        json1 = copy.deepcopy(MINIMAL_FILING_JSON)
        filing = Filing()
        filing.storage
        filing._json = json1
        filing._status = Filing.Status.COMPLETED.value
        filing.save()
    except Exception as err:
        print(err)

    diff = filing.diff()

    assert not diff
