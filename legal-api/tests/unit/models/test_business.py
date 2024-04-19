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
from datetime import datetime, timedelta
from flask import current_app

import datedelta
import pytest
from sqlalchemy_continuum import versioning_manager

from legal_api.exceptions import BusinessException
from legal_api.models import AmalgamatingBusiness, Amalgamation, Business, Filing, db
from legal_api.utils.legislation_datetime import LegislationDatetime
from tests import EPOCH_DATETIME, TIMEZONE_OFFSET
from tests.unit import has_expected_date_str_format


def factory_business(designation: str = '001'):
    """Return a valid Business object stamped with the supplied designation."""
    return Business(legal_name=f'legal_name-{designation}',
                    founding_date=datetime.utcfromtimestamp(0),
                    last_ledger_timestamp=datetime.utcfromtimestamp(0),
                    dissolution_date=None,
                    identifier='CP1234567',
                    tax_id=f'BN0000{designation}',
                    fiscal_year_end_date=datetime(2001, 8, 5, 7, 7, 58, 272362),
                    state=Business.State.ACTIVE)


def test_business_identifier(session):
    """Assert that setting the business identifier must be in a valid format."""
    from tests.conftest import not_raises
    valid_identifier = 'CP1234567'
    invalid_identifier = '1234567'
    b = Business()

    with not_raises(BusinessException):
        b.identifier = valid_identifier

    with pytest.raises(BusinessException):
        b.identifier = invalid_identifier


TEST_IDENTIFIER_DATA = [
    ('CP1234567', True),
    ('BC1234567', True),
    ('C1234567', True),
    ('FM1234567', True),
    ('cp1234567', False),
    ('bc1234567', False),
    ('c1234567', False),
    ('fm1234567', False),
    ('CP0000000', False),
    ('CP000000A', False),
    ('AB0000001', False),
]


@pytest.mark.parametrize('identifier,expected', TEST_IDENTIFIER_DATA)
def test_business_validate_identifier(identifier, expected):
    """Assert that the identifier is validated correctly."""
    assert Business.validate_identifier(identifier) is expected


def test_business(session):
    """Assert a valid business is stored correctly.

    Start with a blank database.
    """
    business = factory_business('001')
    business.save()

    assert business.id is not None
    assert business.state == Business.State.ACTIVE
    assert business.admin_freeze is False


def test_business_find_by_legal_name_pass(session):
    """Assert that the business can be found by name."""
    designation = '001'
    business = Business(legal_name=f'legal_name-{designation}',
                        founding_date=datetime.utcfromtimestamp(0),
                        last_ledger_timestamp=datetime.utcfromtimestamp(0),
                        dissolution_date=None,
                        identifier=f'CP1234{designation}',
                        tax_id=f'BN0000{designation}',
                        fiscal_year_end_date=datetime(2001, 8, 5, 7, 7, 58, 272362))
    session.add(business)
    session.commit()

    b = Business.find_by_legal_name('legal_name-001')
    assert b is not None


def test_business_find_by_legal_name_fail(session):
    """Assert that the business can not be found, once it is disolved."""
    designation = '001'
    business = Business(legal_name=f'legal_name-{designation}',
                        founding_date=datetime.utcfromtimestamp(0),
                        last_ledger_timestamp=datetime.utcfromtimestamp(0),
                        dissolution_date=datetime.utcfromtimestamp(0),
                        identifier=f'CP1234{designation}',
                        tax_id=f'BN0000{designation}',
                        fiscal_year_end_date=datetime(2001, 8, 5, 7, 7, 58, 272362))
    session.add(business)
    session.commit()

    # business is dissolved, it should not be found by name search
    b = Business.find_by_legal_name('legal_name-001')
    assert b is None


