# Copyright © 2024 Province of British Columbia
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
"""Test suite to ensure Corpse business checks work correctly."""
import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta
from business_model.models import Address, Office, OfficeType, PartyRole
from tests.unit.models import factory_business, factory_business_office, factory_party_role
from tests.unit.services.warnings import factory_address
from legal_api.services.warnings.business.business_checks import BusinessWarningReferers, WarningType
from legal_api.services.warnings.business.business_checks.corps import check_business, check_directors, check_offices
from legal_api.services.warnings.business.business_checks.firms import check_address


def create_complete_business(identifier="BC1234567"):
    """Create a corp with a complete registered office and records office."""
    business = factory_business(identifier=identifier, entity_type="BC")
    factory_business_office(business, OfficeType.REGISTERED)
    factory_business_office(business, OfficeType.RECORDS)
    return business


def add_office(business, office_type, mailing_address=None, delivery_address=None):
    """Attach an office with the given addresses (None = no address row) to the business."""
    office = Office(office_type=office_type)
    for address in (mailing_address, delivery_address):
        if address:
            office.addresses.append(address)
    business.offices.append(office)
    business.save()
    return office


def add_director(business, mailing_address, delivery_address, cessation_date=None):
    """Attach a director with the given addresses to the business."""
    officer = {'firstName': 'Jane', 'lastName': 'Doe', 'middleInitial': '', 'partyType': 'person',
               'organizationName': ''}
    party_role = factory_party_role(delivery_address, mailing_address, officer, datetime(2020, 1, 1), cessation_date,
                                    PartyRole.RoleTypes.DIRECTOR)
    business.party_roles.append(party_role)
    business.save()
    return party_role

@pytest.mark.parametrize("has_amalgamation, expected_warning", [
    (True, True),  # Future effective amalgamation
    (False, False)  # No amalgamation
])
def test_check_business(session, has_amalgamation, expected_warning):
    """Test the check_business function."""
    business = create_complete_business()

    mock_filing = Mock()
    mock_filing.id = "filing-id"
    mock_filing.filing_json = {
        "filing": {
            "amalgamationApplication": {
                "amalgamatingBusinesses": [{"identifier": "BC7654321"}],
                "nameRequest": {
                    "legalName": "NAMED AMALG CORP.",
                    "legalType": "BC"
                }
            },
            "business": {
                "identifier": "T987654321",
                "legalType": "BC"
            }
        }
    }
    if has_amalgamation:
        # Set effective_date in the future to simulate an amalgamation
        mock_filing.effective_date = datetime.now() + timedelta(days=1)
        mock_filing.payment_completion_date = datetime.now()
    else:
        # Set dates that do not indicate an amalgamation
        mock_filing.effective_date = datetime.now()
        mock_filing.payment_completion_date = datetime.now()

    with patch('business_model.models.business.Business.is_pending_amalgamating_business', return_value=mock_filing):
        result = check_business(business, is_staff=True)

        if expected_warning:
            assert len(result) == 1
            warning = result[0]
            assert warning['code'] == "AMALGAMATING_BUSINESS"
            assert warning['message'] == "This business is part of a future effective amalgamation."
            assert warning['warningType'] == WarningType.FUTURE_EFFECTIVE_AMALGAMATION
            assert 'amalgamationDate' in warning['data']
            assert isinstance(warning['data']['amalgamationDate'], datetime)
            assert warning['data']['filingId'] == "filing-id"
            assert warning['data']['amalgamatingBusinesses'] == [{"identifier": "BC7654321"}]
            assert warning['data']['resultingBusinessName'] == "NAMED AMALG CORP."
            assert warning['data']['resultingBusinessIdentifier'] == "T987654321"
        else:
            assert len(result) == 0


@pytest.mark.parametrize("name_request, expected_resulting_name", [
    # named amalgamation result - legalName present
    ({"legalName": "NAMED AMALG CORP.", "legalType": "BC"}, "NAMED AMALG CORP."),
    # numbered amalgamation result - no legalName key at all
    ({"correctNameOption": "correct-aml-numbered", "legalType": "BC"}, None),
    # no nameRequest present at all
    ({}, None),
])
def test_check_business_amalgamation_resulting_name(session, name_request, expected_resulting_name):
    """Test that resultingBusinessName reflects whether the amalgamation result is named or numbered."""
    business = create_complete_business()

    mock_filing = Mock()
    mock_filing.id = "filing-id"
    mock_filing.effective_date = datetime.now() + timedelta(days=1)
    mock_filing.payment_completion_date = datetime.now()
    mock_filing.filing_json = {
        "filing": {
            "amalgamationApplication": {
                "amalgamatingBusinesses": [{"identifier": "BC7654321"}],
                "nameRequest": name_request
            },
            "business": {
                "identifier": "T987654321",
                "legalType": "BC"
            }
        }
    }

    with patch('business_model.models.business.Business.is_pending_amalgamating_business', return_value=mock_filing):
        warning = check_business(business, is_staff=True)[0]

    assert warning['data'].get('resultingBusinessName') == expected_resulting_name

    if expected_resulting_name is None:
        assert 'resultingBusinessName' not in warning['data']
    else:
        assert 'resultingBusinessName' in warning['data']


