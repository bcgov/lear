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

"""Tests to assure the LegalEntity Model.

Test-Suite to ensure that the Business Model is working as expected.
"""
import uuid
from datetime import datetime, timedelta

import datedelta
import pytest
from flask import current_app
from sql_versioning import history_cls

from business_model.exceptions import BusinessException
from business_model import LegalEntity
from business_model.utils.legislation_datetime import LegislationDatetime
from tests import EPOCH_DATETIME, TIMEZONE_OFFSET
from tests import has_expected_date_str_format


def factory_legal_entity(designation: str = '001'):
    """Return a valid Business object stamped with the supplied designation."""
    return LegalEntity(legal_name=f'legal_name-{designation}',
                    founding_date=datetime.utcfromtimestamp(0),
                    last_ledger_timestamp=datetime.utcfromtimestamp(0),
                    dissolution_date=None,
                    identifier='CP1234567',
                    tax_id=f'BN0000{designation}',
                    fiscal_year_end_date=datetime(2001, 8, 5, 7, 7, 58, 272362),
                    state=LegalEntity.State.ACTIVE)


def test_business_identifier(session):
    """Assert that setting the business identifier must be in a valid format."""
    from tests.conftest import not_raises
    valid_identifier = 'CP1234567'
    invalid_identifier = '1234567'
    b = LegalEntity()

    with not_raises(BusinessException):
        b.identifier = valid_identifier

    with pytest.raises(BusinessException):
        b.identifier = invalid_identifier


TEST_IDENTIFIER_DATA = [
    ('CP1234567', 'CP', True),
    ('CP0000000', 'CP', False),
    ('CP000000A', 'CP', False),
    ('AB0000001', 'BC', False),
    (None, 'person', True),
]


@pytest.mark.parametrize('identifier,entity_type,expected', TEST_IDENTIFIER_DATA)
def test_business_validate_identifier(entity_type, identifier, expected):
    """Assert that the identifier is validated correctly."""
    assert LegalEntity.validate_identifier(entity_type, identifier) is expected


def test_business(session):
    """Assert a valid business is stored correctly.

    Start with a blank database.
    """
    legal_entity =factory_legal_entity('001')
    legal_entity.save()

    assert legal_entity.id is not None
    assert legal_entity.state == LegalEntity.State.ACTIVE
    assert legal_entity.admin_freeze is False

def test_business_history(session):
    """Assert a valid business is stored correctly.

    Start with a blank database.
    """
    legal_entity =factory_legal_entity('001')
    legal_entity.save()

    legal_entity.admin_freeze = False
    legal_entity.save()

    entity_history_cls = history_cls(LegalEntity)
    entity_history = session.query(entity_history_cls).all()

    for en in entity_history:
        print(en)
    # assert legal_entity.id is not None
    # assert legal_entity.state == LegalEntity.State.ACTIVE
    # assert legal_entity.admin_freeze is False


def test_business_find_by_legal_name_pass(session):
    """Assert that the business can be found by name."""
    designation = '001'
    legal_name=f'legal_name-{str(uuid.uuid4().hex)}'
    legal_entity =LegalEntity(legal_name=legal_name,
                        founding_date=datetime.utcfromtimestamp(0),
                        last_ledger_timestamp=datetime.utcfromtimestamp(0),
                        dissolution_date=None,
                        identifier=f'CP1234{designation}',
                        tax_id=f'BN0000{designation}',
                        fiscal_year_end_date=datetime(2001, 8, 5, 7, 7, 58, 272362))
    session.add(legal_entity)
    session.commit()

    b = LegalEntity.find_by_legal_name(legal_name)
    assert b is not None


def test_business_find_by_legal_name_fail(session):
    """Assert that the business can not be found, once it is disolved."""
    legal_name=f'legal_name-{str(uuid.uuid4().hex)}'
    designation = '001'
    legal_entity =LegalEntity(legal_name=legal_name,
                        founding_date=datetime.utcfromtimestamp(0),
                        last_ledger_timestamp=datetime.utcfromtimestamp(0),
                        dissolution_date=datetime.utcfromtimestamp(0),
                        identifier=f'CP1234{designation}',
                        tax_id=f'BN0000{designation}',
                        fiscal_year_end_date=datetime(2001, 8, 5, 7, 7, 58, 272362))
    session.add(legal_entity)
    session.commit()

    # business is dissolved, it should not be found by name search
    b = LegalEntity.find_by_legal_name(legal_name)
    assert b is None


def test_business_find_by_legal_name_missing(session):
    """Assert that the business can be found by name."""
    designation = '001'
    legal_entity =LegalEntity(legal_name=f'legal_name-{designation}',
                        founding_date=datetime.utcfromtimestamp(0),
                        last_ledger_timestamp=datetime.utcfromtimestamp(0),
                        dissolution_date=None,
                        identifier=f'CP1234{designation}',
                        tax_id=f'BN0000{designation}',
                        fiscal_year_end_date=datetime(2001, 8, 5, 7, 7, 58, 272362))
    session.add(legal_entity)
    session.commit()

    b = LegalEntity.find_by_legal_name()
    assert b is None


