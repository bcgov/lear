# Copyright © 2022 Province of British Columbia
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in business with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Test suite to ensure Firms business checks work correctly."""
from contextlib import suppress
from datetime import datetime
from unittest.mock import patch

import pytest

from legal_api.models import Address, EntityRole, LegalEntity, Office, PartyRole
from legal_api.services.warnings.business.business_checks import BusinessWarningReferers, firms
from legal_api.services.warnings.business.business_checks.firms import (
    check_address,
    check_business,
    check_completing_party,
    check_completing_party_for_filing,
    check_gp_parties,
    check_gp_party,
    check_office,
    check_parties,
    check_sp_parties,
    check_sp_party,
    check_start_date,
)
from tests.unit.services.warnings import (
    create_business,
    create_filing,
    factory_address,
    factory_filing_role_organization,
    factory_filing_role_person,
    factory_legal_entity,
    factory_party_role_organization,
    factory_party_role_person,
    factory_party_roles,
)


@pytest.mark.parametrize(
    "test_name, address_type, null_addr_field_name, referer, expected_code, expected_msg",
    [
        # business office mailing address checks
        ("SUCCESS", "mailing", None, BusinessWarningReferers.BUSINESS_OFFICE, None, None),
        (
            "FAIL_NO_STREET",
            "mailing",
            "street",
            BusinessWarningReferers.BUSINESS_OFFICE,
            "NO_BUSINESS_OFFICE_MAILING_ADDRESS_STREET",
            "Street is required for business office mailing address.",
        ),
        (
            "FAIL_NO_CITY",
            "mailing",
            "city",
            BusinessWarningReferers.BUSINESS_OFFICE,
            "NO_BUSINESS_OFFICE_MAILING_ADDRESS_CITY",
            "City is required for business office mailing address.",
        ),
        (
            "FAIL_NO_COUNTRY",
            "mailing",
            "country",
            BusinessWarningReferers.BUSINESS_OFFICE,
            "NO_BUSINESS_OFFICE_MAILING_ADDRESS_COUNTRY",
            "Country is required for business office mailing address.",
        ),
        (
            "FAIL_NO_POSTAL_CODE",
            "mailing",
            "postal_code",
            BusinessWarningReferers.BUSINESS_OFFICE,
            "NO_BUSINESS_OFFICE_MAILING_ADDRESS_POSTAL_CODE",
            "Postal code is required for business office mailing address.",
        ),
        ("SUCCESS", "mailing", "region", BusinessWarningReferers.BUSINESS_OFFICE, None, None),
        # business office delivery address checks
        ("SUCCESS", "delivery", None, BusinessWarningReferers.BUSINESS_OFFICE, None, None),
        (
            "FAIL_NO_STREET",
            "delivery",
            "street",
            BusinessWarningReferers.BUSINESS_OFFICE,
            "NO_BUSINESS_OFFICE_DELIVERY_ADDRESS_STREET",
            "Street is required for business office delivery address.",
        ),
        (
            "FAIL_NO_CITY",
            "delivery",
            "city",
            BusinessWarningReferers.BUSINESS_OFFICE,
            "NO_BUSINESS_OFFICE_DELIVERY_ADDRESS_CITY",
            "City is required for business office delivery address.",
        ),
        (
            "FAIL_NO_COUNTRY",
            "delivery",
            "country",
            BusinessWarningReferers.BUSINESS_OFFICE,
            "NO_BUSINESS_OFFICE_DELIVERY_ADDRESS_COUNTRY",
            "Country is required for business office delivery address.",
        ),
        (
            "FAIL_NO_POSTAL_CODE",
            "delivery",
            "postal_code",
            BusinessWarningReferers.BUSINESS_OFFICE,
            "NO_BUSINESS_OFFICE_DELIVERY_ADDRESS_POSTAL_CODE",
            "Postal code is required for business office delivery address.",
        ),
        (
            "FAIL_NO_REGION",
            "delivery",
            "region",
            BusinessWarningReferers.BUSINESS_OFFICE,
            "NO_BUSINESS_OFFICE_DELIVERY_ADDRESS_REGION",
            "Region is required for business office delivery address.",
        ),
        # business office mailing address checks
        ("SUCCESS", "mailing", None, BusinessWarningReferers.BUSINESS_PARTY, None, None),
        (
            "FAIL_NO_STREET",
            "mailing",
            "street",
            BusinessWarningReferers.BUSINESS_PARTY,
            "NO_BUSINESS_PARTY_MAILING_ADDRESS_STREET",
            "Street is required for business party mailing address.",
        ),
        (
            "FAIL_NO_CITY",
            "mailing",
            "city",
            BusinessWarningReferers.BUSINESS_PARTY,
            "NO_BUSINESS_PARTY_MAILING_ADDRESS_CITY",
            "City is required for business party mailing address.",
        ),
        (
            "FAIL_NO_COUNTRY",
            "mailing",
            "country",
            BusinessWarningReferers.BUSINESS_PARTY,
            "NO_BUSINESS_PARTY_MAILING_ADDRESS_COUNTRY",
            "Country is required for business party mailing address.",
        ),
        (
            "FAIL_NO_POSTAL_CODE",
            "mailing",
            "postal_code",
            BusinessWarningReferers.BUSINESS_PARTY,
            "NO_BUSINESS_PARTY_MAILING_ADDRESS_POSTAL_CODE",
            "Postal code is required for business party mailing address.",
        ),
        ("SUCCESS", "mailing", "region", BusinessWarningReferers.BUSINESS_PARTY, None, None),
        # completing party mailing address checks
        ("SUCCESS", "mailing", None, BusinessWarningReferers.COMPLETING_PARTY, None, None),
        (
            "FAIL_NO_STREET",
            "mailing",
            "street",
            BusinessWarningReferers.COMPLETING_PARTY,
            "NO_COMPLETING_PARTY_MAILING_ADDRESS_STREET",
            "Street is required for completing party mailing address.",
        ),
        (
            "FAIL_NO_CITY",
            "mailing",
            "city",
            BusinessWarningReferers.COMPLETING_PARTY,
            "NO_COMPLETING_PARTY_MAILING_ADDRESS_CITY",
            "City is required for completing party mailing address.",
        ),
        (
            "FAIL_NO_COUNTRY",
            "mailing",
            "country",
            BusinessWarningReferers.COMPLETING_PARTY,
            "NO_COMPLETING_PARTY_MAILING_ADDRESS_COUNTRY",
            "Country is required for completing party mailing address.",
        ),
        (
            "FAIL_NO_POSTAL_CODE",
            "mailing",
            "postal_code",
            BusinessWarningReferers.COMPLETING_PARTY,
            "NO_COMPLETING_PARTY_MAILING_ADDRESS_POSTAL_CODE",
            "Postal code is required for completing party mailing address.",
        ),
        ("SUCCESS", "mailing", "region", BusinessWarningReferers.COMPLETING_PARTY, None, None),
    ],
)
def test_check_address(session, test_name, address_type, null_addr_field_name, referer, expected_code, expected_msg):
    """Assert that business address checks functions properly."""

    fail_testcase_names = ["FAIL_NO_STREET", "FAIL_NO_CITY", "FAIL_NO_COUNTRY", "FAIL_NO_POSTAL_CODE", "FAIL_NO_REGION"]

    if test_name == "SUCCESS":
        address = factory_address(address_type=address_type)
    elif test_name in (fail_testcase_names):
        address = factory_address(address_type=address_type, make_null_field_name=null_addr_field_name)
    result = check_address(address, address_type, referer)

    if expected_code:
        assert len(result) == 1
        business_warning = result[0]
        assert business_warning["code"] == expected_code
        assert business_warning["message"] == expected_msg
    else:
        assert len(result) == 0


@pytest.mark.parametrize(
    "test_name, legal_type, role, party_type, expected_code, expected_msg",
    [
        # SP tests
        ("SUCCESS", "SP", "proprietor", "person", None, None),
        ("SUCCESS", "SP", "proprietor", "organization", None, None),
        (
            "FAIL_NO_PERSON_NAME",
            "SP",
            "proprietor",
            "person",
            "NO_PROPRIETOR_PERSON_NAME",
            "Proprietor name is required.",
        ),
        (
            "FAIL_NO_ORG_NAME",
            "SP",
            "proprietor",
            "organization",
            "NO_PROPRIETOR_ORG_NAME",
            "Proprietor organization name is required.",
        ),
        # GP tests
        ("SUCCESS", "GP", "partner", "person", None, None),
        ("SUCCESS", "GP", "partner", "organization", None, None),
        ("FAIL_NO_PERSON_NAME", "GP", "partner", "person", "NO_PARTNER_PERSON_NAME", "Partner name is required."),
        (
            "FAIL_NO_ORG_NAME",
            "GP",
            "partner",
            "organization",
            "NO_PARTNER_ORG_NAME",
            "Partner organization name is required.",
        ),
    ],
)
def test_check_firm_party(session, test_name, legal_type, role, party_type, expected_code, expected_msg):
    """Assert that business firm party checks functions properly."""

    legal_entity = factory_legal_entity(legal_type, "BC1234567", 123)

    if party_type == "person":
        party_role = factory_party_role_person(legal_entity=legal_entity, role=role, custom_person_id=1111)
    elif party_type == "organization":
        party_role = factory_party_role_organization(legal_entity=legal_entity, role=role, custom_org_id=1111)

    if test_name == "FAIL_NO_PERSON_NAME":
        party_role.related_entity.first_name = None
        party_role.related_entity.last_name = None
    elif test_name == "FAIL_NO_ORG_NAME":
        party_role.related_colin_entity.organization_name = None

    with patch.object(firms, "check_address", return_value=[]):
        result = check_firm_party(legal_type, party_role)

    if expected_code:
        assert len(result) == 1
        business_warning = result[0]
        assert business_warning["code"] == expected_code
        assert business_warning["message"] == expected_msg
    else:
        assert len(result) == 0


@pytest.mark.parametrize(
    "test_name, legal_type, role, num_persons_roles, num_org_roles, expected_code, expected_msg",
    [
        # SP tests
        ("SUCCESS", "SP", EntityRole.RoleTypes.proprietor, 1, 0, None, None),
        ("SUCCESS", "SP", EntityRole.RoleTypes.proprietor, 0, 1, None, None),
        (
            "FAIL_PROPRIETOR_REQUIRED",
            "SP",
            EntityRole.RoleTypes.proprietor,
            0,
            0,
            "NO_PROPRIETOR",
            "A proprietor is required.",
        ),
        #
        # GP tests
        ("SUCCESS", "GP", EntityRole.RoleTypes.partner, 2, 0, None, None),
        ("SUCCESS", "GP", EntityRole.RoleTypes.partner, 0, 2, None, None),
        ("SUCCESS", "GP", EntityRole.RoleTypes.partner, 1, 1, None, None),
        ("FAIL_PARTNER_REQUIRED", "GP", EntityRole.RoleTypes.partner, 0, 0, "NO_PARTNER", "2 partners are required."),
        ("FAIL_PARTNER_REQUIRED", "GP", EntityRole.RoleTypes.partner, 1, 0, "NO_PARTNER", "2 partners are required."),
        ("FAIL_PARTNER_REQUIRED", "GP", EntityRole.RoleTypes.partner, 0, 1, "NO_PARTNER", "2 partners are required."),
    ],
)
def test_check_firm_parties(
    session, test_name, legal_type, role, num_persons_roles: int, num_org_roles: int, expected_code, expected_msg
):
    """Assert that business firm parties check functions properly."""

    party_roles = factory_party_roles(role, num_persons_roles, num_org_roles)

    with patch.object(firms, "check_firm_party", return_value=[]):
        result = check_firm_parties(legal_type, party_roles)

    if expected_code:
        assert len(result) == 1
        business_warning = result[0]
        assert business_warning["code"] == expected_code
        assert business_warning["message"] == expected_msg
    else:
        assert len(result) == 0


@pytest.mark.parametrize(
    "test_name, role, party_type, expected_code, expected_msg",
    [
        ("SUCCESS", "completing_party", "person", None, None),
        ("SUCCESS", "completing_party", "organization", None, None),
        (
            "FAIL_NO_PERSON_NAME",
            "completing_party",
            "person",
            "NO_COMPLETING_PARTY_PERSON_NAME",
            "Completing Party name is required.",
        ),
        (
            "FAIL_NO_ORG_NAME",
            "completing_party",
            "organization",
            "NO_COMPLETING_PARTY_ORG_NAME",
            "Completing Party organization name is required.",
        ),
    ],
)
def test_check_completing_party(session, test_name, role, party_type, expected_code, expected_msg):
    """Assert that business firm party checks functions properly."""

    filing_id = 55555

    if party_type == "person":
        party_role = factory_filing_role_person(filing_id=filing_id, role=role, custom_person_id=1111)
    elif party_type == "organization":
        party_role = factory_filing_role_organization(filing_id=filing_id, role=role, custom_org_id=99999)

    if test_name == "FAIL_NO_PERSON_NAME":
        party_role.legal_entity.first_name = None
        party_role.legal_entity.last_name = None
    elif test_name == "FAIL_NO_ORG_NAME":
        party_role.related_colin_entity.organization_name = None

    with patch.object(firms, "check_address", return_value=[]):
        result = check_completing_party(party_role)

    if expected_code:
        assert len(result) == 1
        business_warning = result[0]
        assert business_warning["code"] == expected_code
        assert business_warning["message"] == expected_msg
    else:
        assert len(result) == 0


@pytest.mark.parametrize(
    "test_name, filing_type, expected_code, expected_msg",
    [
        ("SUCCESS", "registration", None, None),
        ("SUCCESS", "conversion", None, None),
        ("FAIL_NO_COMPLETING_PARTY", "registration", "NO_COMPLETING_PARTY", "A completing party is required."),
        ("FAIL_NO_COMPLETING_PARTY", "conversion", "NO_COMPLETING_PARTY", "A completing party is required."),
    ],
)
def test_check_completing_party_for_filing(session, test_name, filing_type, expected_code, expected_msg):
    """Assert that business firm parties check functions properly."""

    filing = None
    if test_name == "SUCCESS":
        filing = create_filing(filing_type=filing_type, add_completing_party=True)
    elif test_name == "FAIL_NO_COMPLETING_PARTY":
        filing = create_filing(filing_type=filing_type, add_completing_party=False)

    with patch.object(firms, "check_completing_party", return_value=[]):
        result = check_completing_party_for_filing(filing)

    if expected_code:
        assert len(result) == 1
        business_warning = result[0]
        assert business_warning["code"] == expected_code
        assert business_warning["message"] == expected_msg
    else:
        assert len(result) == 0


@pytest.mark.parametrize(
    "test_name, legal_type, identifier, num_persons_roles, num_org_roles, filing_types, filing_has_completing_party, \
        expected_code, expected_msg",
    [
        # SP tests
        ("SUCCESS", "SP", "FM0000001", 1, 0, ["registration"], [True], None, None),
        ("SUCCESS", "SP", "FM0000001", 0, 1, ["registration"], [True], None, None),
        ("SUCCESS", "SP", "FM0000001", 1, 0, ["registration", "conversion"], [False, True], None, None),
        ("SUCCESS", "SP", "FM0000001", 0, 1, ["registration", "conversion"], [False, True], None, None),
        (
            "FAIL_NO_PROPRIETOR",
            "SP",
            "FM0000001",
            0,
            0,
            ["registration"],
            [True],
            "NO_PROPRIETOR",
            "A proprietor is required.",
        ),
        (
            "NO_COMPLETING_PARTY",
            "SP",
            "FM0000001",
            1,
            0,
            ["registration"],
            [False],
            "NO_COMPLETING_PARTY",
            "A completing party is required.",
        ),
        (
            "NO_COMPLETING_PARTY",
            "SP",
            "FM0000001",
            0,
            1,
            ["registration"],
            [False],
            "NO_COMPLETING_PARTY",
            "A completing party is required.",
        ),
        # GP tests
        ("SUCCESS", "GP", "FM0000001", 2, 0, ["registration"], [True], None, None),
        ("SUCCESS", "GP", "FM0000001", 0, 2, ["registration"], [True], None, None),
        ("SUCCESS", "GP", "FM0000001", 1, 1, ["registration"], [True], None, None),
        ("SUCCESS", "GP", "FM0000001", 2, 0, ["registration", "conversion"], [False, True], None, None),
        ("SUCCESS", "GP", "FM0000001", 0, 2, ["registration", "conversion"], [False, True], None, None),
        ("SUCCESS", "GP", "FM0000001", 1, 1, ["registration", "conversion"], [False, True], None, None),
        (
            "FAIL_NO_PARTNER",
            "GP",
            "FM0000001",
            0,
            0,
            ["registration"],
            [True],
            "NO_PARTNER",
            "2 partners are required.",
        ),
        (
            "FAIL_NO_PARTNER",
            "GP",
            "FM0000001",
            1,
            0,
            ["registration"],
            [True],
            "NO_PARTNER",
            "2 partners are required.",
        ),
        (
            "FAIL_NO_PARTNER",
            "GP",
            "FM0000001",
            0,
            1,
            ["registration"],
            [True],
            "NO_PARTNER",
            "2 partners are required.",
        ),
        (
            "NO_COMPLETING_PARTY",
            "GP",
            "FM0000001",
            2,
            0,
            ["registration"],
            [False],
            "NO_COMPLETING_PARTY",
            "A completing party is required.",
        ),
        (
            "NO_COMPLETING_PARTY",
            "GP",
            "FM0000001",
            0,
            2,
            ["registration"],
            [False],
            "NO_COMPLETING_PARTY",
            "A completing party is required.",
        ),
        (
            "NO_COMPLETING_PARTY",
            "GP",
            "FM0000001",
            1,
            1,
            ["registration"],
            [False],
            "NO_COMPLETING_PARTY",
            "A completing party is required.",
        ),
    ],
)
def test_check_parties(
    session,
    test_name,
    legal_type,
    identifier,
    num_persons_roles: int,
    num_org_roles: int,
    filing_types: list,
    filing_has_completing_party: list,
    expected_code,
    expected_msg,
):
    """Assert that business firm parties check functions properly."""

    with suppress(Exception):
        sess = session.begin_nested()
        legal_entity = None

        create_business(
            entity_type=legal_type,
            identifier=identifier,
            firm_num_persons_roles=num_persons_roles,
            firm_num_org_roles=num_org_roles,
            filing_types=filing_types,
            filing_has_completing_party=filing_has_completing_party,
        )

        legal_entity = LegalEntity.find_by_identifier(identifier)
        assert legal_entity
        assert legal_entity.entity_type == legal_type
        assert legal_entity.identifier == identifier

        with patch.object(firms, "check_address", return_value=[]):
            result = check_parties(legal_type, legal_entity)

        if expected_code:
            assert len(result) == 1
            business_warning = result[0]
            assert business_warning["code"] == expected_code
            assert business_warning["message"] == expected_msg
        else:
            assert len(result) == 0

        sess.rollback()


@pytest.mark.parametrize(
    "test_name, legal_type, identifier, has_office, num_persons_roles, num_org_roles, filing_types, \
        filing_has_completing_party, expected_code, expected_msg",
    [
        # SP tests
        ("SUCCESS", "SP", "FM0000001", True, 1, 0, ["registration"], [True], None, None),
        ("SUCCESS", "SP", "FM0000001", True, 0, 1, ["registration"], [True], None, None),
        ("SUCCESS", "SP", "FM0000001", True, 1, 0, ["registration", "conversion"], [False, True], None, None),
        ("SUCCESS", "SP", "FM0000001", True, 0, 1, ["registration", "conversion"], [False, True], None, None),
        (
            "FAIL_NO_PROPRIETOR",
            "SP",
            "FM0000001",
            True,
            0,
            0,
            ["registration"],
            [True],
            "NO_PROPRIETOR",
            "A proprietor is required.",
        ),
        (
            "FAIL_NO_OFFICE",
            "SP",
            "FM0000001",
            False,
            1,
            0,
            ["registration"],
            [True],
            "NO_BUSINESS_OFFICE",
            "A business office is required.",
        ),
        (
            "FAIL_NO_COMPLETING_PARTY",
            "SP",
            "FM0000001",
            True,
            1,
            0,
            ["registration"],
            [False],
            "NO_COMPLETING_PARTY",
            "A completing party is required.",
        ),
        # GP tests
        ("SUCCESS", "GP", "FM0000001", True, 2, 0, ["registration"], [True], None, None),
        ("SUCCESS", "GP", "FM0000001", True, 0, 2, ["registration"], [True], None, None),
        ("SUCCESS", "GP", "FM0000001", True, 1, 1, ["registration"], [True], None, None),
        ("SUCCESS", "GP", "FM0000001", True, 2, 0, ["registration", "conversion"], [False, True], None, None),
        ("SUCCESS", "GP", "FM0000001", True, 0, 2, ["registration", "conversion"], [False, True], None, None),
        ("SUCCESS", "GP", "FM0000001", True, 1, 1, ["registration", "conversion"], [False, True], None, None),
        (
            "FAIL_NO_PARTNER",
            "GP",
            "FM0000001",
            True,
            0,
            0,
            ["registration"],
            [True],
            "NO_PARTNER",
            "2 partners are required.",
        ),
        (
            "FAIL_NO_PARTNER",
            "GP",
            "FM0000001",
            True,
            1,
            0,
            ["registration"],
            [True],
            "NO_PARTNER",
            "2 partners are required.",
        ),
        (
            "FAIL_NO_PARTNER",
            "GP",
            "FM0000001",
            True,
            0,
            1,
            ["registration"],
            [True],
            "NO_PARTNER",
            "2 partners are required.",
        ),
        (
            "FAIL_NO_OFFICE",
            "GP",
            "FM0000001",
            False,
            2,
            0,
            ["registration"],
            [True],
            "NO_BUSINESS_OFFICE",
            "A business office is required.",
        ),
        (
            "FAIL_NO_COMPLETING_PARTY",
            "GP",
            "FM0000001",
            True,
            2,
            0,
            ["registration"],
            [False],
            "NO_COMPLETING_PARTY",
            "A completing party is required.",
        ),
    ],
)
def test_check_business(
    session,
    test_name,
    legal_type,
    identifier,
    has_office,
    num_persons_roles: int,
    num_org_roles: int,
    filing_types: list,
    filing_has_completing_party: list,
    expected_code,
    expected_msg,
):
    """Assert that business firm parties check functions properly."""

    # pytest scope change, so do a nested transaction
    # to avoid test data comflicts
    # failed tests rollback correctly, so watch out!
    with suppress(Exception):
        sess = session.begin_nested()

        legal_entity = None

        create_business(
            entity_type=legal_type,
            identifier=identifier,
            create_office=has_office,
            create_office_mailing_address=has_office,
            create_office_delivery_address=has_office,
            firm_num_persons_roles=num_persons_roles,
            firm_num_org_roles=num_org_roles,
            filing_types=filing_types,
            filing_has_completing_party=filing_has_completing_party,
            start_date=datetime.utcnow(),
        )

        legal_entity = LegalEntity.find_by_identifier(identifier)
        assert legal_entity
        assert legal_entity.entity_type == legal_type
        assert legal_entity.identifier == identifier

        with patch.object(firms, "check_address", return_value=[]):
            result = check_business(legal_entity)

        if expected_code:
            assert len(result) == 1
            business_warning = result[0]
            assert business_warning["code"] == expected_code
            assert business_warning["message"] == expected_msg
        else:
            assert len(result) == 0

        sess.rollback()


@pytest.mark.parametrize(
    "test_name, legal_type, identifier, expected_code, expected_msg",
    [
        # SP tests
        ("SUCCESS", "SP", "FM0000001", None, None),
        ("FAIL_NO_OFFICE", "SP", "FM0000001", "NO_BUSINESS_OFFICE", "A business office is required."),
        (
            "FAIL_NO_MAILING_ADDR",
            "SP",
            "FM0000001",
            "NO_BUSINESS_OFFICE_MAILING_ADDRESS",
            "Business office mailing address is required.",
        ),
        (
            "FAIL_NO_DELIVERY_ADDR",
            "SP",
            "FM0000001",
            "NO_BUSINESS_OFFICE_DELIVERY_ADDRESS",
            "Business office delivery address is required.",
        ),
        # GP tests
        ("SUCCESS", "GP", "FM0000001", None, None),
        ("FAIL_NO_OFFICE", "GP", "FM0000001", "NO_BUSINESS_OFFICE", "A business office is required."),
        (
            "FAIL_NO_MAILING_ADDR",
            "GP",
            "FM0000001",
            "NO_BUSINESS_OFFICE_MAILING_ADDRESS",
            "Business office mailing address is required.",
        ),
        (
            "FAIL_NO_DELIVERY_ADDR",
            "GP",
            "FM0000001",
            "NO_BUSINESS_OFFICE_DELIVERY_ADDRESS",
            "Business office delivery address is required.",
        ),
    ],
)
def test_check_office(session, test_name, legal_type, identifier, expected_code, expected_msg):
    """Assert that business firm parties check functions properly."""

    with suppress(Exception):
        sess = session.begin_nested()
        legal_entity = None
        if test_name == "SUCCESS":
            create_business(
                entity_type=legal_type,
                identifier=identifier,
                create_office=True,
                create_office_mailing_address=True,
                create_office_delivery_address=True,
            )
        elif test_name == "FAIL_NO_OFFICE":
            create_business(entity_type=legal_type, identifier=identifier, create_office=False)
        elif test_name == "FAIL_NO_MAILING_ADDR":
            create_business(
                entity_type=legal_type,
                identifier=identifier,
                create_office=True,
                create_office_mailing_address=False,
                create_office_delivery_address=True,
            )
        elif test_name == "FAIL_NO_DELIVERY_ADDR":
            create_business(
                entity_type=legal_type,
                identifier=identifier,
                create_office=True,
                create_office_mailing_address=True,
                create_office_delivery_address=False,
            )

        legal_entity = LegalEntity.find_by_identifier(identifier)
        assert legal_entity
        assert legal_entity.entity_type == legal_type
        assert legal_entity.identifier == identifier

        result = check_office(legal_entity)

        if expected_code:
            assert len(result) == 1
            business_warning = result[0]
            assert business_warning["code"] == expected_code
            assert business_warning["message"] == expected_msg
        else:
            assert len(result) == 0

        sess.rollback()


@pytest.mark.parametrize(
    "test_name, legal_type, identifier, num_persons_roles, num_org_roles, person_cessation_dates, org_cessation_dates, \
        filing_types, filing_has_completing_party, expected_code, expected_msg",
    [
        # SP tests
        (
            "SUCCESS_PARTY_MA_MISSING_STREET",
            "SP",
            "FM0000001",
            2,
            0,
            [None, datetime.utcnow()],
            [],
            ["registration"],
            [True],
            None,
            None,
        ),
        # # GP tests
        # ("SUCCESS_PARTY_MA_MISSING_STREET", "GP", "FM0000001", 3, 0, [None, None, datetime.utcnow()], [],
        #    ["registration"], [True], None, None),
    ],
)
def test_check_parties_cessation_date(
    session,
    test_name,
    legal_type,
    identifier,
    num_persons_roles: int,
    num_org_roles: int,
    person_cessation_dates: list,
    org_cessation_dates: list,
    filing_types: list,
    filing_has_completing_party: list,
    expected_code,
    expected_msg,
):
    """Assert that business firm parties check functions properly."""

    with suppress(Exception):
        sess = session.begin_nested()
        legal_entity = None

        create_business(
            entity_type=legal_type,
            identifier=identifier,
            firm_num_persons_roles=num_persons_roles,
            firm_num_org_roles=num_org_roles,
            person_cessation_dates=person_cessation_dates,
            org_cessation_dates=org_cessation_dates,
            create_firm_party_address=True,
            filing_types=filing_types,
            filing_has_completing_party=filing_has_completing_party,
            create_completing_party_address=True,
        )

        legal_entity = LegalEntity.find_by_identifier(identifier)
        assert legal_entity
        assert legal_entity.entity_type == legal_type
        assert legal_entity.identifier == identifier

        ceased_party = None
        if "PARTY_MA_MISSING_STREET" in test_name:
            ceased_party_role = (
                legal_entity.entity_roles.filter(EntityRole.role_type.in_(["partner", "proprietor"]))
                .filter(EntityRole.cessation_date is None)
                .one_or_none()
            )
            ceased_party = ceased_party_role.related_entity
            ceased_party.entity_mailing_address.street = None

        if ceased_party:
            ceased_party.save()

        result = check_parties(legal_type, legal_entity)

        if expected_code:
            assert len(result) == 1
        else:
            assert len(result) == 0

        sess.rollback()
