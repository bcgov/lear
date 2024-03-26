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
from contextlib import suppress
from datetime import date, datetime, timedelta

import datedelta
import pytest
from flask import current_app
from sqlalchemy_continuum import versioning_manager

from legal_api.exceptions import BusinessException
from legal_api.models import (
    AlternateName,
    AmalgamatingBusiness,
    Amalgamation,
    BusinessCommon,
    ColinEntity,
    EntityRole,
    Filing,
    LegalEntity,
    db,
)
from legal_api.utils.legislation_datetime import LegislationDatetime
from tests import EPOCH_DATETIME, TIMEZONE_OFFSET
from tests.unit import has_expected_date_str_format

ALTERNATE_NAME_1 = "operating name 1"
ALTERNATE_NAME_1_IDENTIFIER = "FM1111111"
ALTERNATE_NAME_1_START_DATE = "2023-09-02"
ALTERNATE_NAME_1_START_DATE_ISO = "2023-09-02T07:00:00+00:00"
ALTERNATE_NAME_1_REGISTERED_DATE = "2000-01-01T00:00:00+00:00"

ALTERNATE_NAME_2 = "operating name 2"
ALTERNATE_NAME_2_IDENTIFIER = "FM2222222"
ALTERNATE_NAME_2_START_DATE = "2023-09-05"
ALTERNATE_NAME_2_START_DATE_ISO = "2023-09-05T07:00:00+00:00"
ALTERNATE_NAME_2_REGISTERED_DATE = "2005-01-01T00:00:00+00:00"


def factory_legal_entity(designation: str = "001"):
    """Return a valid Business object stamped with the supplied designation."""
    return LegalEntity(
        _legal_name=f"legal_name-{designation}",
        founding_date=datetime.utcfromtimestamp(0),
        last_ledger_timestamp=datetime.utcfromtimestamp(0),
        dissolution_date=None,
        identifier="CP1234567",
        tax_id=f"BN0000{designation}",
        fiscal_year_end_date=datetime(2001, 8, 5, 7, 7, 58, 272362),
        state=LegalEntity.State.ACTIVE,
    )


def test_business_identifier(session):
    """Assert that setting the business identifier must be in a valid format."""
    from tests.conftest import not_raises

    valid_identifier = "CP1234567"
    invalid_identifier = "1234567"
    b = LegalEntity()

    with not_raises(BusinessException):
        b.identifier = valid_identifier

    with pytest.raises(BusinessException):
        b.identifier = invalid_identifier


TEST_IDENTIFIER_DATA = [
    ("CP1234567", "CP", True),
    ("CP0000000", "CP", False),
    ("CP000000A", "CP", False),
    ("AB0000001", "BC", False),
    (None, "person", True),
]


@pytest.mark.parametrize("identifier,entity_type,expected", TEST_IDENTIFIER_DATA)
def test_business_validate_identifier(entity_type, identifier, expected):
    """Assert that the identifier is validated correctly."""
    assert LegalEntity.validate_identifier(entity_type, identifier) is expected


def test_business(session):
    """Assert a valid business is stored correctly.

    Start with a blank database.
    """
    legal_entity = factory_legal_entity("001")
    legal_entity.save()

    assert legal_entity.id is not None
    assert legal_entity.state == LegalEntity.State.ACTIVE
    assert legal_entity.admin_freeze is False


def test_business_find_by_legal_name_pass(session):
    """Assert that the business can be found by name."""
    designation = "001"
    legal_name = f"legal_name-{str(uuid.uuid4().hex)}"
    legal_entity = LegalEntity(
        _legal_name=legal_name,
        founding_date=datetime.utcfromtimestamp(0),
        last_ledger_timestamp=datetime.utcfromtimestamp(0),
        dissolution_date=None,
        identifier=f"CP1234{designation}",
        tax_id=f"BN0000{designation}",
        fiscal_year_end_date=datetime(2001, 8, 5, 7, 7, 58, 272362),
    )
    session.add(legal_entity)
    session.commit()

    b = LegalEntity.find_by_legal_name(legal_name)
    assert b is not None


