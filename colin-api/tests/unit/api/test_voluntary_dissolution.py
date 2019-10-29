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

"""Tests to assure the change of address filing end-point."""

from tests import oracle_integration


ID = []


@oracle_integration
def test_get_vd(client):
    """Assert that the get end point for voluntary dissolution is successful."""
    rv = client.get('/api/v1/businesses/CP0001697/filings/voluntaryDissolution')

    assert 200 == rv.status_code

    assert rv.json['filing']['voluntaryDissolution']
    assert rv.json['filing']['voluntaryDissolution']['eventId']
    ID.append(rv.json['filing']['voluntaryDissolution']['eventId'])


@oracle_integration
def test_get_vd_by_id(client):
    """Assert that giving an id gets the corresponding voluntary dissolution."""
    rv = client.get(f'/api/v1/businesses/CP0001697/filings/voluntaryDissolution?eventId={ID[0]}')

    assert 200 == rv.status_code

    assert rv.json['filing']['voluntaryDissolution']
    assert rv.json['filing']['voluntaryDissolution']['eventId'] == ID[0]


@oracle_integration
def test_get_vd_by_id_wrong_corp(client):
    """Assert that a coop searching for a vd filing associated with a different coop returns a 404."""
    rv = client.get(f'/api/v1/businesses/CP0000005/filings/voluntaryDissolution?eventId={ID[0]}')
    assert 404 == rv.status_code


@oracle_integration
def test_get_vd_no_results(client):
    """Assert that searching for a vd filing on a coop without one returns a 404."""
    rv = client.get('/api/v1/businesses/CP0000000/filings/voluntaryDissolution')

    assert 404 == rv.status_code