def test_business_find_by_legal_name_missing(session):
    """Assert that the business can be found by name."""
    designation = '001'
    business = Business(legal_name=f'legal_name-{designation}',
                        founding_date=datetime.utcfromtimestamp(0),
                        last_ledger_timestamp=datetime.utcfromtimestamp(0),
                        dissolution_date=None,
                        identifier=f'CP1234{designation}',
                        tax_id=f'BN0000{designation}',
                        fiscal_year_end_date=datetime(2001, 8, 5, 7, 7, 58, 272362))
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
                        founding_date=datetime.utcfromtimestamp(0),
                        last_ledger_timestamp=datetime.utcfromtimestamp(0),
                        dissolution_date=datetime.utcfromtimestamp(0),
                        identifier=f'CP1234{designation}',
                        tax_id=f'BN0000{designation}',
                        fiscal_year_end_date=datetime(2001, 8, 5, 7, 7, 58, 272362))
    business.save()

    b = business.delete()

    assert b.id == business.id


def test_delete_business_active(session):
    """Assert that the business can be found by name."""
    designation = '001'
    business = Business(legal_name=f'legal_name-{designation}',
                        founding_date=datetime.utcfromtimestamp(0),
                        last_ledger_timestamp=datetime.utcfromtimestamp(0),
                        dissolution_date=None,
                        identifier='CP1234567',
                        tax_id='XX',
                        fiscal_year_end_date=datetime(2001, 8, 5, 7, 7, 58, 272362))
    business.save()

    b = business.delete()

    assert b.id == business.id


def test_business_find_by_identifier(session):
    """Assert that the business can be found by name."""
    designation = '001'
    business = Business(legal_name=f'legal_name-{designation}',
                        founding_date=datetime.utcfromtimestamp(0),
                        last_ledger_timestamp=datetime.utcfromtimestamp(0),
                        dissolution_date=None,
                        identifier='CP1234567',
                        tax_id=f'BN0000{designation}',
                        fiscal_year_end_date=datetime(2001, 8, 5, 7, 7, 58, 272362))
    business.save()

    b = Business.find_by_identifier('CP1234567')

    assert b is not None


def test_business_find_by_identifier_no_identifier(session):
    """Assert that the business can be found by name."""
    designation = '001'
    business = Business(legal_name=f'legal_name-{designation}',
                        founding_date=datetime.utcfromtimestamp(0),
                        last_ledger_timestamp=datetime.utcfromtimestamp(0),
                        dissolution_date=None,
                        identifier=f'CP1234{designation}',
                        tax_id=f'BN0000{designation}',
                        fiscal_year_end_date=datetime(2001, 8, 5, 7, 7, 58, 272362))
    business.save()

    b = Business.find_by_identifier()

    assert b is None


TEST_GOOD_STANDING_DATA = [
    (datetime.now() - datedelta.datedelta(months=6), Business.LegalTypes.COMP, Business.State.ACTIVE.value, False, True),
    (datetime.now() - datedelta.datedelta(months=6), Business.LegalTypes.COMP, Business.State.ACTIVE.value, True, False),
    (datetime.now() - datedelta.datedelta(months=6), Business.LegalTypes.COMP, Business.State.HISTORICAL.value, False, True),
    (datetime.now() - datedelta.datedelta(years=1, months=6), Business.LegalTypes.COMP, Business.State.ACTIVE.value, False, False),
    (datetime.now() - datedelta.datedelta(years=1, months=6), Business.LegalTypes.SOLE_PROP, Business.State.ACTIVE.value, False, True),
    (datetime.now() - datedelta.datedelta(years=1, months=6), Business.LegalTypes.PARTNERSHIP, Business.State.ACTIVE.value, False, True),
    (datetime.now() - datedelta.datedelta(months=6), Business.LegalTypes.SOLE_PROP, Business.State.ACTIVE.value, False, True),
    (datetime.now() - datedelta.datedelta(months=6), Business.LegalTypes.PARTNERSHIP, Business.State.ACTIVE.value, False, True)
]


