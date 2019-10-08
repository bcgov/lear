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

"""Tests to assure the historic filings end-point.

Test-Suite to ensure that the historic filings endpoint is working as expected.
"""
from tests import oracle_integration


@oracle_integration
def test_get_historic_filings(client):
    """Assert that the historic filings are successfully returned."""
    bob_date = '2019-03-08'
    identifier = 'CP0001965'

    rv = client.get(f'/api/v1/businesses/{identifier}/filings/historic')

    assert 200 == rv.status_code
    historic_filings = rv.json
    for filing in historic_filings:
        assert filing['filing']['business']['identifier'] == identifier
        assert filing['filing']['header']['date'] < bob_date
        assert filing['filing']['header']['name'] in filing['filing'].keys()