def test_business_find_by_legal_name_fail(session):
    """Assert that the business can not be found, once it is disolved."""
    legal_name = f"legal_name-{str(uuid.uuid4().hex)}"
    designation = "001"
    legal_entity = LegalEntity(
        _legal_name=legal_name,
        founding_date=datetime.utcfromtimestamp(0),
        last_ledger_timestamp=datetime.utcfromtimestamp(0),
        dissolution_date=datetime.utcfromtimestamp(0),
        identifier=f"CP1234{designation}",
        tax_id=f"BN0000{designation}",
        fiscal_year_end_date=datetime(2001, 8, 5, 7, 7, 58, 272362),
    )
    session.add(legal_entity)
    session.commit()

    # business is dissolved, it should not be found by name search
    b = LegalEntity.find_by_legal_name(legal_name)
    assert b is None


def test_business_find_by_legal_name_missing(session):
    """Assert that the business can be found by name."""
    designation = "001"
    legal_entity = LegalEntity(
        _legal_name=f"legal_name-{designation}",
        founding_date=datetime.utcfromtimestamp(0),
        last_ledger_timestamp=datetime.utcfromtimestamp(0),
        dissolution_date=None,
        identifier=f"CP1234{designation}",
        tax_id=f"BN0000{designation}",
        fiscal_year_end_date=datetime(2001, 8, 5, 7, 7, 58, 272362),
    )
    session.add(legal_entity)
    session.commit()

    b = LegalEntity.find_by_legal_name()
    assert b is None


def test_business_find_by_legal_name_no_database_connection(app_request):
    """Assert that None is return even if the database connection does not exist."""
    app_request.config["SQLALCHEMY_DATABASE_URI"] = "postgresql://does:not@exist:5432/nada"
    with app_request.app_context():
        b = LegalEntity.find_by_legal_name("failure to find")
        assert b is None


def test_delete_business_with_dissolution(session):
    """Assert that the business can be found by name."""
    designation = "001"
    legal_entity = LegalEntity(
        _legal_name=f"legal_name-{designation}",
        founding_date=datetime.utcfromtimestamp(0),
        last_ledger_timestamp=datetime.utcfromtimestamp(0),
        dissolution_date=datetime.utcfromtimestamp(0),
        identifier=f"CP1234{designation}",
        tax_id=f"BN0000{designation}",
        fiscal_year_end_date=datetime(2001, 8, 5, 7, 7, 58, 272362),
    )
    legal_entity.save()

    b = legal_entity.delete()

    assert b.id == legal_entity.id


def test_delete_business_active(session):
    """Assert that the business can be found by name."""
    designation = "001"
    legal_entity = LegalEntity(
        _legal_name=f"legal_name-{designation}",
        founding_date=datetime.utcfromtimestamp(0),
        last_ledger_timestamp=datetime.utcfromtimestamp(0),
        dissolution_date=None,
        identifier="CP1234567",
        tax_id="XX",
        fiscal_year_end_date=datetime(2001, 8, 5, 7, 7, 58, 272362),
    )
    legal_entity.save()

    b = legal_entity.delete()

    assert b.id == legal_entity.id


def test_business_find_by_identifier(session):
    """Assert that the business can be found by name."""
    designation = "001"
    identifier = "CP0000001"
    legal_entity = LegalEntity(
        _legal_name=f"legal_name-{designation}",
        entity_type="CP",
        founding_date=datetime.utcfromtimestamp(0),
        last_ledger_timestamp=datetime.utcfromtimestamp(0),
        dissolution_date=None,
        identifier=identifier,
        tax_id=f"BN0000{designation}",
        fiscal_year_end_date=datetime(2001, 8, 5, 7, 7, 58, 272362),
    )
    legal_entity.save()

    b = LegalEntity.find_by_identifier(identifier)

    assert b is not None


def test_business_find_by_identifier_no_identifier(session):
    """Assert that the business can be found by name."""
    designation = "001"
    legal_entity = LegalEntity(
        _legal_name=f"legal_name-{designation}",
        founding_date=datetime.utcfromtimestamp(0),
        last_ledger_timestamp=datetime.utcfromtimestamp(0),
        dissolution_date=None,
        identifier=f"CP1234{designation}",
        tax_id=f"BN0000{designation}",
        fiscal_year_end_date=datetime(2001, 8, 5, 7, 7, 58, 272362),
    )
    legal_entity.save()

    b = LegalEntity.find_by_identifier()

    assert b is None