@pytest.mark.parametrize('last_ar_date, legal_type, state, limited_restoration, expected', TEST_GOOD_STANDING_DATA)
def test_good_standing(session, last_ar_date, legal_type, state, limited_restoration, expected):
    """Assert that the business is in good standing when conditions are met."""
    designation = '001'
    business = Business(legal_name=f'legal_name-{designation}',
                        founding_date=datetime.utcfromtimestamp(0),
                        last_ledger_timestamp=datetime.utcfromtimestamp(0),
                        dissolution_date=None,
                        identifier=f'CP1234{designation}',
                        legal_type=legal_type,
                        state=state,
                        tax_id=f'BN0000{designation}',
                        fiscal_year_end_date=datetime(2001, 8, 5, 7, 7, 58, 272362),
                        last_ar_date=last_ar_date,
                        restoration_expiry_date=datetime.utcnow() if limited_restoration else None)
    business.save()

    assert business.good_standing is expected


def test_business_json(session):
    """Assert that the business model is saved correctly."""
    business = Business(legal_name='legal_name',
                        legal_type='CP',
                        founding_date=EPOCH_DATETIME,
                        start_date=datetime(2021, 8, 5, 8, 7, 58, 272362),
                        last_ledger_timestamp=EPOCH_DATETIME,
                        identifier='CP1234567',
                        last_modified=EPOCH_DATETIME,
                        last_ar_date=EPOCH_DATETIME,
                        last_agm_date=EPOCH_DATETIME,
                        restriction_ind=True,
                        association_type='CP',
                        # NB: default not intitialized since bus not committed before check
                        state=Business.State.ACTIVE,
                        tax_id='123456789'
                        )
    # basic json
    base_url = current_app.config.get('LEGAL_API_BASE_URL')

    # slim json
    d_slim = {
        'adminFreeze': False,
        'goodStanding': False,  # good standing will be false because the epoch is 1970
        'identifier': 'CP1234567',
        'legalName': 'legal_name',
        'legalType': Business.LegalTypes.COOP.value,
        'state': Business.State.ACTIVE.name,
        'taxId': '123456789'
    }

    assert business.json(slim=True) == d_slim

    # remove taxId to test it doesn't show up again until the final test
    business.tax_id = None
    d_slim.pop('taxId')

    d = {
        **d_slim,
        'foundingDate': EPOCH_DATETIME.isoformat(),
        'lastAddressChangeDate': '',
        'lastDirectorChangeDate': '',
        'lastLedgerTimestamp': EPOCH_DATETIME.isoformat(),
        'lastModified': EPOCH_DATETIME.isoformat(),
        'lastAnnualReportDate': datetime.date(EPOCH_DATETIME).isoformat(),
        'lastAnnualGeneralMeetingDate': datetime.date(EPOCH_DATETIME).isoformat(),
        'naicsKey': None,
        'naicsCode': None,
        'naicsDescription': None,
        'nextAnnualReport': '1971-01-01T08:00:00+00:00',
        'hasRestrictions': True,
        'arMinDate': '1971-01-01',
        'arMaxDate': '1972-04-30',
        'complianceWarnings': [],
        'warnings': [],
        'hasCorrections': False,
        'associationType': 'CP',
        'startDate': '2021-08-05',
        'hasCourtOrders': False,
        'allowedActions': {}
    }

    assert business.json() == d

    # include dissolutionDate
    business.dissolution_date = EPOCH_DATETIME
    d['dissolutionDate'] = LegislationDatetime.format_as_legislation_date(business.dissolution_date)
    business_json = business.json()
    assert business_json == d
    dissolution_date_str = business_json['dissolutionDate']
    dissolution_date_format_correct = has_expected_date_str_format(dissolution_date_str, '%Y-%m-%d')
    assert dissolution_date_format_correct

    business.dissolution_date = None
    d.pop('dissolutionDate')

    # include fiscalYearEndDate
    business.fiscal_year_end_date = EPOCH_DATETIME
    d['fiscalYearEndDate'] = datetime.date(business.fiscal_year_end_date).isoformat()
    assert business.json() == d
    business.fiscal_year_end_date = None
    d.pop('fiscalYearEndDate')

    # include taxId
    business.tax_id = '123456789'
    d['taxId'] = business.tax_id
    assert business.json() == d