def test_check_business_excludes_filing_id_for_non_staff(session):
    """Test that filing ids and the resulting business identifier are only included for staff users."""
    business = create_complete_business()
    mock_filing = Mock(
        id="filing-id",
        effective_date=datetime.now() + timedelta(days=1),
        payment_completion_date=datetime.now(),
        filing_json={
            "filing": {
                "amalgamationApplication": {
                    "amalgamatingBusinesses": [{"identifier": "BC7654321"}],
                    "nameRequest": {
                        "legalName": "NAMED AMALG CORP.",
                        "legalType": "BC"
                    }
                },
                "business": {
                    "identifier": "T987654321",
                    "legalType": "BC"
                }
            }
        }
    )

    with patch('business_model.models.business.Business.is_pending_amalgamating_business', return_value=mock_filing):
        warning = check_business(business)[0]

    assert warning['data'] == {
        "amalgamationDate": mock_filing.effective_date,
        "amalgamatingBusinesses": [{"identifier": "BC7654321"}],
        "resultingBusinessName": "NAMED AMALG CORP."
    }
    assert 'filingId' not in warning['data']
    assert 'resultingBusinessIdentifier' not in warning['data']


def test_check_business_complete_corp_has_no_missing_info_warnings(session):
    """Assert a corp with complete offices and directors yields no MISSING_REQUIRED_BUSINESS_INFO warnings."""
    business = create_complete_business()
    add_director(business, factory_address('mailing'), factory_address('delivery'))

    with patch('business_model.models.business.Business.is_pending_amalgamating_business', return_value=None):
        result = check_business(business)

    assert result == []


def test_check_offices_missing_offices(session):
    """Assert a corp without registered/records offices gets one warning per office, identified by officeType."""
    business = factory_business(identifier="BC1234567", entity_type="BC")

    result = check_offices(business)

    assert [(x['code'], x['message'], x['data']) for x in result] == [
        ('NO_REGISTERED_OFFICE', 'A registered office is required.', {'officeType': 'registeredOffice'}),
        ('NO_RECORDS_OFFICE', 'A records office is required.', {'officeType': 'recordsOffice'}),
    ]
    assert all(x['warningType'] == WarningType.MISSING_REQUIRED_BUSINESS_INFO for x in result)


def test_check_offices_ignores_deactivated_office(session):
    """Assert a deactivated office does not satisfy the office check."""
    business = factory_business(identifier="BC1234567", entity_type="BC")
    office = add_office(business, OfficeType.REGISTERED, factory_address('mailing'), factory_address('delivery'))
    office.deactivated_date = datetime.now()
    factory_business_office(business, OfficeType.RECORDS)

    result = check_offices(business)

    assert [x['code'] for x in result] == ['NO_REGISTERED_OFFICE']


