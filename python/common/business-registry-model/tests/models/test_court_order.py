# Copyright © 2026 Province of British Columbia
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

"""Tests to assure the CourtOrder Model.

Test-Suite to ensure that the CourtOrder Model is working as expected.
"""
from datetime import UTC, datetime

from business_model.models import CourtOrder
from tests.models import factory_business, factory_filing


def test_court_order_save(session):
    """Assert that the court order was saved."""
    business = factory_business('CP1234567')
    filing = factory_filing(business, data_dict={'filing': {'header': {'name': 'courtOrder'}}})

    court_order = CourtOrder(
        filing_id=filing.id,
        business_id=business.id,
        file_number='12345',
        effect_of_order='planOfArrangement',
        order_details='Some details'
    )
    court_order.save()
    assert court_order.id


def test_court_order_json(session):
    """Assert that court order json property works."""
    business = factory_business('CP1234567')
    filing = factory_filing(business, data_dict={'filing': {'header': {'name': 'courtOrder'}}})
    from datetime import timezone
    order_date = datetime.now(UTC)

    court_order = CourtOrder(
        filing_id=filing.id,
        business_id=business.id,
        file_number='12345',
        order_date=order_date,
        effect_of_order='planOfArrangement',
        order_details='Some details'
    )
    court_order.save()

    co_json = court_order.json
    assert co_json['id'] == court_order.id
    assert co_json['filingId'] == filing.id
    assert co_json['fileNumber'] == '12345'
    assert co_json['orderDate'] == order_date
    assert co_json['effectOfOrder'] == 'planOfArrangement'
    assert co_json['orderDetails'] == 'Some details'


def test_court_order_get_by_id(session):
    """Assert that a court order can be retrieved by ID."""
    business = factory_business('CP1234567')
    filing = factory_filing(business, data_dict={'filing': {'header': {'name': 'courtOrder'}}})

    court_order = CourtOrder(
        filing_id=filing.id,
        business_id=business.id,
        file_number='12345',
        effect_of_order='planOfArrangement',
        order_details='Some details'
    )
    court_order.save()

    fetched = CourtOrder.get_by_id(court_order.id)
    assert fetched
    assert fetched.id == court_order.id


def test_court_order_get_by_filing_id(session):
    """Assert that a court order can be retrieved by filing ID."""
    business = factory_business('CP1234567')
    filing = factory_filing(business, data_dict={'filing': {'header': {'name': 'courtOrder'}}})

    court_order = CourtOrder(
        filing_id=filing.id,
        business_id=business.id,
        file_number='12345',
        effect_of_order='planOfArrangement',
        order_details='Some details'
    )
    court_order.save()

    fetched = CourtOrder.get_by_filing_id(filing.id)
    assert fetched
    assert fetched.filing_id == filing.id


def test_court_order_get_by_business_id(session):
    """Assert that court orders can be retrieved by business ID."""
    business = factory_business('CP1234567')
    filing = factory_filing(business, data_dict={'filing': {'header': {'name': 'courtOrder'}}})

    court_order1 = CourtOrder(
        filing_id=filing.id,
        business_id=business.id,
        file_number='12345',
        effect_of_order='planOfArrangement',
        order_details='Some details 1'
    )
    court_order1.save()

    court_order2 = CourtOrder(
        filing_id=filing.id,
        business_id=business.id,
        file_number='67890',
        effect_of_order='planOfArrangement',
        order_details='Some details 2'
    )
    court_order2.save()

    fetched_list = CourtOrder.get_by_business_id(business.id)
    assert len(fetched_list) == 2


def test_court_order_missing_getters(session):
    """Assert that None/empty list is returned when ID is missing or not found."""
    assert CourtOrder.get_by_id(None) is None
    assert CourtOrder.get_by_filing_id(None) is None
    assert CourtOrder.get_by_business_id(None) == []
