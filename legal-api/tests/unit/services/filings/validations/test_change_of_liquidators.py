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
"""Test Change of Liquidator validation."""
import copy
from datetime import UTC, date, datetime, timedelta
from http import HTTPStatus
import pytest

from business_common.utils.legislation_datetime import LegislationDatetime
from business_model.models import Party, PartyRole
from legal_api.services.filings import validate
from tests.unit.services.filings.validations import lists_are_equal
from tests.unit.models import factory_business
from registry_schemas.example_data import CHANGE_OF_LIQUIDATORS, FILING_HEADER


@pytest.mark.parametrize(
    'test_name, roles, expected_code, expected_msg',
    [
        (
            'Valid liquidator with valid meta',
            [{'roleType': 'Liquidator', 'meta': {'appointmentMethod': 'court', 'courtOrderNumber': '12345'}}],
            None,
            None
        ),
        (
            'Invalid liquidator with missing meta key (schema 422)',
            [{'roleType': 'Liquidator'}],
            HTTPStatus.UNPROCESSABLE_ENTITY,
            [
                {
                    'context': [],
                    'error': "'meta' is a required property",
                    'path': 'changeOfLiquidators/relationships/0/roles/0'
                }
            ]
        ),
        (
            'Invalid liquidator with meta None (schema 422)',
            [{'roleType': 'Liquidator', 'meta': None}],
            HTTPStatus.UNPROCESSABLE_ENTITY,
            [
                {
                    'context': [],
                    'error': "None is not of type 'object'",
                    'path': 'changeOfLiquidators/relationships/0/roles/0/meta'
                }
            ]
        ),
        (
            'Invalid liquidator meta non-dict (schema 422)',
            [{'roleType': 'Liquidator', 'meta': 'not_a_dict'}],
            HTTPStatus.UNPROCESSABLE_ENTITY,
            [
                {
                    'context': [],
                    'error': "'not_a_dict' is not of type 'object'",
                    'path': 'changeOfLiquidators/relationships/0/roles/0/meta'
                }
            ]
        ),
        (
            'Invalid liquidator meta property (business rule 400)',
            [{
                'roleType': 'Liquidator', 
                'meta': {
                    'appointmentMethod': 'court', 
                    'courtOrderNumber': '12345', 
                    'unauthorizedKey': 'invalid'
                }
            }],
            HTTPStatus.BAD_REQUEST,
            [
                {
                    'error': 'Invalid meta property: unauthorizedKey.',
                    'path': '/filing/changeOfLiquidators/relationships/0/roles/0/meta/unauthorizedKey'
                }
            ]
        ),
        (
            'Invalid role without meta',
            [{'roleType': 'Director'}],
            HTTPStatus.BAD_REQUEST,
            [
                {
                    'error': 'Invalid role type for this filing.',
                    'path': '/filing/changeOfLiquidators/relationships/0/roles/0/roleType'
                }
            ]
        ),
        (
            'Invalid role with meta',
            [{'roleType': 'Director', 'meta': {'appointmentMethod': 'company'}}],
            HTTPStatus.BAD_REQUEST,
            [
                {
                    'error': 'Invalid role type for this filing.',
                    'path': '/filing/changeOfLiquidators/relationships/0/roles/0/roleType'
                },
                {
                    'error': 'Cannot submit meta properties for this role.',
                    'path': '/filing/changeOfLiquidators/relationships/0/roles/0/meta'
                }
            ]
        ),
    ]
)
def test_validate_col_relationships(
    session, test_name, roles, expected_code, expected_msg
):
    """Assert relationship validations for Change of Liquidators."""
    identifier = 'BC1234567'
    business = factory_business(identifier)

    f = copy.deepcopy(FILING_HEADER)
    f['filing']['header']['date'] = date.today().isoformat()
    f['filing']['header']['name'] = 'changeOfLiquidators'
    f['filing']['business']['identifier'] = identifier

    col = copy.deepcopy(CHANGE_OF_LIQUIDATORS)
    col['relationships'][0]['roles'] = copy.deepcopy(roles)
    # Ensure all relationships in the filing have appointmentDate so role/meta validations can be isolated
    for rel in col.get('relationships', []):
        for role in rel.get('roles', []):
            role.setdefault('appointmentDate', date.today().isoformat())
    f['filing']['changeOfLiquidators'] = col

    err = validate(business, f)

    if expected_code:
        assert err.code == expected_code
        assert lists_are_equal(err.msg, expected_msg)
    else:
        assert err is None