@pytest.mark.parametrize(
    'office_type, address_type, null_field, expected_code, expected_msg',
    [
        (OfficeType.REGISTERED, 'mailing', 'NO_ADDRESS', 'NO_REGISTERED_OFFICE_MAILING_ADDRESS',
         'Registered office mailing address is required.'),
        (OfficeType.REGISTERED, 'mailing', 'street', 'NO_REGISTERED_OFFICE_MAILING_ADDRESS_STREET',
         'Street is required for registered office mailing address.'),
        (OfficeType.REGISTERED, 'mailing', 'city', 'NO_REGISTERED_OFFICE_MAILING_ADDRESS_CITY',
         'City is required for registered office mailing address.'),
        (OfficeType.REGISTERED, 'mailing', 'country', 'NO_REGISTERED_OFFICE_MAILING_ADDRESS_COUNTRY',
         'Country is required for registered office mailing address.'),
        (OfficeType.REGISTERED, 'mailing', 'postal_code', 'NO_REGISTERED_OFFICE_MAILING_ADDRESS_POSTAL_CODE',
         'Postal code is required for registered office mailing address.'),
        (OfficeType.REGISTERED, 'mailing', 'region', None, None),
        (OfficeType.REGISTERED, 'delivery', 'NO_ADDRESS', 'NO_REGISTERED_OFFICE_DELIVERY_ADDRESS',
         'Registered office delivery address is required.'),
        (OfficeType.REGISTERED, 'delivery', 'street', 'NO_REGISTERED_OFFICE_DELIVERY_ADDRESS_STREET',
         'Street is required for registered office delivery address.'),
        (OfficeType.REGISTERED, 'delivery', 'region', 'NO_REGISTERED_OFFICE_DELIVERY_ADDRESS_REGION',
         'Region is required for registered office delivery address.'),
        (OfficeType.RECORDS, 'mailing', 'NO_ADDRESS', 'NO_RECORDS_OFFICE_MAILING_ADDRESS',
         'Records office mailing address is required.'),
        (OfficeType.RECORDS, 'mailing', 'postal_code', 'NO_RECORDS_OFFICE_MAILING_ADDRESS_POSTAL_CODE',
         'Postal code is required for records office mailing address.'),
        (OfficeType.RECORDS, 'delivery', 'NO_ADDRESS', 'NO_RECORDS_OFFICE_DELIVERY_ADDRESS',
         'Records office delivery address is required.'),
        (OfficeType.RECORDS, 'delivery', 'city', 'NO_RECORDS_OFFICE_DELIVERY_ADDRESS_CITY',
         'City is required for records office delivery address.'),
        (OfficeType.RECORDS, 'delivery', 'country', 'NO_RECORDS_OFFICE_DELIVERY_ADDRESS_COUNTRY',
         'Country is required for records office delivery address.'),
        (OfficeType.RECORDS, 'delivery', 'region', 'NO_RECORDS_OFFICE_DELIVERY_ADDRESS_REGION',
         'Region is required for records office delivery address.'),
    ])
def test_check_offices_address_fields(session, office_type, address_type, null_field, expected_code, expected_msg):
    """Assert each missing office address field raises the matching warning carrying the officeType."""
    business = factory_business(identifier="BC1234567", entity_type="BC")
    other_type = OfficeType.RECORDS if office_type == OfficeType.REGISTERED else OfficeType.REGISTERED
    factory_business_office(business, other_type)

    addresses = {'mailing': factory_address('mailing'), 'delivery': factory_address('delivery')}
    if null_field == 'NO_ADDRESS':
        addresses[address_type] = None
    else:
        addresses[address_type] = factory_address(address_type, make_null_field_name=null_field)
    add_office(business, office_type, addresses['mailing'], addresses['delivery'])

    result = check_offices(business)

    if expected_code:
        assert len(result) == 1
        warning = result[0]
        assert warning['code'] == expected_code
        assert warning['message'] == expected_msg
        assert warning['warningType'] == WarningType.MISSING_REQUIRED_BUSINESS_INFO
        assert warning['data'] == {'officeType': office_type}
    else:
        assert result == []


@pytest.mark.parametrize(
    'address_type, null_field, expected_code, expected_msg',
    [
        ('mailing', None, None, None),
        ('mailing', 'region', None, None),
        ('mailing', 'NO_ADDRESS', 'NO_DIRECTOR_MAILING_ADDRESS', 'Director mailing address is required.'),
        ('mailing', 'street', 'NO_DIRECTOR_MAILING_ADDRESS_STREET',
         'Street is required for director mailing address.'),
        ('mailing', 'city', 'NO_DIRECTOR_MAILING_ADDRESS_CITY', 'City is required for director mailing address.'),
        ('mailing', 'country', 'NO_DIRECTOR_MAILING_ADDRESS_COUNTRY',
         'Country is required for director mailing address.'),
        ('mailing', 'postal_code', 'NO_DIRECTOR_MAILING_ADDRESS_POSTAL_CODE',
         'Postal code is required for director mailing address.'),
        ('delivery', 'region', None, None),
        ('delivery', 'NO_ADDRESS', 'NO_DIRECTOR_DELIVERY_ADDRESS', 'Director delivery address is required.'),
        ('delivery', 'street', 'NO_DIRECTOR_DELIVERY_ADDRESS_STREET',
         'Street is required for director delivery address.'),
        ('delivery', 'city', 'NO_DIRECTOR_DELIVERY_ADDRESS_CITY', 'City is required for director delivery address.'),
        ('delivery', 'country', 'NO_DIRECTOR_DELIVERY_ADDRESS_COUNTRY',
         'Country is required for director delivery address.'),
        ('delivery', 'postal_code', 'NO_DIRECTOR_DELIVERY_ADDRESS_POSTAL_CODE',
         'Postal code is required for director delivery address.'),
    ])
