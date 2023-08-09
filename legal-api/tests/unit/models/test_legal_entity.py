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
from flask import current_app

import datedelta
import pytest

from legal_api.exceptions import BusinessException
from legal_api.models import LegalEntity, EntityRole, ColinEntity, AlternateName
from legal_api.utils.legislation_datetime import LegislationDatetime
from tests import EPOCH_DATETIME, TIMEZONE_OFFSET
from tests.unit import has_expected_date_str_format


def factory_legal_entity(designation: str = '001'):
    """Return a valid Business object stamped with the supplied designation."""
    return LegalEntity(_legal_name=f'legal_name-{designation}',
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


def test_business_find_by_legal_name_pass(session):
    """Assert that the business can be found by name."""
    designation = '001'
    legal_name=f'legal_name-{str(uuid.uuid4().hex)}'
    legal_entity =LegalEntity(_legal_name=legal_name,
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
    legal_entity =LegalEntity(_legal_name=legal_name,
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
    legal_entity =LegalEntity(_legal_name=f'legal_name-{designation}',
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


def test_business_find_by_legal_name_no_database_connection(app_request):
    """Assert that None is return even if the database connection does not exist."""
    app_request.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://does:not@exist:5432/nada'
    with app_request.app_context():
        b = LegalEntity.find_by_legal_name('failure to find')
        assert b is None


def test_delete_business_with_dissolution(session):
    """Assert that the business can be found by name."""
    designation = '001'
    legal_entity =LegalEntity(_legal_name=f'legal_name-{designation}',
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
    legal_entity =LegalEntity(_legal_name=f'legal_name-{designation}',
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
    legal_entity =LegalEntity(_legal_name=f'legal_name-{designation}',
                        entity_type='CP',
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
    legal_entity =LegalEntity(_legal_name=f'legal_name-{designation}',
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
    legal_entity =LegalEntity(_legal_name=f'legal_name-{designation}',
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
    legal_entity =LegalEntity(_legal_name='legal_name',
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
        'businessName': 'legal_name',
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
    from legal_api.models import Address, Office

    legal_entity =LegalEntity(_legal_name='legal_name',
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
    from legal_api.models import LegalEntity

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
        _legal_name='Test - Legal Name',
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


@pytest.mark.parametrize(
    'entity_type',
    [
        ('CP'),
        ('BEN'),
        ('BC'),
        ('ULC'),
        ('CC')
    ]
)
def test_legal_name_non_firm(session, entity_type):
    """Assert that correct legal name returned for non-firm entity types."""
    legal_entity = LegalEntity(
        _legal_name='Test - Legal Name',
        entity_type=entity_type,
        founding_date=datetime.utcfromtimestamp(0),
        identifier='BC1234567',
        state=LegalEntity.State.ACTIVE
    )
    legal_entity.save()
    assert legal_entity.legal_name == 'Test - Legal Name'


@pytest.mark.parametrize(
    'test_name, firm_entity_type, partner_info, expected_legal_name',
    [
        ('SP_1_Person',
         LegalEntity.EntityTypes.SOLE_PROP.value,
         {
             'legalEntities': [
                 {
                     'entityType': LegalEntity.EntityTypes.PERSON.value,
                     'firstName': 'Jane',
                     'middleName': None,
                     'lastName': 'Doe'
                 }
             ],
             'colinEntities': []
         },
         'Jane Doe'),
        ('SP_1_Person',
         LegalEntity.EntityTypes.SOLE_PROP.value,
         {
             'legalEntities': [
                 {
                     'entityType': LegalEntity.EntityTypes.PERSON.value,
                     'firstName': 'John',
                     'middleName': 'jklasdf',
                     'lastName': 'Doe'
                 }
             ],
             'colinEntities': []
         },
         'John jklasdf Doe'),
        ('SP_1_Org',
         LegalEntity.EntityTypes.SOLE_PROP.value,
         {
             'legalEntities': [
                 {
                     'entityType': LegalEntity.EntityTypes.ORGANIZATION.value,
                     'organizationName': 'XYZ Studio'
                 }
             ],
             'colinEntities': []
         },
         'XYZ Studio'),
        ('SP_1_Colin_Org',
         LegalEntity.EntityTypes.SOLE_PROP.value,
         {
             'legalEntities': [],
             'colinEntities': [
                 { 'organizationName': 'ABC Labs' }
             ]
         },
         'ABC Labs'),
        ('GP_2_Partners-2_Persons',
         LegalEntity.EntityTypes.PARTNERSHIP.value,
         {
             'legalEntities': [
                 {
                     'entityType': LegalEntity.EntityTypes.PERSON.value,
                     'firstName': 'Jane',
                     'middleName': 'abc',
                     'lastName': 'Doe'
                 },
                 {
                     'entityType': LegalEntity.EntityTypes.PERSON.value,
                     'firstName': 'John',
                     'middleName': None,
                     'lastName': 'Doe'
                 }
             ],
             'colinEntities': []
         },
         'Jane abc Doe, John Doe'),
        ('GP_3_Partners-3_Persons',
         LegalEntity.EntityTypes.PARTNERSHIP.value,
         {
             'legalEntities': [
                 {
                     'entityType': LegalEntity.EntityTypes.PERSON.value,
                     'firstName': 'Jane',
                     'middleName': None,
                     'lastName': 'Doe'
                 },
                 {
                     'entityType': LegalEntity.EntityTypes.PERSON.value,
                     'firstName': 'John',
                     'middleName': None,
                     'lastName': 'Doe'
                 },
                 {
                     'entityType': LegalEntity.EntityTypes.PERSON.value,
                     'firstName': 'Jimmy',
                     'middleName': None,
                     'lastName': 'Doe'
                 }
             ],
             'colinEntities': []
         },
         'Jane Doe, Jimmy Doe, et al'),
        ('GP_2_Partners-2_Orgs',
         LegalEntity.EntityTypes.PARTNERSHIP.value,
         {
             'legalEntities': [
                 {
                     'entityType': LegalEntity.EntityTypes.ORGANIZATION.value,
                     'organizationName': 'XYZ Studio'
                 },
                 {
                     'entityType': LegalEntity.EntityTypes.ORGANIZATION.value,
                     'organizationName': 'ABC Studio'
                 }
             ],
             'colinEntities': []
         },
         'ABC Studio, XYZ Studio'),
        ('GP_3_Partners-3_Orgs',
         LegalEntity.EntityTypes.PARTNERSHIP.value,
         {
             'legalEntities': [
                 {
                     'entityType': LegalEntity.EntityTypes.ORGANIZATION.value,
                     'organizationName': 'XYZ Studio'
                 },
                 {
                     'entityType': LegalEntity.EntityTypes.ORGANIZATION.value,
                     'organizationName': 'XYZ Labs'
                 },
                 {
                     'entityType': LegalEntity.EntityTypes.ORGANIZATION.value,
                     'organizationName': 'XYZ Widgets'
                 }
             ],
             'colinEntities': []
         },
         'XYZ Labs, XYZ Studio, et al'),
        ('GP_2_Partners-1_Person_1_Org',
         LegalEntity.EntityTypes.PARTNERSHIP.value,
         {
             'legalEntities': [
                 {
                     'entityType': LegalEntity.EntityTypes.PERSON.value,
                     'firstName': 'Jimmy',
                     'middleName': None,
                     'lastName': 'Doe'
                 },
                 {
                     'entityType': LegalEntity.EntityTypes.ORGANIZATION.value,
                     'organizationName': 'XYZ Widgets'
                 }
             ],
             'colinEntities': []
         },
         'Jimmy Doe, XYZ Widgets'),
        ('GP_4_partners_2_Persons_2_Orgs',
         LegalEntity.EntityTypes.PARTNERSHIP.value,
         {
             'legalEntities': [
                 {
                     'entityType': LegalEntity.EntityTypes.PERSON.value,
                     'firstName': 'Jane',
                     'middleName': 'abc',
                     'lastName': 'Doe'
                 },
                 {
                     'entityType': LegalEntity.EntityTypes.PERSON.value,
                     'firstName': 'John',
                     'middleName': None,
                     'lastName': 'Doe'
                 },
                 {
                     'entityType': LegalEntity.EntityTypes.ORGANIZATION.value,
                     'organizationName': 'ABC Labs'
                 },
                 {
                     'entityType': LegalEntity.EntityTypes.ORGANIZATION.value,
                     'organizationName': 'XYZ Widgets'
                 }
             ],
             'colinEntities': []
         },
         'ABC Labs, Jane abc Doe, et al'),
        ('GP_2_Partners-2_Colin_Orgs',
         LegalEntity.EntityTypes.PARTNERSHIP.value,
         {
             'legalEntities': [],
             'colinEntities': [
                 { 'organizationName': 'ABC Labs' },
                 { 'organizationName': 'XYZ Labs' }
             ]
         },
         'ABC Labs, XYZ Labs'),
        ('GP_3_Partners-3_Colin_Orgs',
         LegalEntity.EntityTypes.PARTNERSHIP.value,
         {
             'legalEntities': [],
             'colinEntities': [
                 { 'organizationName': '111 Labs' },
                 { 'organizationName': '222 Labs' },
                 { 'organizationName': '333 Labs' }
             ]
         },
         '111 Labs, 222 Labs, et al'),
        ('GP_5_Partners-1_Person_2_Orgs_2_Colin_Orgs',
         LegalEntity.EntityTypes.PARTNERSHIP.value,
         {
             'legalEntities': [
                  {
                      'entityType': LegalEntity.EntityTypes.PERSON.value,
                      'firstName': 'Jane',
                      'middleName': 'abc',
                      'lastName': 'Doe'
                  },
                  {
                      'entityType': LegalEntity.EntityTypes.ORGANIZATION.value,
                      'organizationName': 'XYZ Studio'
                  },
                  {
                      'entityType': LegalEntity.EntityTypes.ORGANIZATION.value,
                      'organizationName': 'ABC Studio'
                  }
             ],
             'colinEntities': [
                 { 'organizationName': 'ABC Labs' },
                 { 'organizationName': 'XYZ Labs' }
             ]
         },
         'ABC Labs, ABC Studio, et al'),
    ]
)
def test_legal_name_firms(session, test_name, firm_entity_type, partner_info, expected_legal_name):
    """Assert that correct legal name returned for firms."""
    le_firm = LegalEntity(
        entity_type=firm_entity_type,
        founding_date=datetime.utcfromtimestamp(0),
        identifier='FM1234567',
        state=LegalEntity.State.ACTIVE
    )

    le_entries = partner_info.get('legalEntities')
    for le_entry in le_entries:
        entity_type = le_entry.get('entityType')
        le_partner = LegalEntity(
            entity_type=entity_type,
            founding_date=datetime.utcfromtimestamp(0),
            state=LegalEntity.State.ACTIVE
        )
        if entity_type == LegalEntity.EntityTypes.PERSON.value:
            le_partner.first_name = le_entry.get('firstName')
            le_partner.middle_initial = le_entry.get('middleName')
            le_partner.last_name = le_entry.get('lastName')
        else:
            le_partner._legal_name = le_entry.get('organizationName')
        le_partner.save()
        entity_role_partner = EntityRole(
            role_type=EntityRole.RoleTypes.partner.value,
            legal_entity_id=le_firm.id,
            appointment_date=datetime.utcfromtimestamp(0),
            related_entity_id=le_partner.id
        )
        le_firm.entity_roles.append(entity_role_partner)

    ce_entries = partner_info.get('colinEntities')
    for ce_entry in ce_entries:
        ce_partner = ColinEntity(organization_name=ce_entry.get('organizationName'))
        ce_partner.save()
        entity_role_partner = EntityRole(
            role_type=EntityRole.RoleTypes.partner.value,
            legal_entity_id=le_firm.id,
            appointment_date=datetime.utcfromtimestamp(0),
            related_colin_entity_id=ce_partner.id
        )
        le_firm.entity_roles.append(entity_role_partner)

    le_firm.save()

    assert le_firm.legal_name == expected_legal_name


@pytest.mark.parametrize(
    'entity_type, legal_name, operating_name, expected_business_name',
    [
        ('CP', 'CP Test XYZ', None, 'CP Test XYZ'),
        ('BEN', 'BEN Test XYZ', None, 'BEN Test XYZ'),
        ('BC', 'BC Test XYZ', None, 'BC Test XYZ'),
        ('ULC', 'ULC Test XYZ', None, 'ULC Test XYZ'),
        ('CC', 'CC Test XYZ', None, 'CC Test XYZ'),
        ('SP', None, 'SP Test XYZ', 'SP Test XYZ'),
        ('GP', None, 'GP Test XYZ', 'GP Test XYZ')
    ]
)
def test_business_name(session, entity_type, legal_name, operating_name, expected_business_name):
    """Assert that correct business name is returned."""
    le = LegalEntity(
        _legal_name=legal_name,
        entity_type=entity_type,
        founding_date=datetime.utcfromtimestamp(0),
        identifier='BC1234567',
        state=LegalEntity.State.ACTIVE
    )

    if operating_name:
        alternate_name = AlternateName(
            identifier='BC1234567',
            name_type=AlternateName.NameType.OPERATING,
            name=operating_name,
            bn15='111111100BC1111',
            start_date=datetime.utcnow(),
            legal_entity_id=le.id)
        alternate_name.save()
        le.alternate_names.append(alternate_name)

    le.save()

    assert le.business_name == expected_business_name




