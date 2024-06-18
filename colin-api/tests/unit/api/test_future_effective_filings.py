# Copyright © 2024 Province of British Columbia
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

"""Tests to assure the future effective filings end-point.

Test-Suite to ensure that the future effective filings endpoint is working as expected.
"""
import json
from datetime import datetime

from dateutil.relativedelta import relativedelta
from registry_schemas.example_data import ANNUAL_REPORT

from tests import oracle_integration


@oracle_integration
def test_get_future_effective_filings(client):
    """Assert that the future effective filings are successfully returned."""
    identifier = 'CP0001965'
    effective_date = datetime.utcnow() + relativedelta(months=5)

    headers = {'content-type': 'application/json'}
    fake_filing = ANNUAL_REPORT
    fake_filing['filing']['header']['learEffectiveDate'] = \
        f"{effective_date.strftime('%Y-%m-%d')}T15:22:39.868757+00:00"
    fake_filing['filing']['business']['identifier'] = 'CP0001965'
    fake_filing['filing']['annualReport']['annualGeneralMeetingDate'] = '2018-04-08'
    fake_filing['filing']['annualReport']['annualReportDate'] = '2018-04-08'

    rv = client.post('/api/v1/businesses/CP/CP0001965/filings/annualReport',
                     data=json.dumps(fake_filing), headers=headers)

    assert 201 == rv.status_code

    rv = client.get(f'/api/v1/businesses/CP/{identifier}/filings/future')

    assert 200 == rv.status_code
    future_effective_filings = rv.json
    assert len(future_effective_filings) > 0