def test_business_relationships_json(session):
    """Assert that the business model is saved correctly."""
    from legal_api.models import Address, Office

    business = Business(legal_name='legal_name',
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


@pytest.mark.parametrize('business_type,expected', [
    ('CP', True),
    ('NOT_FOUND', False),
])
def test_get_next_value_from_sequence(session, business_type, expected):
    """Assert that the sequence value is generated successfully."""
    from legal_api.models import Business

    if expected:
        first_val = Business.get_next_value_from_sequence(business_type)
        assert first_val

        next_val = Business.get_next_value_from_sequence(business_type)
        assert next_val
        assert next_val == first_val + 1

    else:
        assert not Business.get_next_value_from_sequence(business_type)


def test_continued_in_business(session):
    """Assert that the continued corp is saved successfully."""
    business = Business(
        legal_name='Test - Legal Name',
        legal_type='BC',
        founding_date=datetime.utcfromtimestamp(0),
        last_ledger_timestamp=datetime.utcfromtimestamp(0),
        dissolution_date=None,
        identifier='BC1234567',
        state=Business.State.ACTIVE,
        jurisdiction='CA',
        foreign_identifier='C1234567',
        foreign_legal_name='Prev Legal Name',
        foreign_legal_type='BEN',
        foreign_incorporation_date=datetime.utcfromtimestamp(0),
    )
    business.save()
    business_json = business.json()
    assert business_json['jurisdiction'] == business.jurisdiction
    assert business_json['foreignIdentifier'] == business.foreign_identifier
    assert business_json['foreignLegalName'] == business.foreign_legal_name
    assert business_json['foreignLegalType'] == business.foreign_legal_type
    assert business_json['foreignIncorporationDate'] == \
        LegislationDatetime.format_as_legislation_date(business.foreign_incorporation_date)


@pytest.mark.parametrize('test_name,existing_business_state', [
    ('EXIST', Business.State.HISTORICAL),
    ('NOT_EXIST', Business.State.ACTIVE),
])
def test_amalgamated_into_business_json(session, test_name, existing_business_state):
    """Assert that the amalgamated into is in json."""
    existing_business = Business(
        legal_name='Test - Amalgamating Legal Name',
        legal_type='BC',
        founding_date=datetime.utcfromtimestamp(0),
        dissolution_date=datetime.now(),
        identifier='BC1234567',
        state=Business.State.ACTIVE,
    )
    existing_business.save()

    if test_name == 'EXIST':

        filing = Filing()
        filing._filing_type = 'amalgamationApplication'
        filing.save()

        # Versioning business
        uow = versioning_manager.unit_of_work(db.session)
        transaction = uow.create_transaction(db.session)

        business = Business(
            legal_name='Test - Legal Name',
            legal_type='BC',
            founding_date=datetime.utcfromtimestamp(0),
            identifier='BC1234568',
            state=Business.State.ACTIVE,
        )
        amalgamation = Amalgamation()
        amalgamation.filing_id = filing.id
        amalgamation.amalgamation_type = 'regular'
        amalgamation.amalgamation_date = datetime.now()
        amalgamation.court_approval = True

        amalgamating_business = AmalgamatingBusiness()
        amalgamating_business.role = 'amalgamating'
        amalgamating_business.business_id = existing_business.id
        amalgamation.amalgamating_businesses.append(amalgamating_business)

        business.amalgamation.append(amalgamation)
        db.session.add(business)
        existing_business.state_filing_id = filing.id
        existing_business.state = existing_business_state
        db.session.add(existing_business)
        db.session.commit()

        filing.transaction_id = transaction.id
        filing.business_id = business.id
        filing.save()

    business_json = existing_business.json()

    if test_name == 'EXIST':
        assert not 'stateFiling' in business_json
        assert 'amalgamatedInto' in business_json
        assert business_json['amalgamatedInto']['amalgamationDate'] == amalgamation.amalgamation_date.isoformat()
        assert business_json['amalgamatedInto']['amalgamationType'] == amalgamation.amalgamation_type.name
        assert business_json['amalgamatedInto']['courtApproval'] == amalgamation.court_approval
        assert business_json['amalgamatedInto']['identifier'] == business.identifier
        assert business_json['amalgamatedInto']['legalName'] == business.legal_name
    else:
        assert not 'amalgamatedInto' in business_json