def test_delete_business_with_dissolution(session):
    """Assert that the business can be found by name."""
    designation = '001'
    legal_entity =LegalEntity(legal_name=f'legal_name-{designation}',
                        founding_date=datetime.utcfromtimestamp(0),
                        last_ledger_timestamp=datetime.utcfromtimestamp(0),
                        dissolution_date=datetime.utcfromtimestamp(0),
                        identifier=f'CP1234{designation}',
                        tax_id=f'BN0000{designation}',
                        fiscal_year_end_date=datetime(2001, 8, 5, 7, 7, 58, 272362))
    legal_entity.save()

    b = legal_entity.delete()

    assert b.id == legal_entity.id


def test_delete_business_active(session):
    """Assert that the business can be found by name."""
    designation = '001'
    legal_entity =LegalEntity(legal_name=f'legal_name-{designation}',
                        founding_date=datetime.utcfromtimestamp(0),
                        last_ledger_timestamp=datetime.utcfromtimestamp(0),
                        dissolution_date=None,
                        identifier='CP1234567',
                        tax_id='XX',
                        fiscal_year_end_date=datetime(2001, 8, 5, 7, 7, 58, 272362))
    legal_entity.save()

    b = legal_entity.delete()

    assert b.id == legal_entity.id


def test_business_find_by_identifier(session):
    """Assert that the business can be found by name."""
    designation = '001'
    identifier = 'CP0000001'
    legal_entity =LegalEntity(legal_name=f'legal_name-{designation}',
                        founding_date=datetime.utcfromtimestamp(0),
                        last_ledger_timestamp=datetime.utcfromtimestamp(0),
                        dissolution_date=None,
                        identifier=identifier,
                        tax_id=f'BN0000{designation}',
                        fiscal_year_end_date=datetime(2001, 8, 5, 7, 7, 58, 272362))
    legal_entity.save()

    b = LegalEntity.find_by_identifier(identifier)

    assert b is not None


def test_business_find_by_identifier_no_identifier(session):
    """Assert that the business can be found by name."""
    designation = '001'
    legal_entity =LegalEntity(legal_name=f'legal_name-{designation}',
                        founding_date=datetime.utcfromtimestamp(0),
                        last_ledger_timestamp=datetime.utcfromtimestamp(0),
                        dissolution_date=None,
                        identifier=f'CP1234{designation}',
                        tax_id=f'BN0000{designation}',
                        fiscal_year_end_date=datetime(2001, 8, 5, 7, 7, 58, 272362))
    legal_entity.save()

    b = LegalEntity.find_by_identifier()

    assert b is None


TEST_GOOD_STANDING_DATA = [
    (datetime.now() - datedelta.datedelta(months=6), LegalEntity.EntityTypes.COMP, LegalEntity.State.ACTIVE.value, False, True),
    (datetime.now() - datedelta.datedelta(months=6), LegalEntity.EntityTypes.COMP, LegalEntity.State.ACTIVE.value, True, False),
    (datetime.now() - datedelta.datedelta(months=6), LegalEntity.EntityTypes.COMP, LegalEntity.State.HISTORICAL.value, False, True),
    (datetime.now() - datedelta.datedelta(years=1, months=6), LegalEntity.EntityTypes.COMP, LegalEntity.State.ACTIVE.value, False, False),
    (datetime.now() - datedelta.datedelta(years=1, months=6), LegalEntity.EntityTypes.SOLE_PROP, LegalEntity.State.ACTIVE.value, False, True),
    (datetime.now() - datedelta.datedelta(years=1, months=6), LegalEntity.EntityTypes.PARTNERSHIP, LegalEntity.State.ACTIVE.value, False, True),
    (datetime.now() - datedelta.datedelta(months=6), LegalEntity.EntityTypes.SOLE_PROP, LegalEntity.State.ACTIVE.value, False, True),
    (datetime.now() - datedelta.datedelta(months=6), LegalEntity.EntityTypes.PARTNERSHIP, LegalEntity.State.ACTIVE.value, False, True)
]


@pytest.mark.parametrize('last_ar_date, entity_type, state, limited_restoration, expected', TEST_GOOD_STANDING_DATA)
def test_good_standing(session, last_ar_date, entity_type, state, limited_restoration, expected):
    """Assert that the business is in good standing when conditions are met."""
    designation = '001'
    legal_entity =LegalEntity(legal_name=f'legal_name-{designation}',
                        founding_date=datetime.utcfromtimestamp(0),
                        last_ledger_timestamp=datetime.utcfromtimestamp(0),
                        dissolution_date=None,
                        identifier=f'CP1234{designation}',
                        entity_type=entity_type,
                        state=state,
                        tax_id=f'BN0000{designation}',
                        fiscal_year_end_date=datetime(2001, 8, 5, 7, 7, 58, 272362),
                        last_ar_date=last_ar_date,
                        restoration_expiry_date=datetime.utcnow() if limited_restoration else None)
    legal_entity.save()

    assert legal_entity.good_standing is expected


