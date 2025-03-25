# Copyright © 2022 Province of British Columbia
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

"""Tests to assure the DCConnection Model.

Test-Suite to ensure that the DCConnection Model is working as expected.
"""

from business_model.models import DCConnection

from tests.models import factory_business


def test_valid_dc_connection_save(session):
    """Assert that a valid dc_connection can be saved."""
    identifier = 'FM1234567'
    business = factory_business(identifier)
    connection = create_dc_connection(business)
    assert connection.id


def test_find_by_id(session):
    """Assert that the method returns correct value."""
    identifier = 'FM1234567'
    business = factory_business(identifier)
    connection = create_dc_connection(business)

    res = DCConnection.find_by_id(connection.id)

    assert res
    assert res.connection_id == connection.connection_id


def test_find_dc_connection_by_connection_id(session):
    """Assert that the method returns correct value."""
    identifier = 'FM1234567'
    business = factory_business(identifier)
    connection = create_dc_connection(business)

    res = DCConnection.find_by_connection_id(connection.connection_id)

    assert res
    assert res.id == connection.id


def test_find_active_by(session):
    """Assert that the method returns correct value."""
    identifier = 'FM1234567'
    business = factory_business(identifier)
    create_dc_connection(business, is_active=True)

    res = DCConnection.find_active_by(business.id)

    assert res
    assert res.connection_state == 'active'


def test_find_by(session):
    """Assert that the method returns correct value."""
    identifier = 'FM1234567'
    business = factory_business(identifier)
    connection = create_dc_connection(business)

    res = DCConnection.find_by(business_id=business.id, connection_state='invitation')

    assert len(res) == 1
    assert res[0].id == connection.id


def create_dc_connection(business, is_active=False):
    """Create new dc_connection object."""
    connection = DCConnection(
        connection_id='0d94e18b-3a52-4122-8adf-33e2ccff681f',
        invitation_url="""http://192.168.65.3:8020?c_i=eyJAdHlwZSI6ICJodHRwczovL2RpZGNvbW0ub3JnL2Nvbm5lY3Rpb
25zLzEuMC9pbnZpdGF0aW9uIiwgIkBpZCI6ICIyZjU1M2JkZS01YWJlLTRkZDctODIwZi1mNWQ2Mjc1OWQxODgi
LCAicmVjaXBpZW50S2V5cyI6IFsiMkFHSjVrRDlVYU45OVpSeUFHZVZKNDkxclZhNzZwZGZYdkxXZkFyc2lKWjY
iXSwgImxhYmVsIjogImZhYmVyLmFnZW50IiwgInNlcnZpY2VFbmRwb2ludCI6ICJodHRwOi8vMTkyLjE2OC42NS4zOjgwMjAifQ==""",
        is_active=is_active,
        connection_state='active' if is_active else 'invitation',
        business_id=business.id
    )
    connection.save()
    return connection
