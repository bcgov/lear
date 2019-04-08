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

"""Tests to assure the Business Class.

Test-Suite to ensure that the Business Class is working as expected.
"""
import datetime

from legal_api.models import Business


def factory_business(designation: str = '001'):
    """Return a valid Business object stamped with the supplied designation."""
    return Business(legal_name=f'legal_name-{designation}',
                    founding_date=datetime.datetime.utcfromtimestamp(0),
                    dissolution_date=None,
                    identifier=f'CP1234567',
                    tax_id=f'BN0000{designation}',
                    fiscal_year_end_date=datetime.datetime(2001, 8, 5, 7, 7, 58, 272362))


def test_business(session):
    """Assert a valid business is stored correctly.

    Start with a blank database.
    """
    business = factory_business('001')
    business.save()

    assert business.id is not None


def test_business_find_by_legal_name_pass(session):
    """Assert that the business can be found by name."""
    designation = '001'
    business = Business(legal_name=f'legal_name-{designation}',
                        founding_date=datetime.datetime.utcfromtimestamp(0),
                        dissolution_date=None,
                        identifier=f'BC COOP{designation}',
                        tax_id=f'BN0000{designation}',
                        fiscal_year_end_date=datetime.datetime(2001, 8, 5, 7, 7, 58, 272362))
    session.add(business)
    session.commit()

    b = Business.find_by_legal_name('legal_name-001')
    assert b is not None


def test_business_find_by_legal_name_fail(session):
    """Assert that the business can not be found, once it is disolved."""
    designation = '001'
    business = Business(legal_name=f'legal_name-{designation}',
                        founding_date=datetime.datetime.utcfromtimestamp(0),
                        dissolution_date=datetime.datetime.utcfromtimestamp(0),
                        identifier=f'BC COOP{designation}',
                        tax_id=f'BN0000{designation}',
                        fiscal_year_end_date=datetime.datetime(2001, 8, 5, 7, 7, 58, 272362))
    session.add(business)
    session.commit()

    # business is disolved, it should not be found by name search
    b = Business.find_by_legal_name('legal_name-001')
    assert b is None


def test_business_find_by_legal_name_missing(session):
    """Assert that the business can be found by name."""
    designation = '001'
    business = Business(legal_name=f'legal_name-{designation}',
                        founding_date=datetime.datetime.utcfromtimestamp(0),
                        dissolution_date=None,
                        identifier=f'BC COOP{designation}',
                        tax_id=f'BN0000{designation}',
                        fiscal_year_end_date=datetime.datetime(2001, 8, 5, 7, 7, 58, 272362))
    session.add(business)
    session.commit()

    b = Business.find_by_legal_name()
    assert b is None


def test_business_find_by_legal_name_no_database_connection(app_request):
    """Assert that None is return even if the database connection does not exist."""
    app_request.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://does:not@exist:5432/nada'
    with app_request.app_context():
        b = Business.find_by_legal_name('failure to find')
        assert b is None


def test_delete_business_with_dissolution(session):
    """Assert that the business can be found by name."""
    designation = '001'
    business = Business(legal_name=f'legal_name-{designation}',
                        founding_date=datetime.datetime.utcfromtimestamp(0),
                        dissolution_date=datetime.datetime.utcfromtimestamp(0),
                        identifier=f'BC COOP{designation}',
                        tax_id=f'BN0000{designation}',
                        fiscal_year_end_date=datetime.datetime(2001, 8, 5, 7, 7, 58, 272362))
    business.save()

    b = business.delete()

    assert b.id == business.id


def test_delete_business_active(session):
    """Assert that the business can be found by name."""
    designation = '001'
    business = Business(legal_name=f'legal_name-{designation}',
                        founding_date=datetime.datetime.utcfromtimestamp(0),
                        dissolution_date=None,
                        identifier='CP1234567',
                        tax_id=f'XX',
                        fiscal_year_end_date=datetime.datetime(2001, 8, 5, 7, 7, 58, 272362))
    business.save()

    b = business.delete()

    assert b.id == business.id


def test_business_find_by_identifier(session):
    """Assert that the business can be found by name."""
    designation = '001'
    business = Business(legal_name=f'legal_name-{designation}',
                        founding_date=datetime.datetime.utcfromtimestamp(0),
                        dissolution_date=None,
                        identifier='CP1234567',
                        tax_id=f'BN0000{designation}',
                        fiscal_year_end_date=datetime.datetime(2001, 8, 5, 7, 7, 58, 272362))
    business.save()

    b = Business.find_by_identifier('CP1234567')

    assert b is not None


def test_business_find_by_identifier_no_identifier(session):
    """Assert that the business can be found by name."""
    designation = '001'
    business = Business(legal_name=f'legal_name-{designation}',
                        founding_date=datetime.datetime.utcfromtimestamp(0),
                        dissolution_date=None,
                        identifier=f'BC COOP{designation}',
                        tax_id=f'BN0000{designation}',
                        fiscal_year_end_date=datetime.datetime(2001, 8, 5, 7, 7, 58, 272362))
    business.save()

    b = Business.find_by_identifier()

    assert b is None