@pytest.mark.parametrize(
    'test_name, mailing_country_region, delivery_country_region, expected_code, expected_msg',
    [
        (
            'Valid office - all BC',
            ['CA', 'BC'],
            ['CA', 'BC'],
            None,
            None
        ),
        (
            'Valid office - mailing EX-BC',
            ['CA', 'AB'], # mailing can be outside of BC
            ['CA', 'BC'],
            None,
            None
        ),
        (
            'Valid office - mailing EX-CA',
            ['US', 'CA'], # mailing can be outside of Canada
            ['CA', 'BC'],
            None,
            None
        ),
        (
            'Invalid office - delivery EX-CA',
            ['CA', 'BC'],
            ['US', 'BC'], # delivery fails outside of Canada
            HTTPStatus.BAD_REQUEST,
            [
                {
                    'error': "Address Country must be 'CA'.",
                    'path': '/filing/changeOfLiquidators/offices/liquidationRecordsOffice'
                }
            ]
        ),
        (
            'Invalid office - delivery EX-BC',
            ['CA', 'BC'],
            ['CA', 'AB'], # delivery fails outside of BC
            HTTPStatus.BAD_REQUEST,
            [
                {
                    'error': "Address Region must be 'BC'.",
                    'path': '/filing/changeOfLiquidators/offices/liquidationRecordsOffice'
                }
            ]
        ),
    ]
)
def test_validate_col_offices(
    session, test_name, mailing_country_region, delivery_country_region, expected_code, expected_msg,
):
    """Assert office validations for Change of Liquidators."""
    identifier = 'BC1234567'
    business = factory_business(identifier)

    f = copy.deepcopy(FILING_HEADER)
    f['filing']['header']['date'] = date.today().isoformat()
    f['filing']['header']['name'] = 'changeOfLiquidators'
    f['filing']['business']['identifier'] = identifier

    col = copy.deepcopy(CHANGE_OF_LIQUIDATORS)
    # Ensure relationships have appointmentDate so office validation can run in isolation
    for rel in col.get('relationships', []):
        for role in rel.get('roles', []):
            role.setdefault('appointmentDate', date.today().isoformat())

    mailing_country = mailing_country_region[0]
    mailing_region = mailing_country_region[1]
    
    delivery_country = delivery_country_region[0]
    delivery_region = delivery_country_region[1]

    office = col['offices']['liquidationRecordsOffice']
    mailing = office['mailingAddress']
    delivery = office['deliveryAddress']

    mailing['addressCountry'] = mailing_country
    mailing['addressRegion'] = mailing_region
    delivery['addressCountry'] = delivery_country
    delivery['addressRegion'] = delivery_region
    
    f['filing']['changeOfLiquidators'] = col

    err = validate(business, f)

    if expected_code:
        assert err.code == expected_code
        assert lists_are_equal(err.msg, expected_msg)
    else:
        assert err is None


