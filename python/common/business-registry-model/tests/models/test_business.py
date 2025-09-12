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
import base64
import copy
import uuid
from datetime import datetime, timezone

import datedelta
import pytest
from flask import current_app
from registry_schemas.example_data import (
    FILING_HEADER,
    RESTORATION,
    TRANSITION_FILING_TEMPLATE,
)

from business_model.exceptions import BusinessException
from business_model.models import (
    AmalgamatingBusiness,
    Amalgamation,
    Batch,
    BatchProcessing,
    Business,
    Filing,
    Party,
    PartyRole,
    db,
)
from business_model.models.db import VersioningProxy
from business_model.utils.legislation_datetime import LegislationDatetime

# from business_model.services import flags
from tests import EPOCH_DATETIME, has_expected_date_str_format
from tests.models import factory_batch, factory_completed_filing, factory_party_role
from tests.models import factory_business as factory_business_from_tests


def random_str():
    return base64.urlsafe_b64encode(uuid.uuid4().bytes).decode().replace('=', '')


def factory_business(designation: str = '001'):
    """Return a valid Business object stamped with the supplied designation."""
    return Business(legal_name=f'legal_name-{designation}',
                    founding_date=datetime.fromtimestamp(0, timezone.utc),
                    last_ledger_timestamp=datetime.fromtimestamp(0, timezone.utc),
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
    ('BC123456789', False),
    ('C123456', False),
    ('12345678', False),
    ('1234567', False),
    ('123456', False),
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
    legal_name = random_str()
    business = Business(legal_name=legal_name,
                        founding_date=datetime.fromtimestamp(0, timezone.utc),
                        last_ledger_timestamp=datetime.fromtimestamp(0, timezone.utc),
                        dissolution_date=None,
                        identifier=f'CP1234{designation}',
                        tax_id=f'BN0000{designation}',
                        fiscal_year_end_date=datetime(2001, 8, 5, 7, 7, 58, 272362))
    session.add(business)
    session.commit()

    b = Business.find_by_legal_name(legal_name)
    assert b is not None


def test_business_find_by_legal_name_fail(session):
    """Assert that the business can not be found, once it is disolved."""
    legal_name = random_str()
    business = Business(
        legal_name=legal_name,
        founding_date=datetime.fromtimestamp(0, timezone.utc),
        last_ledger_timestamp=datetime.fromtimestamp(0, timezone.utc),
        dissolution_date=datetime.fromtimestamp(0, timezone.utc),
        identifier="CP3435367",
        tax_id="BN0000001",
        fiscal_year_end_date=datetime(2001, 8, 5, 7, 7, 58, 272362),
    )
    session.add(business)
    session.commit()

    # business is dissolved, it should not be found by name search
    b = Business.find_by_legal_name(legal_name)
    assert b is None


def test_business_find_by_legal_name_missing(session):
    """Assert that the business can be found by name."""
    designation = '001'
    business = Business(legal_name=f'legal_name-{designation}',
                        founding_date=datetime.fromtimestamp(0, timezone.utc),
                        last_ledger_timestamp=datetime.fromtimestamp(0, timezone.utc),
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
    app_request.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql+pg8000://does:not@exist:5432/nada'
    with app_request.app_context():
        b = Business.find_by_legal_name('failure to find')
        assert b is None


def test_delete_business_with_dissolution(session):
    """Assert that the business can be found by name."""
    designation = '001'
    business = Business(legal_name=f'legal_name-{designation}',
                        founding_date=datetime.fromtimestamp(0, timezone.utc),
                        last_ledger_timestamp=datetime.fromtimestamp(0, timezone.utc),
                        dissolution_date=datetime.fromtimestamp(0, timezone.utc),
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
                        founding_date=datetime.fromtimestamp(0, timezone.utc),
                        last_ledger_timestamp=datetime.fromtimestamp(0, timezone.utc),
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
    identifier = 'CP1213147'
    business = Business(legal_name=f'legal_name-{designation}',
                        founding_date=datetime.fromtimestamp(0, timezone.utc),
                        last_ledger_timestamp=datetime.fromtimestamp(0, timezone.utc),
                        dissolution_date=None,
                        identifier=identifier,
                        tax_id=f'BN0000{designation}',
                        fiscal_year_end_date=datetime(2001, 8, 5, 7, 7, 58, 272362))
    business.save()

    b = Business.find_by_identifier(identifier)

    assert b is not None


def test_business_find_by_identifier_no_identifier(session):
    """Assert that the business can be found by name."""
    designation = '001'
    business = Business(legal_name=f'legal_name-{designation}',
                        founding_date=datetime.fromtimestamp(0, timezone.utc),
                        last_ledger_timestamp=datetime.fromtimestamp(0, timezone.utc),
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
                        founding_date=datetime.fromtimestamp(0, timezone.utc),
                        last_ledger_timestamp=datetime.fromtimestamp(0, timezone.utc),
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


RESTORATION_FILING = copy.deepcopy(FILING_HEADER)
RESTORATION_FILING['filing']['restoration'] = RESTORATION


@pytest.mark.parametrize('test_name, has_no_transition_filed, good_standing', [
    ('NO_NEED_TRANSITION_NEW_ACT', False, True),
    ('NO_NEED_TRANSITION_BUT_IN_LIMITED_RESTORATION', False, False),
    ('TRANSITION_COMPLETED', False, True),
    ('TRANSITION_NOT_FILED', True, False)
])
def test_good_standing_check_transition_filing(session, test_name, has_no_transition_filed, good_standing):
    "Assert that the business is in good standing with additional check for transition filing"
    business = factory_business_from_tests(identifier='BC1234567', entity_type=Business.LegalTypes.COMP.value, last_ar_date=datetime.utcnow())
    restoration_filing = factory_completed_filing(business, RESTORATION_FILING, filing_type='restoration')
    if test_name == 'NO_NEED_TRANSITION_NEW_ACT':
        business.founding_date = datetime.utcnow()
        business.save()
    elif test_name == 'NO_NEED_TRANSITION_BUT_IN_LIMITED_RESTORATION':
        business.restoration_expiry_date = datetime.utcnow() + datedelta.datedelta(years=1)
        business.save()
        restoration_filing.effective_date = datetime.utcnow()
        restoration_filing.save()
    elif test_name == 'TRANSITION_COMPLETED':
        factory_completed_filing(business, TRANSITION_FILING_TEMPLATE, filing_type='transition')

    check_result = business._has_no_transition_filed_after_restoration()
    assert check_result == has_no_transition_filed
    # with patch.object(flags, 'is_on', return_value=True):
    #     assert business.good_standing == good_standing


def test_business_json(app, session):
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
                        tax_id='123456789',
                        no_dissolution=False
                        )
    # basic json
    base_url = current_app.config.get('LEGAL_API_BASE_URL')

    # slim json
    d_slim = {
        'adminFreeze': False,
        'foundingDate': '1970-01-01T00:00:00+00:00',
        'goodStanding': False,  # good standing will be false because the epoch is 1970
        'identifier': 'CP1234567',
        'inDissolution': False,
        'inLiquidation': False,
        'legalName': 'legal_name',
        'legalType': Business.LegalTypes.COOP.value,
        'state': Business.State.ACTIVE.name,
        'lastModified': EPOCH_DATETIME.isoformat(),
        'taxId': '123456789'
    }

    # with patch.object(flags, 'is_on', return_value=True):
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
        'allowedActions': {},
        'noDissolution': False,
        'alternateNames': []
    }

    # with patch.object(flags, 'is_on', return_value=True):
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

    #     # include fiscalYearEndDate
    business.fiscal_year_end_date = EPOCH_DATETIME
    d['fiscalYearEndDate'] = datetime.date(business.fiscal_year_end_date).isoformat()
    assert business.json() == d
    business.fiscal_year_end_date = None
    d.pop('fiscalYearEndDate')

    #     # include taxId
    business.tax_id = '123456789'
    d['taxId'] = business.tax_id
    assert business.json() == d


ALTERNATE_NAME_1 = "operating name 1"
ALTERNATE_NAME_1_IDENTIFIER = "FM1111111"
ALTERNATE_NAME_1_START_DATE = "2023-09-02"
ALTERNATE_NAME_1_START_DATE_ISO = "2023-09-02T07:00:00+00:00"
ALTERNATE_NAME_1_REGISTERED_DATE = "2000-01-01"
ALTERNATE_NAME_1_REGISTERED_DATE_ISO = "2000-01-01T07:00:00+00:00"

ALTERNATE_NAME_2 = "operating name 2"
ALTERNATE_NAME_2_IDENTIFIER = "FM2222222"
ALTERNATE_NAME_2_START_DATE = "2023-09-05"
ALTERNATE_NAME_2_START_DATE_ISO = "2023-09-05T07:00:00+00:00"
ALTERNATE_NAME_2_REGISTERED_DATE = "2005-01-01"
ALTERNATE_NAME_2_REGISTERED_DATE_ISO = "2005-01-01T07:00:00+00:00"


@pytest.mark.parametrize(
    "test_name, businesses_info, alternate_names_info, expected_alternate_names",
    [
        (
            "NO_ALTERNATE_NAMES_NON_FIRMS",
            [
                {"identifier": "CP1234567", "legalType": "CP", "legalName": "CP Test XYZ"},
                {"identifier": "BC1234567", "legalType": "BEN", "legalName": "BEN Test XYZ"},
                {"identifier": "BC1234567", "legalType": "BC", "legalName": "BC Test XYZ"},
                {"identifier": "BC1234567", "legalType": "ULC", "legalName": "ULC Test XYZ"},
                {"identifier": "BC1234567", "legalType": "CC", "legalName": "CCC Test XYZ"},
            ],
            [],
            [],
        ),
        (
            "ALTERNATE_NAMES_NON_FIRMS",
            # business_info
            [
                {"identifier": "CP1234567", "legalType": "CP", "legalName": "CP Test XYZ"},
                {"identifier": "BC1234567", "legalType": "BEN", "legalName": "BEN Test XYZ"},
                {"identifier": "BC1234567", "legalType": "BC", "legalName": "BC Test XYZ"},
                {"identifier": "BC1234567", "legalType": "ULC", "legalName": "ULC Test XYZ"},
                {"identifier": "BC1234567", "legalType": "CC", "legalName": "CCC Test XYZ"},
            ],
            # alternate_names_info
            [
                {
                    "identifier": ALTERNATE_NAME_1_IDENTIFIER,
                    "entityType": "SP",
                    "name": ALTERNATE_NAME_1,
                    "registeredDate": ALTERNATE_NAME_1_REGISTERED_DATE_ISO,
                    "startDate": ALTERNATE_NAME_1_START_DATE_ISO,
                },
            ],
            # expected_alternate_names
            [
                {
                    "identifier": ALTERNATE_NAME_1_IDENTIFIER,
                    "entityType": "SP",
                    "registeredDate": ALTERNATE_NAME_1_REGISTERED_DATE_ISO,
                    "startDate": ALTERNATE_NAME_1_START_DATE,
                    "name": ALTERNATE_NAME_1,
                    "type": "DBA",
                },
            ],
        ),
        (
            "ALTERNATE_NAMES_FIRMS_SP",
            # business_info
            [
                {
                    "identifier": ALTERNATE_NAME_1_IDENTIFIER,
                    "legalType": "SP",
                    "legalName": ALTERNATE_NAME_1,
                    "foundingDate": ALTERNATE_NAME_1_REGISTERED_DATE_ISO,
                }
            ],
            # alternate_names_info
            [
                {
                    "identifier": ALTERNATE_NAME_2_IDENTIFIER,
                    "entityType": "SP",
                    "name": ALTERNATE_NAME_2,
                    "registeredDate": ALTERNATE_NAME_2_REGISTERED_DATE_ISO,
                    "startDate": ALTERNATE_NAME_2_START_DATE_ISO,
                }
            ],
            # expected_alternate_names
            [
                {
                    "identifier": ALTERNATE_NAME_1_IDENTIFIER,
                    "entityType": "SP",
                    "registeredDate": ALTERNATE_NAME_1_REGISTERED_DATE_ISO,
                    "startDate": None,
                    "name": ALTERNATE_NAME_1,
                    "type": "DBA",
                }
            ],
        ),
        (
            "ALTERNATE_NAMES_FIRMS_GP",
            # business_info
            [
                {
                    "identifier": ALTERNATE_NAME_2_IDENTIFIER,
                    "legalType": "GP",
                    "legalName": ALTERNATE_NAME_2,
                    "foundingDate": ALTERNATE_NAME_2_REGISTERED_DATE_ISO,
                }
            ],
            # alternate_names_info
            [
                {
                    "identifier": ALTERNATE_NAME_2_IDENTIFIER,
                    "entityType": "GP",
                    "name": ALTERNATE_NAME_2,
                    "registeredDate": ALTERNATE_NAME_2_REGISTERED_DATE_ISO,
                    "startDate": ALTERNATE_NAME_2_START_DATE_ISO,
                }
            ],
            # expected_alternate_names
            [
                {
                    "identifier": ALTERNATE_NAME_2_IDENTIFIER,
                    "entityType": "GP",
                    "registeredDate": ALTERNATE_NAME_2_REGISTERED_DATE_ISO,
                    "startDate": None,
                    "name": ALTERNATE_NAME_2,
                    "type": "DBA",
                }
            ],
        ),
        # tests scenario where GP has 2 operating names:
        # 1. operating name for GP when firm first created
        # 2. operating name for SP that it owns
        (
            "ALTERNATE_NAMES_FIRMS_GP_MULTIPLE_NAMES",
            # business_info
            [
                {
                    "identifier": ALTERNATE_NAME_1_IDENTIFIER,
                    "legalType": "GP",
                    "legalName": ALTERNATE_NAME_1,
                    "foundingDate": ALTERNATE_NAME_1_REGISTERED_DATE_ISO,
                }
            ],
            # alternate_names_info
            [
                {
                    "identifier": ALTERNATE_NAME_1_IDENTIFIER,
                    "entityType": "GP",
                    "name": ALTERNATE_NAME_1,
                    "registeredDate": ALTERNATE_NAME_1_REGISTERED_DATE_ISO,
                    "startDate": ALTERNATE_NAME_1_START_DATE_ISO,
                },
                {
                    "identifier": ALTERNATE_NAME_2_IDENTIFIER,
                    "entityType": "SP",
                    "name": ALTERNATE_NAME_2,
                    "registeredDate": ALTERNATE_NAME_2_REGISTERED_DATE_ISO,
                    "startDate": ALTERNATE_NAME_2_START_DATE_ISO,
                },
            ],
            # expected_alternate_names
            [
                {
                    "identifier": ALTERNATE_NAME_2_IDENTIFIER,
                    "entityType": "SP",
                    "registeredDate": ALTERNATE_NAME_2_REGISTERED_DATE_ISO,
                    "startDate": ALTERNATE_NAME_2_START_DATE,
                    "name": ALTERNATE_NAME_2,
                    "type": "DBA",
                },
                {
                    "identifier": ALTERNATE_NAME_1_IDENTIFIER,
                    "entityType": "GP",
                    "registeredDate": ALTERNATE_NAME_1_REGISTERED_DATE_ISO,
                    "startDate": None,
                    "name": ALTERNATE_NAME_1,
                    "type": "DBA",
                },
            ],
        ),
    ],
)
def test_business_alternate_names(session, test_name, businesses_info, alternate_names_info, expected_alternate_names):
    """Assert that the business' alternate names are correct."""
    for business_info in businesses_info:
        session.begin_nested()
        founding_date_str = business_info.get("foundingDate")
        start_date_str = business_info.get("startDate")
        founding_date = datetime.strptime(business_info["foundingDate"], "%Y-%m-%dT%H:%M:%S%z") if founding_date_str else datetime.fromtimestamp(0, timezone.utc)
        start_date = datetime.strptime(business_info["startDate"], "%Y-%m-%dT%H:%M:%S%z") if start_date_str else None

        business = Business(
            legal_name=business_info["legalName"],
            legal_type=business_info["legalType"],
            founding_date=founding_date,
            start_date=start_date,
            identifier=business_info["identifier"],
            state=Business.State.ACTIVE
        )
        session.add(business)

        for alternate_name_info in alternate_names_info:
            business_alternate_name = Business(
                legal_name=alternate_name_info["name"],
                legal_type=alternate_name_info["entityType"],
                founding_date=datetime.strptime(alternate_name_info["registeredDate"], "%Y-%m-%dT%H:%M:%S%z"),
                start_date=datetime.strptime(alternate_name_info["startDate"], "%Y-%m-%dT%H:%M:%S%z"),
                identifier=alternate_name_info["identifier"],
                state=Business.State.ACTIVE
            )
            session.add(business_alternate_name)
            session.flush()

            if alternate_name_info["entityType"] == Business.LegalTypes.SOLE_PROP:
                party = Party(
                    party_type=Party.PartyTypes.ORGANIZATION.value,
                    identifier=business_info["identifier"],
                    organization_name=business_info["legalName"]
                )
                session.add(party)

                party_role = PartyRole(
                    role=PartyRole.RoleTypes.PROPRIETOR.value,
                    business_id=business_alternate_name.id,
                    party=party
                )
                session.add(party_role)

        session.flush()

        # with patch.object(flags, 'is_on', return_value=True):
        #     business_json = business.json()
        # assert 'alternateNames' in business_json
        # assert business_json['alternateNames'] == expected_alternate_names
        session.rollback()


def test_business_relationships_json(session):
    """Assert that the business model is saved correctly."""
    from business_model.models import Address, Office

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
    from business_model.models import Business

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
        founding_date=datetime.fromtimestamp(0, timezone.utc),
        last_ledger_timestamp=datetime.fromtimestamp(0, timezone.utc),
        dissolution_date=None,
        identifier='BC2123247',
        state=Business.State.ACTIVE,
        jurisdiction='CA',
        foreign_legal_name='Prev Legal Name',
    )
    business.save()
    business_json = business.json()
    assert business_json['jurisdiction'] == business.jurisdiction
    assert business_json['foreignLegalName'] == business.foreign_legal_name


@pytest.mark.parametrize('test_name,existing_business_state', [
    ('EXIST', Business.State.HISTORICAL),
    ('NOT_EXIST', Business.State.ACTIVE),
])
def test_amalgamated_into_business_json(session, test_name, existing_business_state):
    """Assert that the amalgamated into is in json."""
    existing_business = Business(
        legal_name='Test - Amalgamating Legal Name',
        legal_type='BC',
        founding_date=datetime.fromtimestamp(0, timezone.utc),
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
        transaction_id = VersioningProxy.get_transaction_id(session())

        business = Business(
            legal_name='Test - Legal Name',
            legal_type='BC',
            founding_date=datetime.fromtimestamp(0, timezone.utc),
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

        filing.transaction_id = transaction_id
        filing.business_id = business.id
        filing.save()

    business_json = existing_business.json()

    if test_name == 'EXIST':
        assert 'stateFiling' not in business_json
        assert 'amalgamatedInto' in business_json
        assert business_json['amalgamatedInto']['amalgamationDate'] == amalgamation.amalgamation_date.isoformat()
        assert business_json['amalgamatedInto']['amalgamationType'] == amalgamation.amalgamation_type.name
        assert business_json['amalgamatedInto']['courtApproval'] == amalgamation.court_approval
        assert business_json['amalgamatedInto']['identifier'] == business.identifier
        assert business_json['amalgamatedInto']['legalName'] == business.legal_name
    else:
        assert 'amalgamatedInto' not in business_json


@pytest.mark.parametrize('test_name, legal_type', [
    ('GP', 'GP'),
    ('GP_MORE_PARTNERS', 'GP'),
    ('SP', 'SP'),
    ('NON_FIRM', 'BC'),
])
def test_firm_business_json(session, test_name, legal_type):
    """Assert that correct legal name is in json (legal name easy fix)."""
    business = Business(
        legal_name='TEST ABC',
        legal_type=legal_type,
        founding_date=datetime.fromtimestamp(0, timezone.utc),
        last_ledger_timestamp=datetime.fromtimestamp(0, timezone.utc),
        dissolution_date=None,
        identifier='BC1234567',
        state=Business.State.ACTIVE,
    )

    officer1 = {
        'firstName': 'Jane',
        'lastName': 'Doe',
        'middleInitial': 'A',
        'partyType': 'person',
        'organizationName': ''
    }
    officer2 = {
        'firstName': 'John',
        'lastName': 'Doe',
        'middleInitial': 'B',
        'partyType': 'person',
        'organizationName': ''
    }

    officer3 = {
        'firstName': 'John',
        'lastName': 'Doe',
        'middleInitial': 'C',
        'partyType': 'person',
        'organizationName': ''
    }

    if legal_type == Business.LegalTypes.SOLE_PROP:
        proprietor_role = factory_party_role(None, None, officer1, None, None, PartyRole.RoleTypes.PROPRIETOR)
        business.party_roles.append(proprietor_role)
    elif legal_type == Business.LegalTypes.PARTNERSHIP:
        partner_role1 = factory_party_role(None, None, officer1, None, None, PartyRole.RoleTypes.PARTNER)
        partner_role2 = factory_party_role(None, None, officer2, None, None, PartyRole.RoleTypes.PARTNER)
        business.party_roles.append(partner_role1)
        business.party_roles.append(partner_role2)

        if 'MORE_PARTNERS' in test_name:
            partner_role3 = factory_party_role(None, None, officer3, None, None, PartyRole.RoleTypes.PARTNER)
            business.party_roles.append(partner_role3)
    else:
        party_role = factory_party_role(None, None, officer1, None, None, PartyRole.RoleTypes.DIRECTOR)
        business.party_roles.append(party_role)

    business.save()

    business_json = business.json()
    if legal_type in [
        Business.LegalTypes.SOLE_PROP.value,
        Business.LegalTypes.PARTNERSHIP.value
    ]:
        if legal_type == Business.LegalTypes.SOLE_PROP.value:
            assert business_json['legalName'] == 'JANE A DOE'
        elif 'MORE_PARTNERS' in test_name:
            assert business_json['legalName'] == 'JANE A DOE, JOHN B DOE, et al'
        else:
            assert business_json['legalName'] == 'JANE A DOE, JOHN B DOE'
    else:
        assert business_json['legalName'] == 'TEST ABC'


@pytest.mark.parametrize(
    'test_name, is_testing_business_id, batch_status, batch_processing_status, expected',
    [
        ('test_valid_in_dissolution', False, Batch.BatchStatus.PROCESSING, BatchProcessing.BatchProcessingStatus.PROCESSING, True),
        ('test_batch_is_completed', False, Batch.BatchStatus.COMPLETED, BatchProcessing.BatchProcessingStatus.PROCESSING, False),
        ('test_batch_processing_completed', False, Batch.BatchStatus.PROCESSING, BatchProcessing.BatchProcessingStatus.COMPLETED, False),
        ('test_both_completed', False, Batch.BatchStatus.COMPLETED, BatchProcessing.BatchProcessingStatus.COMPLETED, False),
        ('test_no_matched_business_id', True, Batch.BatchStatus.PROCESSING, BatchProcessing.BatchProcessingStatus.PROCESSING, False),
        ('test_batch_processing_withdrawn', False, Batch.BatchStatus.PROCESSING, BatchProcessing.BatchProcessingStatus.WITHDRAWN, False)
    ])
def test_in_dissolution(session, test_name, is_testing_business_id, batch_status, batch_processing_status, expected):
    """Assert in_dissolution works as expected, did not test with different batch types, since at this moment we only have one option in the BatchType Enum"""
    if is_testing_business_id:
        business_identifier_in = 'BC1234567'
        business_identifier_not_in = 'BC7654321'
        business_in_dissolution = factory_business(business_identifier_in)
        business_in_dissolution.save()
        business_not_in_dissolution = factory_business(business_identifier_not_in)
        business_not_in_dissolution.save()
        batch = factory_batch()
        batch.save()
        batch_processing = BatchProcessing(
            batch_id=batch.id,
            business_id=business_in_dissolution.id,
            business_identifier=business_identifier_in,
            step=BatchProcessing.BatchProcessingStep.WARNING_LEVEL_2,
            status=batch_processing_status,
            notes=''
        )
        batch_processing.save()
        assert business_not_in_dissolution.in_dissolution is False
    else:
        business_identifier = 'BC1234567'
        business = factory_business(business_identifier)
        business.save()
        batch = Batch(
            batch_type=Batch.BatchType.INVOLUNTARY_DISSOLUTION,
            status=batch_status,
            size=3,
            notes=''
        )
        batch.save()
        batch_processing = BatchProcessing(
            batch_id=batch.id,
            business_id=business.id,
            business_identifier=business_identifier,
            step=BatchProcessing.BatchProcessingStep.WARNING_LEVEL_2,
            status=batch_processing_status,
            notes=''
        )
        batch_processing.save()
        assert business.in_dissolution is expected