TEST_GOOD_STANDING_DATA = [
    (
        datetime.now() - datedelta.datedelta(months=6),
        LegalEntity.EntityTypes.COMP,
        LegalEntity.State.ACTIVE.value,
        False,
        True,
    ),
    (
        datetime.now() - datedelta.datedelta(months=6),
        LegalEntity.EntityTypes.COMP,
        LegalEntity.State.ACTIVE.value,
        True,
        False,
    ),
    (
        datetime.now() - datedelta.datedelta(months=6),
        LegalEntity.EntityTypes.COMP,
        LegalEntity.State.HISTORICAL.value,
        False,
        True,
    ),
    (
        datetime.now() - datedelta.datedelta(years=1, months=6),
        LegalEntity.EntityTypes.COMP,
        LegalEntity.State.ACTIVE.value,
        False,
        False,
    ),
    (
        datetime.now() - datedelta.datedelta(years=1, months=6),
        LegalEntity.EntityTypes.SOLE_PROP,
        LegalEntity.State.ACTIVE.value,
        False,
        True,
    ),
    (
        datetime.now() - datedelta.datedelta(years=1, months=6),
        LegalEntity.EntityTypes.PARTNERSHIP,
        LegalEntity.State.ACTIVE.value,
        False,
        True,
    ),
    (
        datetime.now() - datedelta.datedelta(months=6),
        LegalEntity.EntityTypes.SOLE_PROP,
        LegalEntity.State.ACTIVE.value,
        False,
        True,
    ),
    (
        datetime.now() - datedelta.datedelta(months=6),
        LegalEntity.EntityTypes.PARTNERSHIP,
        LegalEntity.State.ACTIVE.value,
        False,
        True,
    ),
]


@pytest.mark.parametrize("last_ar_date, entity_type, state, limited_restoration, expected", TEST_GOOD_STANDING_DATA)
def test_good_standing(session, last_ar_date, entity_type, state, limited_restoration, expected):
    """Assert that the business is in good standing when conditions are met."""
    designation = "001"
    legal_entity = LegalEntity(
        _legal_name=f"legal_name-{designation}",
        founding_date=datetime.utcfromtimestamp(0),
        last_ledger_timestamp=datetime.utcfromtimestamp(0),
        dissolution_date=None,
        identifier=f"CP1234{designation}",
        entity_type=entity_type,
        state=state,
        tax_id=f"BN0000{designation}",
        fiscal_year_end_date=datetime(2001, 8, 5, 7, 7, 58, 272362),
        last_ar_date=last_ar_date,
        restoration_expiry_date=datetime.utcnow() if limited_restoration else None,
    )
    legal_entity.save()

    assert legal_entity.good_standing is expected