@pytest.mark.parametrize(
    'test_name, sub_type, in_liquidation, pop_offices, expected_code, expected_msg',
    [
        (
            'Missing offices for appointLiquidator when not in liquidation',
            'appointLiquidator',
            False,
            True,
            HTTPStatus.BAD_REQUEST,
            [
                {
                    'error': "Missing required offices ['liquidationRecordsOffice'].",
                    'path': '/filing/changeOfLiquidators/offices'
                }
            ]
        ),
        (
            'Valid appointLiquidator without offices when already in liquidation',
            'appointLiquidator',
            True,
            True,
            None,
            None
        ),
        (
            'Invalid office on ceaseLiquidator (offices not allowed)',
            'ceaseLiquidator',
            True,
            False,
            HTTPStatus.BAD_REQUEST,
            [
                {
                    'error': "Invalid office liquidationRecordsOffice. Only [] are allowed.",
                    'path': '/filing/changeOfLiquidators/offices'
                }
            ]
        ),
    ]
)
def test_validate_col_required_offices(
    session, test_name, sub_type, in_liquidation, pop_offices, expected_code, expected_msg
):
    """Assert offices are required for appointLiquidator when not in liquidation."""
    identifier = 'BC1234567'
    business = factory_business(identifier)
    business.in_liquidation = in_liquidation

    f = copy.deepcopy(FILING_HEADER)
    f['filing']['header']['date'] = date.today().isoformat()
    f['filing']['header']['name'] = 'changeOfLiquidators'
    f['filing']['business']['identifier'] = identifier

    col = copy.deepcopy(CHANGE_OF_LIQUIDATORS)
    col['type'] = sub_type
    if pop_offices:
        col.pop('offices', None)

    if sub_type == 'ceaseLiquidator':
        party = Party(
            party_type=Party.PartyTypes.PERSON.value,
            first_name='TEST',
            last_name='LIQUIDATOR'
        )
        party.save()
        party_role = PartyRole(
            role=PartyRole.RoleTypes.LIQUIDATOR.value,
            appointment_date=date.today(),
            business_id=business.id,
            party_id=party.id
        )
        party_role.save()
        col['relationships'] = [col['relationships'][0]]
        col['relationships'][0]['entity']['identifier'] = str(party.id)

    f['filing']['changeOfLiquidators'] = col

    err = validate(business, f)

    if expected_code:
        assert err is not None
        assert err.code == expected_code
        assert lists_are_equal(err.msg, expected_msg)
    else:
        assert err is None


@pytest.mark.parametrize(
    'test_name, filing_sub_type, in_liquidation, day_offset, raw_date, expected_code, expected_msg',
    [
        (
            'Valid appointLiquidator date (not in liquidation)',
            'appointLiquidator',
            False,
            -5,
            None,
            None,
            None
        ),
        (
            'Valid appointLiquidator current date (not in liquidation)',
            'appointLiquidator',
            False,
            0,
            None,
            None,
            None
        ),
        (
            'Missing date for appointLiquidator (not in liquidation)',
            'appointLiquidator',
            False,
            None,
            None,
            HTTPStatus.BAD_REQUEST,
            [
                {
                    'error': "'changeOfLiquidatorsDate' is required when business is not yet in liquidation.",
                    'path': '/filing/changeOfLiquidators/changeOfLiquidatorsDate'
                }
            ]
        ),
        (
            'Future date for appointLiquidator (not in liquidation)',
            'appointLiquidator',
            False,
            1,
            None,
            HTTPStatus.BAD_REQUEST,
            [
                {
                    'error': "'changeOfLiquidatorsDate' cannot be in the future.",
                    'path': '/filing/changeOfLiquidators/changeOfLiquidatorsDate'
                }
            ]
        ),
        (
            'Invalid format date for appointLiquidator (not in liquidation)',
            'appointLiquidator',
            False,
            None,
            '2026/05/15',
            HTTPStatus.UNPROCESSABLE_ENTITY,
            [
                {
                    'error': "'2026/05/15' is not a 'date'",
                    'path': 'changeOfLiquidators/changeOfLiquidatorsDate',
                    'context': []
                }
            ]
        ),
        (
            'Optional date omitted for appointLiquidator when already in liquidation',
            'appointLiquidator',
            True,
            None,
            None,
            None,
            None
        ),
        (
            'Optional date provided in the past when already in liquidation',
            'appointLiquidator',
            True,
            -10,
            None,
            None,
            None
        ),
        (
            'Optional date in the future when already in liquidation',
            'appointLiquidator',
            True,
            2,
            None,
            HTTPStatus.BAD_REQUEST,
            [
                {
                    'error': "'changeOfLiquidatorsDate' cannot be in the future.",
                    'path': '/filing/changeOfLiquidators/changeOfLiquidatorsDate'
                }
            ]
        ),
        (
            'Valid intentToLiquidate past date',
            'intentToLiquidate',
            False,
            -3,
            None,
            None,
            None
        ),
        (
            'Valid intentToLiquidate current date',
            'intentToLiquidate',
            False,
            0,
            None,
            None,
            None
        ),
        (
            'Future date for intentToLiquidate',
            'intentToLiquidate',
            False,
            1,
            None,
            HTTPStatus.BAD_REQUEST,
            [
                {
                    'error': "'changeOfLiquidatorsDate' cannot be in the future.",
                    'path': '/filing/changeOfLiquidators/changeOfLiquidatorsDate'
                }
            ]
        ),
        (
            'Invalid calendar day format for intentToLiquidate',
            'intentToLiquidate',
            False,
            None,
            '2026-02-31',
            HTTPStatus.UNPROCESSABLE_ENTITY,
            [
                {
                    'error': "'2026-02-31' is not a 'date'",
                    'path': 'changeOfLiquidators/changeOfLiquidatorsDate',
                    'context': []
                }
            ]
        ),
    ]
)
def test_validate_col_dates(
    session, test_name, filing_sub_type, in_liquidation, day_offset, raw_date, expected_code, expected_msg
):
    """Assert changeOfLiquidatorsDate validations."""
    identifier = 'BC1234567'
    business = factory_business(identifier)
    business.in_liquidation = in_liquidation

    today_legislation = LegislationDatetime.datenow()

    f = copy.deepcopy(FILING_HEADER)
    f['filing']['header']['date'] = today_legislation.isoformat()
    f['filing']['header']['name'] = 'changeOfLiquidators'
    f['filing']['business']['identifier'] = identifier

    col = copy.deepcopy(CHANGE_OF_LIQUIDATORS)
    col['type'] = filing_sub_type
    # Ensure relationships have appointmentDate so changeOfLiquidatorsDate validation can run in isolation
    for rel in col.get('relationships', []):
        for role in rel.get('roles', []):
            role.setdefault('appointmentDate', today_legislation.isoformat())

    if in_liquidation:
        col.pop('offices')

    if raw_date is not None:
        col['changeOfLiquidatorsDate'] = raw_date
    elif day_offset is not None:
        col['changeOfLiquidatorsDate'] = (today_legislation + timedelta(days=day_offset)).isoformat()
    else:
        col.pop('changeOfLiquidatorsDate', None)

    f['filing']['changeOfLiquidators'] = col

    err = validate(business, f)

    if expected_code:
        assert err is not None
        assert err.code == expected_code
        assert lists_are_equal(err.msg, expected_msg)
    else:
        assert err is None