def test_check_directors_address_fields(session, address_type, null_field, expected_code, expected_msg):
    """Assert each missing director address field raises the matching warning carrying the partyId."""
    business = factory_business(identifier="BC1234567", entity_type="BC")
    addresses = {'mailing': factory_address('mailing'), 'delivery': factory_address('delivery')}
    if null_field == 'NO_ADDRESS':
        addresses[address_type] = None
    elif null_field:
        addresses[address_type] = factory_address(address_type, make_null_field_name=null_field)
    party_role = add_director(business, addresses['mailing'], addresses['delivery'])

    result = check_directors(business)

    if expected_code:
        assert len(result) == 1
        warning = result[0]
        assert warning['code'] == expected_code
        assert warning['message'] == expected_msg
        assert warning['warningType'] == WarningType.MISSING_REQUIRED_BUSINESS_INFO
        assert warning['data'] == {'partyId': party_role.party.id}
    else:
        assert result == []


@pytest.mark.parametrize('country, expected_codes', [
    ('CA', ['NO_DIRECTOR_MAILING_ADDRESS_POSTAL_CODE', 'NO_DIRECTOR_DELIVERY_ADDRESS_POSTAL_CODE']),
    ('HK', []),
])
def test_check_directors_postal_code_required_by_country(session, country, expected_codes):
    """Assert a director without a postal code is only flagged when their country uses postal codes."""
    business = factory_business(identifier="BC1234567", entity_type="BC")
    add_director(business,
                 factory_address('mailing', country=country, postal_code=None),
                 factory_address('delivery', country=country, postal_code=None))

    result = check_directors(business)

    assert [x['code'] for x in result] == expected_codes


def test_check_directors_skips_ceased_directors_and_flags_each_active_one(session):
    """Assert ceased directors are ignored and each active director is reported with its own partyId."""
    business = factory_business(identifier="BC1234567", entity_type="BC")
    add_director(business, None, factory_address('delivery'), cessation_date=datetime(2021, 1, 1))
    active_one = add_director(business, None, factory_address('delivery'))
    active_two = add_director(business, factory_address('mailing', make_null_field_name='city'),
                              factory_address('delivery'))

    result = check_directors(business)

    assert [(x['code'], x['data']) for x in result] == [
        ('NO_DIRECTOR_MAILING_ADDRESS', {'partyId': active_one.party.id}),
        ('NO_DIRECTOR_MAILING_ADDRESS_CITY', {'partyId': active_two.party.id}),
    ]


def test_warnings_carry_their_own_data(session):
    """Assert adding data does not mutate the shared warning mapping (two offices, same code, different data)."""
    business = factory_business(identifier="BC1234567", entity_type="BC")
    add_office(business, OfficeType.REGISTERED, factory_address('mailing', make_null_field_name='street'),
               factory_address('delivery'))
    add_office(business, OfficeType.RECORDS, factory_address('mailing', make_null_field_name='street'),
               factory_address('delivery'))

    result = check_offices(business)

    assert [x['data'] for x in result] == [{'officeType': 'registeredOffice'}, {'officeType': 'recordsOffice'}]
    assert 'data' not in check_address(factory_address('mailing', make_null_field_name='street'), Address.MAILING,
                                       BusinessWarningReferers.REGISTERED_OFFICE)[0]


@pytest.mark.parametrize("enabled_features, warnings_expected", [
    (['reviewImportedData'], True),
    ([], False),
    (None, False),  # flag service unavailable
])
def test_check_business_missing_info_gated_by_feature_flag(session, monkeypatch, enabled_features, warnings_expected):
    """Assert office/director warnings are emitted only while reviewImportedData is in enable-new-feature."""
    business = factory_business(identifier="BC1234567", entity_type="BC")
    add_director(business, factory_address('mailing', make_null_field_name='street'), factory_address('delivery'))
    monkeypatch.setattr('legal_api.services.flags.value', lambda *args, **kwargs: enabled_features)

    with patch('business_model.models.business.Business.is_pending_amalgamating_business', return_value=None):
        result = check_business(business)

    missing_info = [x for x in result if x['warningType'] == WarningType.MISSING_REQUIRED_BUSINESS_INFO]
    if warnings_expected:
        assert [x['code'] for x in missing_info] == ['NO_REGISTERED_OFFICE', 'NO_RECORDS_OFFICE',
                                                     'NO_DIRECTOR_MAILING_ADDRESS_STREET']
    else:
        assert missing_info == []
