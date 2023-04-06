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

"""Tests to assure the Business Model.

Test-Suite to ensure that the Business Model is working as expected.
"""
from datetime import datetime

import pytest

from legal_api.exceptions import BusinessException
from legal_api.models import ShadowBusiness
from tests import EPOCH_DATETIME


def factory_business(designation: str = '001'):
    """Return a valid Business object stamped with the supplied designation."""
    return ShadowBusiness(legal_name=f'legal_name-{designation}',
                    founding_date=datetime.utcfromtimestamp(0),
                    identifier='CP1234567',
                    state=ShadowBusiness.State.ACTIVE)


def test_business_identifier(session):
    """Assert that setting the business identifier must be in a valid format."""
    from tests.conftest import not_raises
    valid_identifier = 'CP1234567'
    invalid_identifier = '1234567'
    b = ShadowBusiness()

    with not_raises(BusinessException):
        b.identifier = valid_identifier

    with pytest.raises(BusinessException):
        b.identifier = invalid_identifier


TEST_IDENTIFIER_DATA = [
    ('CP1234567', True),
    ('CP0000000', False),
    ('CP000000A', False),
    ('AB0000001', False),
]


@pytest.mark.parametrize('identifier,expected', TEST_IDENTIFIER_DATA)
def test_business_validate_identifier(identifier, expected):
    """Assert that the identifier is validated correctly."""
    assert ShadowBusiness.validate_identifier(identifier) is expected


def test_business(session):
    """Assert a valid business is stored correctly.

    Start with a blank database.
    """
    business = factory_business('001')
    business.save()

    assert business.id is not None
    assert business.state == ShadowBusiness.State.ACTIVE


def test_business_find_by_legal_name_pass(session):
    """Assert that the business can be found by name."""
    designation = '001'
    business = ShadowBusiness(legal_name=f'legal_name-{designation}',
                        founding_date=datetime.utcfromtimestamp(0),
                        last_ledger_timestamp=datetime.utcfromtimestamp(0),
                        dissolution_date=None,
                        identifier=f'CP1234{designation}',
                        tax_id=f'BN0000{designation}',
                        fiscal_year_end_date=datetime(2001, 8, 5, 7, 7, 58, 272362))
    session.add(business)
    session.commit()

    b = ShadowBusiness.find_by_legal_name('legal_name-001')
    assert b is not None


def test_business_find_by_legal_name_fail(session):
    """Assert that the business can not be found, once it is disolved."""
    designation = '001'
    business = ShadowBusiness(legal_name=f'legal_name-{designation}',
                        founding_date=datetime.utcfromtimestamp(0),
                        last_ledger_timestamp=datetime.utcfromtimestamp(0),
                        dissolution_date=datetime.utcfromtimestamp(0),
                        identifier=f'CP1234{designation}',
                        tax_id=f'BN0000{designation}',
                        fiscal_year_end_date=datetime(2001, 8, 5, 7, 7, 58, 272362))
    session.add(business)
    session.commit()

    # business is dissolved, it should not be found by name search
    b = ShadowBusiness.find_by_legal_name('legal_name-001')
    assert b is None


def test_business_find_by_legal_name_missing(session):
    """Assert that the business can be found by name."""
    designation = '001'
    business = ShadowBusiness(legal_name=f'legal_name-{designation}',
                        founding_date=datetime.utcfromtimestamp(0),
                        last_ledger_timestamp=datetime.utcfromtimestamp(0),
                        dissolution_date=None,
                        identifier=f'CP1234{designation}',
                        tax_id=f'BN0000{designation}',
                        fiscal_year_end_date=datetime(2001, 8, 5, 7, 7, 58, 272362))
    session.add(business)
    session.commit()

    b = ShadowBusiness.find_by_legal_name()
    assert b is None


def test_business_find_by_legal_name_no_database_connection(app_request):
    """Assert that None is return even if the database connection does not exist."""
    app_request.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://does:not@exist:5432/nada'
    with app_request.app_context():
        b = ShadowBusiness.find_by_legal_name('failure to find')
        assert b is None


def test_business_find_by_identifier(session):
    """Assert that the business can be found by name."""
    designation = '001'
    business = ShadowBusiness(legal_name=f'legal_name-{designation}',
                        founding_date=datetime.utcfromtimestamp(0),
                        last_ledger_timestamp=datetime.utcfromtimestamp(0),
                        dissolution_date=None,
                        identifier='CP1234567',
                        tax_id=f'BN0000{designation}',
                        fiscal_year_end_date=datetime(2001, 8, 5, 7, 7, 58, 272362))
    business.save()

    b = ShadowBusiness.find_by_identifier('CP1234567')

    assert b is not None


def test_business_find_by_identifier_no_identifier(session):
    """Assert that the business can be found by name."""
    designation = '001'
    business = ShadowBusiness(legal_name=f'legal_name-{designation}',
                        founding_date=datetime.utcfromtimestamp(0),
                        last_ledger_timestamp=datetime.utcfromtimestamp(0),
                        dissolution_date=None,
                        identifier=f'CP1234{designation}',
                        tax_id=f'BN0000{designation}',
                        fiscal_year_end_date=datetime(2001, 8, 5, 7, 7, 58, 272362))
    business.save()

    b = ShadowBusiness.find_by_identifier()

    assert b is None


def test_business_relationships_json(session):
    """Assert that the business model is saved correctly."""
    from legal_api.models import Address, Office

    business = ShadowBusiness(legal_name='legal_name',
                        founding_date=EPOCH_DATETIME,
                        last_ledger_timestamp=EPOCH_DATETIME,
                        identifier='CP1234567',
                        last_modified=EPOCH_DATETIME)

    office = Office(office_type='registeredOffice')
    mailing_address = Address(city='Test City', address_type=Address.MAILING,
                              business_id=business.id)
    office.addresses.append(mailing_address)
    business.offices.append(office)
    business.save()

    assert business.mailing_address.one_or_none()

    delivery_address = Address(city='Test City',
                               address_type=Address.DELIVERY,
                               business_id=business.id)
    office.addresses.append(delivery_address)
    business.save()

    assert business.delivery_address.one_or_none()