def test_business_json(session):
    """Assert that the business model is saved correctly."""
    legal_entity = LegalEntity(
        _legal_name="legal_name",
        entity_type="CP",
        founding_date=EPOCH_DATETIME,
        start_date=datetime(2021, 8, 5, 8, 7, 58, 272362),
        last_ledger_timestamp=EPOCH_DATETIME,
        identifier="CP1234567",
        last_modified=EPOCH_DATETIME,
        last_ar_date=EPOCH_DATETIME,
        last_agm_date=EPOCH_DATETIME,
        restriction_ind=True,
        association_type="CP",
        # NB: default not intitialized since bus not committed before check
        state=LegalEntity.State.ACTIVE,
        tax_id="123456789",
    )
    # basic json
    # base_url = current_app.config.get("LEGAL_API_BASE_URL")

    # slim json
    d_slim = {
        "adminFreeze": False,
        "goodStanding": False,  # good standing will be false because the epoch is 1970
        "identifier": "CP1234567",
        "legalName": "legal_name",
        "legalType": LegalEntity.EntityTypes.COOP.value,
        "state": LegalEntity.State.ACTIVE.name,
        "taxId": "123456789",
        "alternateNames": [],
    }

    assert legal_entity.json(slim=True) == d_slim

    # remove taxId to test it doesn't show up again until the final test
    legal_entity.tax_id = None
    d_slim.pop("taxId")

    d = {
        **d_slim,
        "foundingDate": EPOCH_DATETIME.isoformat(),
        "lastAddressChangeDate": "",
        "lastDirectorChangeDate": "",
        "lastLedgerTimestamp": EPOCH_DATETIME.isoformat(),
        "lastModified": EPOCH_DATETIME.isoformat(),
        "lastAnnualReportDate": datetime.date(EPOCH_DATETIME).isoformat(),
        "lastAnnualGeneralMeetingDate": datetime.date(EPOCH_DATETIME).isoformat(),
        "naicsKey": None,
        "naicsCode": None,
        "naicsDescription": None,
        "nextAnnualReport": "1971-01-01T08:00:00+00:00",
        "hasRestrictions": True,
        "arMinDate": "1971-01-01",
        "arMaxDate": "1972-04-30",
        "complianceWarnings": [],
        "warnings": [],
        "hasCorrections": False,
        "associationType": "CP",
        "startDate": "2021-08-05",
        "hasCourtOrders": False,
        "allowedActions": {},
    }

    assert legal_entity.json() == d

    # include dissolutionDate
    legal_entity.dissolution_date = EPOCH_DATETIME
    d["dissolutionDate"] = LegislationDatetime.format_as_legislation_date(legal_entity.dissolution_date)
    business_json = legal_entity.json()
    assert business_json == d
    dissolution_date_str = business_json["dissolutionDate"]
    dissolution_date_format_correct = has_expected_date_str_format(dissolution_date_str, "%Y-%m-%d")
    assert dissolution_date_format_correct

    legal_entity.dissolution_date = None
    d.pop("dissolutionDate")

    # include fiscalYearEndDate
    legal_entity.fiscal_year_end_date = EPOCH_DATETIME
    d["fiscalYearEndDate"] = datetime.date(legal_entity.fiscal_year_end_date).isoformat()
    assert legal_entity.json() == d
    legal_entity.fiscal_year_end_date = None
    d.pop("fiscalYearEndDate")

    # include taxId
    legal_entity.tax_id = "123456789"
    d["taxId"] = legal_entity.tax_id
    assert legal_entity.json() == d


def test_business_relationships_json(session):
    """Assert that the business model is saved correctly."""
    from legal_api.models import Address, Office

    legal_entity = LegalEntity(
        _legal_name="legal_name",
        founding_date=EPOCH_DATETIME,
        last_ledger_timestamp=EPOCH_DATETIME,
        identifier="CP1234567",
        last_modified=EPOCH_DATETIME,
    )

    office = Office(office_type="registeredOffice")
    mailing_address = Address(city="Test City", address_type=Address.MAILING, legal_entity_id=legal_entity.id)
    office.addresses.append(mailing_address)
    legal_entity.offices.append(office)
    legal_entity.save()

    assert legal_entity.office_mailing_address.one_or_none()

    delivery_address = Address(city="Test City", address_type=Address.DELIVERY, legal_entity_id=legal_entity.id)
    office.addresses.append(delivery_address)
    legal_entity.save()

    assert legal_entity.office_delivery_address.one_or_none()


@pytest.mark.parametrize(
    "business_type,expected",
    [
        ("CP", True),
        ("NOT_FOUND", False),
    ],
)
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
    legal_entity = LegalEntity(
        _legal_name="Test - Legal Name",
        entity_type="BC",
        founding_date=datetime.utcfromtimestamp(0),
        last_ledger_timestamp=datetime.utcfromtimestamp(0),
        dissolution_date=None,
        identifier="BC1234567",
        state=LegalEntity.State.ACTIVE,
        jurisdiction="CA",
        foreign_identifier="C1234567",
        foreign_legal_name="Prev Legal Name",
        foreign_legal_type="BEN",
        foreign_incorporation_date=datetime.utcfromtimestamp(0),
    )
    legal_entity.save()
    business_json = legal_entity.json()
    assert business_json["jurisdiction"] == legal_entity.jurisdiction
    assert business_json["foreignIdentifier"] == legal_entity.foreign_identifier
    assert business_json["foreignLegalName"] == legal_entity.foreign_legal_name
    assert business_json["foreignLegalType"] == legal_entity.foreign_legal_type
    assert business_json["foreignIncorporationDate"] == LegislationDatetime.format_as_legislation_date(
        legal_entity.foreign_incorporation_date
    )


