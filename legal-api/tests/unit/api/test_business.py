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

"""Tests to assure the business end-point.

Test-Suite to ensure that the /businesses endpoint is working as expected.
"""
from datetime import datetime

from tests.utilities.schema_assertions import assert_valid_schema


def factory_business_model(legal_name,
                           identifier,
                           founding_date,
                           last_remote_ledger_timestamp,
                           fiscal_year_end_date=None,
                           tax_id=None,
                           dissolution_date=None):
    """Return a valid Business object stamped with the supplied designation."""
    from legal_api.models import Business as BusinessModel
    b = BusinessModel(legal_name=legal_name,
                      identifier=identifier,
                      founding_date=founding_date,
                      last_remote_ledger_timestamp=last_remote_ledger_timestamp,
                      fiscal_year_end_date=fiscal_year_end_date,
                      dissolution_date=dissolution_date,
                      tax_id=tax_id
                      )
    b.save()
    return b


def test_get_business_info(session, client):
    """Assert that the business info can be received in a valid JSONSchema format."""
    factory_business_model(legal_name='legal_name',
                           identifier='CP7654321',
                           founding_date=datetime.utcfromtimestamp(0),
                           last_remote_ledger_timestamp=datetime.utcfromtimestamp(0),
                           fiscal_year_end_date=None,
                           tax_id=None,
                           dissolution_date=None)
    rv = client.get('/api/v1/businesses/CP7654321')

    print('business json', rv.json)

    assert rv.json['business']['identifier'] == 'CP7654321'

    print('valid schema?', assert_valid_schema(rv.json, 'business.json'))

    assert assert_valid_schema(rv.json, 'business.json')


def test_get_business_info_dissolution(session, client):
    """Assert that the business info cannot be received in a valid JSONSchema format."""
    factory_business_model(legal_name='legal_name',
                           identifier='CP1234567',
                           founding_date=datetime.utcfromtimestamp(0),
                           last_remote_ledger_timestamp=datetime.utcfromtimestamp(0),
                           fiscal_year_end_date=None,
                           tax_id=None,
                           dissolution_date=datetime.utcfromtimestamp(0))
    rv = client.get('/api/v1/businesses/CP1234567')

    # dissolved company cannot be found.
    assert rv.status_code == 404