def test_business_json(session):
    """Assert that the business model is saved correctly."""
    legal_entity =LegalEntity(legal_name='legal_name',
                        entity_type='CP',
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
                        state=LegalEntity.State.ACTIVE,
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
        'legalType': LegalEntity.EntityTypes.COOP.value,
        'state': LegalEntity.State.ACTIVE.name,
        'taxId': '123456789'
    }

    assert legal_entity.json(slim=True) == d_slim

    # remove taxId to test it doesn't show up again until the final test
    legal_entity.tax_id = None
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

    assert legal_entity.json() == d

    # include dissolutionDate
    legal_entity.dissolution_date = EPOCH_DATETIME
    d['dissolutionDate'] = LegislationDatetime.format_as_legislation_date(legal_entity.dissolution_date)
    business_json = legal_entity.json()
    assert business_json == d
    dissolution_date_str = business_json['dissolutionDate']
    dissolution_date_format_correct = has_expected_date_str_format(dissolution_date_str, '%Y-%m-%d')
    assert dissolution_date_format_correct

    legal_entity.dissolution_date = None
    d.pop('dissolutionDate')

    # include fiscalYearEndDate
    legal_entity.fiscal_year_end_date = EPOCH_DATETIME
    d['fiscalYearEndDate'] = datetime.date(legal_entity.fiscal_year_end_date).isoformat()
    assert legal_entity.json() == d
    legal_entity.fiscal_year_end_date = None
    d.pop('fiscalYearEndDate')

    # include taxId
    legal_entity.tax_id = '123456789'
    d['taxId'] = legal_entity.tax_id
    assert legal_entity.json() == d


def test_business_relationships_json(session):
    """Assert that the business model is saved correctly."""
    from business_model import Address, Office

    legal_entity =LegalEntity(legal_name='legal_name',
                        founding_date=EPOCH_DATETIME,
                        last_ledger_timestamp=EPOCH_DATETIME,
                        identifier='CP1234567',
                        last_modified=EPOCH_DATETIME)

    office = Office(office_type='registeredOffice')
    mailing_address = Address(city='Test City', address_type=Address.MAILING,
                              legal_entity_id=legal_entity.id)
    office.addresses.append(mailing_address)
    legal_entity.offices.append(office)
    legal_entity.save()

    assert legal_entity.office_mailing_address.one_or_none()

    delivery_address = Address(city='Test City',
                               address_type=Address.DELIVERY,
                               legal_entity_id=legal_entity.id)
    office.addresses.append(delivery_address)
    legal_entity.save()

    assert legal_entity.office_delivery_address.one_or_none()


@pytest.mark.parametrize('business_type,expected', [
    ('CP', True),
    ('NOT_FOUND', False),
])
def test_get_next_value_from_sequence(session, business_type, expected):
    """Assert that the sequence value is generated successfully."""
    from business_model import LegalEntity

    if expected:
        first_val = LegalEntity.get_next_value_from_sequence(business_type)
        assert first_val

        next_val = LegalEntity.get_next_value_from_sequence(business_type)
        assert next_val
        assert next_val == first_val + 1

    else:
        assert not LegalEntity.get_next_value_from_sequence(business_type)


def test_continued_in_business(session):
    """Assert that the continued corp is saved successfully."""
    legal_entity =LegalEntity(
        legal_name='Test - Legal Name',
        entity_type='BC',
        founding_date=datetime.utcfromtimestamp(0),
        last_ledger_timestamp=datetime.utcfromtimestamp(0),
        dissolution_date=None,
        identifier='BC1234567',
        state=LegalEntity.State.ACTIVE,
        jurisdiction='CA',
        foreign_identifier='C1234567',
        foreign_legal_name='Prev Legal Name',
        foreign_legal_type='BEN',
        foreign_incorporation_date=datetime.utcfromtimestamp(0),
    )
    legal_entity.save()
    business_json = legal_entity.json()
    assert business_json['jurisdiction'] == legal_entity.jurisdiction
    assert business_json['foreignIdentifier'] == legal_entity.foreign_identifier
    assert business_json['foreignLegalName'] == legal_entity.foreign_legal_name
    assert business_json['foreignLegalType'] == legal_entity.foreign_legal_type
    assert business_json['foreignIncorporationDate'] == \
        LegislationDatetime.format_as_legislation_date(legal_entity.foreign_incorporation_date)