@pytest.mark.parametrize(
    "test_name,existing_business_state",
    [
        ("EXIST", LegalEntity.State.HISTORICAL),
        ("NOT_EXIST", LegalEntity.State.ACTIVE),
    ],
)
def test_amalgamated_into_business_json(session, test_name, existing_business_state):
    """Assert that the amalgamated into is in json."""
    existing_business = LegalEntity(
        _legal_name="Test - Amalgamating Legal Name",
        entity_type="BC",
        founding_date=datetime.utcfromtimestamp(0),
        dissolution_date=datetime.now(),
        identifier="BC1234567",
        state=LegalEntity.State.ACTIVE,
    )
    existing_business.save()

    if test_name == "EXIST":
        filing = Filing()
        filing._filing_type = "amalgamationApplication"
        filing.save()

        business = LegalEntity(
            _legal_name="Test - Legal Name",
            entity_type="BC",
            founding_date=datetime.utcfromtimestamp(0),
            identifier="BC1234568",
            state=LegalEntity.State.ACTIVE,
        )
        amalgamation = Amalgamation()
        amalgamation.filing_id = filing.id
        amalgamation.amalgamation_type = "regular"
        amalgamation.amalgamation_date = datetime.now()
        amalgamation.court_approval = True

        amalgamating_business = AmalgamatingBusiness()
        amalgamating_business.role = "amalgamating"
        amalgamating_business.legal_entity_id = existing_business.id
        amalgamation.amalgamating_businesses.append(amalgamating_business)

        business.amalgamation.append(amalgamation)
        db.session.add(business)
        existing_business.state_filing_id = filing.id
        existing_business.state = existing_business_state
        db.session.add(existing_business)
        db.session.commit()

        filing.legal_entity_id = business.id
        filing.save()

    business_json = existing_business.json()

    if test_name == "EXIST":
        assert "stateFiling" not in business_json
        assert "amalgamatedInto" in business_json
        assert business_json["amalgamatedInto"]["amalgamationDate"] == amalgamation.amalgamation_date.isoformat()
        assert business_json["amalgamatedInto"]["amalgamationType"] == amalgamation.amalgamation_type.name
        assert business_json["amalgamatedInto"]["courtApproval"] == amalgamation.court_approval
        assert business_json["amalgamatedInto"]["identifier"] == business.identifier
        assert business_json["amalgamatedInto"]["legalName"] == business.legal_name
    else:
        assert "amalgamatedInto" not in business_json


@pytest.mark.parametrize("entity_type", [("CP"), ("BEN"), ("BC"), ("ULC"), ("CC"), ("GP")])
def test_legal_name_non_SP(session, entity_type):
    """Assert that correct legal name returned for non-SP entity types."""
    legal_entity = LegalEntity(
        _legal_name="Test - Legal Name",
        entity_type=entity_type,
        founding_date=datetime.utcfromtimestamp(0),
        identifier="BC1234567",
        state=LegalEntity.State.ACTIVE,
    )
    legal_entity.save()
    assert legal_entity.legal_name == "Test - Legal Name"