@pytest.mark.parametrize(
    'test_name, sub_type, role_updates, in_liquidation, expected_code, expected_msg',
    [
        (
            'Valid appointLiquidator with appointmentDate',
            'appointLiquidator',
            {'appointmentDate': '2023-01-01'},
            False,
            None,
            None,
        ),
        (
            'Invalid appointLiquidator missing appointmentDate',
            'appointLiquidator',
            {'appointmentDate': None},
            False,
            HTTPStatus.BAD_REQUEST,
            [{'error': 'Appointment date is required for this filing.', 'path': '/filing/changeOfLiquidators/relationships/0/roles/0/appointmentDate'}],
        ),
        (
            'Invalid appointLiquidator future appointmentDate',
            'appointLiquidator',
            {'appointmentDate': '2099-01-01'},
            False,
            HTTPStatus.BAD_REQUEST,
            [{'error': 'Appointment date cannot be in the future.', 'path': '/filing/changeOfLiquidators/relationships/0/roles/0/appointmentDate'}],
        ),
        (
            'Invalid appointLiquidator appointmentDate before founding date',
            'appointLiquidator',
            {'appointmentDate': '1900-01-01'},
            False,
            HTTPStatus.BAD_REQUEST,
            [{'error': 'Appointment date cannot be before the business founding date.', 'path': '/filing/changeOfLiquidators/relationships/0/roles/0/appointmentDate'}],
        ),
        (
            'Invalid appointLiquidator cessationDate in the future',
            'appointLiquidator',
            {'appointmentDate': '2023-01-01', 'cessationDate': '2099-01-01'},
            False,
            HTTPStatus.BAD_REQUEST,
            [{'error': 'Cessation date cannot be in the future.', 'path': '/filing/changeOfLiquidators/relationships/0/roles/0/cessationDate'}],
        ),
        (
            'Valid ceaseLiquidator with cessationDate',
            'ceaseLiquidator',
            {'appointmentDate': '2022-01-01', 'cessationDate': '2023-01-01'},
            True,
            None,
            None,
        ),
        (
            'Invalid ceaseLiquidator missing cessationDate',
            'ceaseLiquidator',
            {'appointmentDate': '2022-01-01', 'cessationDate': None},
            True,
            HTTPStatus.BAD_REQUEST,
            [{'error': 'Cessation date is required for this filing.', 'path': '/filing/changeOfLiquidators/relationships/0/roles/0/cessationDate'}],
        ),
        (
            'Invalid ceaseLiquidator missing appointmentDate when cessationDate is present',
            'ceaseLiquidator',
            {'appointmentDate': None, 'cessationDate': '2023-01-01'},
            True,
            HTTPStatus.BAD_REQUEST,
            [{'error': 'Appointment date is required when cessation date is present.', 'path': '/filing/changeOfLiquidators/relationships/0/roles/0/appointmentDate'}],
        ),
        (
            'Invalid ceaseLiquidator future cessationDate',
            'ceaseLiquidator',
            {'appointmentDate': '2022-01-01', 'cessationDate': '2099-01-01'},
            True,
            HTTPStatus.BAD_REQUEST,
            [{'error': 'Cessation date cannot be in the future.', 'path': '/filing/changeOfLiquidators/relationships/0/roles/0/cessationDate'}],
        ),
        (
            'Invalid ceaseLiquidator cessationDate before appointment date',
            'ceaseLiquidator',
            {'appointmentDate': '2022-01-01', 'cessationDate': '2021-01-01'},
            True,
            HTTPStatus.BAD_REQUEST,
            [
                {'error': 'Appointment date cannot be after cessation date.', 'path': '/filing/changeOfLiquidators/relationships/0/roles/0/appointmentDate'},
                {'error': 'Cessation date cannot be before appointment date.', 'path': '/filing/changeOfLiquidators/relationships/0/roles/0/cessationDate'},
            ],
        ),
        (
            'Valid changeAddressLiquidator with valid appointmentDate',
            'changeAddressLiquidator',
            {'appointmentDate': '2022-01-01'},
            True,
            None,
            None,
        ),
    ]
)
def test_validate_liquidator_role_dates(
    session, test_name, sub_type, role_updates, in_liquidation, expected_code, expected_msg
):
    """Assert appointmentDate and cessationDate requirements by sub-type."""
    from business_model.models import Party, PartyRole

    identifier = 'BC1234567'
    business = factory_business(identifier)
    business.in_liquidation = in_liquidation

    f = copy.deepcopy(FILING_HEADER)
    f['filing']['header']['date'] = date.today().isoformat()
    f['filing']['header']['name'] = 'changeOfLiquidators'
    f['filing']['business']['identifier'] = identifier

    col = copy.deepcopy(CHANGE_OF_LIQUIDATORS)
    col['type'] = sub_type
    # Only keep the first relationship for role date testing to isolate tests to relationships[0]
    col['relationships'] = [col['relationships'][0]]
    if in_liquidation and sub_type != 'intentToLiquidate':
        col.pop('offices', None)

    col['changeOfLiquidatorsDate'] = '2023-01-01'

    if sub_type in ['ceaseLiquidator', 'changeAddressLiquidator']:
        party = Party(first_name='TEST', last_name='LIQUIDATOR', party_type='person')
        party.save()
        party_role = PartyRole(
            role=PartyRole.RoleTypes.LIQUIDATOR.value,
            party_id=party.id,
            business_id=business.id,
            appointment_date=datetime(2022, 1, 1, tzinfo=UTC),
        )
        party_role.save()
        col['relationships'][0]['entity']['identifier'] = str(party.id)

    role = col['relationships'][0]['roles'][0]
    # Ensure role has valid meta so meta validation doesn't interfere with date tests
    role.setdefault('meta', {'appointmentMethod': 'court', 'courtOrderNumber': '12345'})
    for key, val in role_updates.items():
        if val is None:
            role.pop(key, None)
        else:
            role[key] = val

    f['filing']['changeOfLiquidators'] = col
    err = validate(business, f)

    if expected_code:
        assert err is not None
        assert err.code == expected_code
        assert lists_are_equal(err.msg, expected_msg)
    else:
        assert err is None