@pytest.mark.parametrize(
    "test_name, partner_info, expected_legal_name",
    [
        (
            "SP_1_Person",
            {
                "legalEntities": [
                    {
                        "entityType": LegalEntity.EntityTypes.PERSON.value,
                        "firstName": "Jane",
                        "middleName": None,
                        "lastName": "Doe",
                    }
                ],
                "colinEntities": [],
            },
            "Jane Doe",
        ),
        (
            "SP_1_Person",
            {
                "legalEntities": [
                    {
                        "entityType": LegalEntity.EntityTypes.PERSON.value,
                        "firstName": "John",
                        "middleName": "jklasdf",
                        "lastName": "Doe",
                    }
                ],
                "colinEntities": [],
            },
            "John jklasdf Doe",
        ),
        (
            "SP_1_Org",
            {
                "legalEntities": [
                    {"entityType": LegalEntity.EntityTypes.ORGANIZATION.value, "organizationName": "XYZ Studio"}
                ],
                "colinEntities": [],
            },
            "XYZ Studio",
        ),
        (
            "SP_1_Colin_Org",
            {"legalEntities": [], "colinEntities": [{"organizationName": "ABC Labs"}]},
            "ABC Labs",
        ),
    ],
)
def test_legal_name_firms_SP(session, test_name, partner_info, expected_legal_name):
    """Assert that correct legal name returned for SP firms."""
    if partner_info:
        legal_entity_id = None
        colin_entity_id = None
        if le_entries := partner_info.get("legalEntities"):
            if len(le_entries) == 1 and (le_entry := le_entries[0]):
                entity_type = le_entry.get("entityType")
                le_partner = LegalEntity(
                    entity_type=entity_type, founding_date=datetime.utcfromtimestamp(0), state=LegalEntity.State.ACTIVE
                )
                if entity_type == LegalEntity.EntityTypes.PERSON.value:
                    first_name = le_entry.get("firstName")
                    middle_initial = le_entry.get("middleName")
                    last_name = le_entry.get("lastName")
                    person_full_name = ""
                    for token in [first_name, middle_initial, last_name]:
                        if token:
                            if len(person_full_name) > 0:
                                person_full_name = f"{person_full_name} {token}"
                            else:
                                person_full_name = token
                    le_partner._legal_name = person_full_name
                else:
                    le_partner._legal_name = le_entry.get("organizationName")
                le_partner.skip_party_listener = True
                le_partner.save()
                legal_entity_id = le_partner.id
        elif ce_entries := partner_info.get("colinEntities"):
            if len(ce_entries) == 1 and (ce_entry := ce_entries[0]):
                ce_partner = ColinEntity(organization_name=ce_entry.get("organizationName"))
                ce_partner.save()
                colin_entity_id = ce_partner.id

        sp_firm = AlternateName(
            identifier="FM1234567",
            name_type=AlternateName.NameType.DBA,
            name="OPERATING NAME",
            start_date=datetime.utcnow(),
            state=AlternateName.State.ACTIVE,
            legal_entity_id=legal_entity_id,
            colin_entity_id=colin_entity_id,
        )

        sp_firm.save()
        sp_firm.legal_name == expected_legal_name


@pytest.mark.parametrize(
    "entity_type, legal_name, expected_business_name",
    [
        ("CP", "CP Test XYZ", "CP Test XYZ"),
        ("BEN", "BEN Test XYZ", "BEN Test XYZ"),
        ("BC", "BC Test XYZ", "BC Test XYZ"),
        ("ULC", "ULC Test XYZ", "ULC Test XYZ"),
        ("CC", "CC Test XYZ", "CC Test XYZ"),
    ],
)
def test_business_name(session, entity_type, legal_name, expected_business_name):
    """Assert that correct business name is returned."""
    sess = session.begin_nested()
    le = LegalEntity(
        _legal_name=legal_name,
        entity_type=entity_type,
        founding_date=datetime.utcfromtimestamp(0),
        identifier="BC1234567",
        state=LegalEntity.State.ACTIVE,
    )

    le.skip_party_listener = True
    session.add(le)
    session.flush()
    assert le.business_name == expected_business_name

    sess.rollback()


@pytest.mark.parametrize(
    "test_name, legal_entities_info, alternate_names_info, expected_alternate_names",
    [
        # no operating names tests
        (
            "NO_ALTERNATE_NAMES_NON_FIRMS",
            [
                {"identifier": "CP1234567", "entityType": "CP", "legalName": "CP Test XYZ"},
                {"identifier": "BC1234567", "entityType": "BEN", "legalName": "BEN Test XYZ"},
                {"identifier": "BC1234567", "entityType": "BC", "legalName": "BC Test XYZ"},
                {"identifier": "BC1234567", "entityType": "ULC", "legalName": "ULC Test XYZ"},
                {"identifier": "BC1234567", "entityType": "CC", "legalName": "CCC Test XYZ"},
            ],
            None,
            [],
        ),
        # one or more operating names tests
        (
            "ALTERNATE_NAMES_NON_FIRMS",
            # legal_entity_info
            [
                {"identifier": "CP1234567", "entityType": "CP", "legalName": "CP Test XYZ"},
                {"identifier": "BC1234567", "entityType": "BEN", "legalName": "BEN Test XYZ"},
                {"identifier": "BC1234567", "entityType": "BC", "legalName": "BC Test XYZ"},
                {"identifier": "BC1234567", "entityType": "ULC", "legalName": "ULC Test XYZ"},
                {"identifier": "BC1234567", "entityType": "CC", "legalName": "CCC Test XYZ"},
            ],
            # alternate_names_info
            [
                {
                    "identifier": ALTERNATE_NAME_1_IDENTIFIER,
                    "entityType": "SP",
                    "operatingName": ALTERNATE_NAME_1,
                    "businessStartDate": ALTERNATE_NAME_1_START_DATE_ISO,
                    "startDate": ALTERNATE_NAME_1_REGISTERED_DATE,
                },
                {
                    "identifier": ALTERNATE_NAME_2_IDENTIFIER,
                    "entityType": "GP",
                    "operatingName": ALTERNATE_NAME_2,
                    "businessStartDate": ALTERNATE_NAME_2_START_DATE_ISO,
                    "startDate": ALTERNATE_NAME_2_REGISTERED_DATE,
                },
            ],
            # expected_alternate_names
            [
                {
                    "identifier": ALTERNATE_NAME_1_IDENTIFIER,
                    "operatingName": ALTERNATE_NAME_1,
                    "entityType": "SP",
                    "nameRegisteredDate": ALTERNATE_NAME_1_REGISTERED_DATE,
                    "nameStartDate": ALTERNATE_NAME_1_START_DATE,
                    "name": ALTERNATE_NAME_1,
                    "nameType": "DBA",
                },
                {
                    "identifier": ALTERNATE_NAME_2_IDENTIFIER,
                    "operatingName": ALTERNATE_NAME_2,
                    "entityType": "GP",
                    "nameRegisteredDate": ALTERNATE_NAME_2_REGISTERED_DATE,
                    "nameStartDate": ALTERNATE_NAME_2_START_DATE,
                    "name": ALTERNATE_NAME_2,
                    "nameType": "DBA",
                },
            ],
        ),
        (
            "ALTERNATE_NAMES_FIRMS_SP",
            # legal_entity_info
            [
                {
                    "identifier": ALTERNATE_NAME_1_IDENTIFIER,
                    "entityType": "SP",
                    "legalName": None,
                    "foundingDate": ALTERNATE_NAME_1_REGISTERED_DATE,
                }
            ],
            # alternate_names_info
            [
                {
                    "identifier": ALTERNATE_NAME_1_IDENTIFIER,
                    "entityType": "SP",
                    "operatingName": ALTERNATE_NAME_1,
                    "businessStartDate": ALTERNATE_NAME_1_START_DATE_ISO,
                    "startDate": ALTERNATE_NAME_1_REGISTERED_DATE,
                }
            ],
            # expected_alternate_names
            [
                {
                    "identifier": ALTERNATE_NAME_1_IDENTIFIER,
                    "operatingName": ALTERNATE_NAME_1,
                    "entityType": "SP",
                    "nameRegisteredDate": ALTERNATE_NAME_1_REGISTERED_DATE,
                    "nameStartDate": ALTERNATE_NAME_1_START_DATE,
                    "name": ALTERNATE_NAME_1,
                    "nameType": "DBA",
                }
            ],
        ),
        (
            "ALTERNATE_NAMES_FIRMS_GP",
            # legal_entity_info
            [
                {
                    "identifier": ALTERNATE_NAME_2_IDENTIFIER,
                    "entityType": "GP",
                    "legalName": None,
                    "foundingDate": ALTERNATE_NAME_2_REGISTERED_DATE,
                }
            ],
            # alternate_names_info
            [
                {
                    "identifier": ALTERNATE_NAME_2_IDENTIFIER,
                    "entityType": "GP",
                    "operatingName": ALTERNATE_NAME_2,
                    "businessStartDate": ALTERNATE_NAME_2_START_DATE_ISO,
                    "startDate": ALTERNATE_NAME_2_REGISTERED_DATE,
                }
            ],
            # expected_alternate_names
            [
                {
                    "identifier": ALTERNATE_NAME_2_IDENTIFIER,
                    "operatingName": ALTERNATE_NAME_2,
                    "entityType": "GP",
                    "nameRegisteredDate": ALTERNATE_NAME_2_REGISTERED_DATE,
                    "nameStartDate": ALTERNATE_NAME_2_START_DATE,
                    "name": ALTERNATE_NAME_2,
                    "nameType": "DBA",
                }
            ],
        ),
        # tests scenario where GP has 2 operating names:
        # 1. operating name for GP when firm first created
        # 2. operating name for SP that it owns
        (
            "ALTERNATE_NAMES_FIRMS_GP_MULTIPLE_NAMES",
            # legal_entity_info
            [
                {
                    "identifier": ALTERNATE_NAME_1_IDENTIFIER,
                    "entityType": "GP",
                    "legalName": None,
                    "foundingDate": ALTERNATE_NAME_1_REGISTERED_DATE,
                }
            ],
            # alternate_names_info
            [
                {
                    "identifier": ALTERNATE_NAME_1_IDENTIFIER,
                    "entityType": "GP",
                    "operatingName": ALTERNATE_NAME_1,
                    "businessStartDate": ALTERNATE_NAME_1_START_DATE_ISO,
                    "startDate": ALTERNATE_NAME_1_REGISTERED_DATE,
                },
                {
                    "identifier": ALTERNATE_NAME_2_IDENTIFIER,
                    "entityType": "SP",
                    "operatingName": ALTERNATE_NAME_2,
                    "businessStartDate": ALTERNATE_NAME_2_START_DATE_ISO,
                    "startDate": ALTERNATE_NAME_2_REGISTERED_DATE,
                },
            ],
            # expected_alternate_names
            [
                {
                    "identifier": ALTERNATE_NAME_1_IDENTIFIER,
                    "operatingName": ALTERNATE_NAME_1,
                    "entityType": "GP",
                    "nameRegisteredDate": ALTERNATE_NAME_1_REGISTERED_DATE,
                    "nameStartDate": ALTERNATE_NAME_1_START_DATE,
                    "name": ALTERNATE_NAME_1,
                    "nameType": "DBA",
                },
                {
                    "identifier": ALTERNATE_NAME_2_IDENTIFIER,
                    "operatingName": ALTERNATE_NAME_2,
                    "entityType": "SP",
                    "nameRegisteredDate": ALTERNATE_NAME_2_REGISTERED_DATE,
                    "nameStartDate": ALTERNATE_NAME_2_START_DATE,
                    "name": ALTERNATE_NAME_2,
                    "nameType": "DBA",
                },
            ],
        ),
    ],
)
def test_alternate_names(session, test_name, legal_entities_info, alternate_names_info, expected_alternate_names):
    """Assert that correct alternate name is returned."""
    for le_info in legal_entities_info:
        sess = session.begin_nested()
        founding_date_str = le_info.get("foundingDate")
        if founding_date_str:
            founding_date = datetime.strptime(founding_date_str, "%Y-%m-%dT%H:%M:%S%z")
        else:
            founding_date = datetime.utcfromtimestamp(0)

        le = LegalEntity(
            _legal_name=le_info["legalName"],
            entity_type=le_info["entityType"],
            founding_date=founding_date,
            identifier=le_info["identifier"],
        )
        session.add(le)

        if alternate_names_info:
            for alternate_name_info in alternate_names_info:
                business_start_date = datetime.strptime(alternate_name_info["businessStartDate"], "%Y-%m-%dT%H:%M:%S%z")

                alternate_name_identifier = alternate_name_info["identifier"]

                start_date = datetime.strptime(alternate_name_info["startDate"], "%Y-%m-%dT%H:%M:%S%z")
                if alternate_name_identifier != le.identifier:
                    le_alternate_name = LegalEntity(
                        entity_type=alternate_name_info["entityType"],
                        founding_date=start_date,
                        identifier=alternate_name_identifier,
                    )
                    session.add(le_alternate_name)

                alternate_name = AlternateName(
                    identifier=alternate_name_identifier,
                    name_type=AlternateName.NameType.DBA,
                    name=alternate_name_info["operatingName"],
                    bn15="111111100BC1111",
                    start_date=start_date,
                    business_start_date=business_start_date,
                    legal_entity_id=le.id,
                )
                le.alternate_names.append(alternate_name)

        session.flush()
        # TODO: once entity_type is added to the AlternateName model, confirm these tests pass.
        for expected_alternate_name in expected_alternate_names:
            assert any(
                alternate_name.json(slim=True)["alternateNames"][0] == expected_alternate_name
                for alternate_name in le.alternate_names
            )
        # if no rollback, test data conflicts between parametrized test runs
        sess.rollback()
