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
"""Test Correction validations."""
import copy
from datetime import date, datetime
from http import HTTPStatus

import datedelta
import pytest

from business_model.models import Address, Business, PartyRole
from legal_api.services.authz import STAFF_ROLE
from legal_api.services.filings import validate
from registry_schemas.example_data import (
    ANNUAL_REPORT,
    CHANGE_OF_DIRECTORS,
    CHANGE_OF_LIQUIDATORS,
    CHANGE_OF_RECEIVERS,
    CORRECTION_AR,
    CORRECTION_COL,
    CORRECTION_COR,
    DISSOLUTION,
    FILING_TEMPLATE,
    INCORPORATION_FILING_TEMPLATE
    )

from tests.unit.models import (
    factory_business,
    factory_business_mailing_address,
    factory_completed_filing,
    factory_filing,
    factory_party_role
)
from tests.unit.services.utils import jwt_request_context


CORRECTION_COD = copy.deepcopy(CORRECTION_COL)
CORRECTION_COD['filing']['correction']['correctedFilingType'] = 'changeOfDirectors'
CORRECTION_COD['filing']['correction']['relationships'][0]['roles'][0]['roleType'] = 'Director'
CORRECTION_DISS = copy.deepcopy(CORRECTION_COL)
CORRECTION_DISS['filing']['correction']['correctedFilingType'] = 'dissolution'
CORRECTION_DISS['filing']['correction']['relationships'][0]['roles'][0]['roleType'] = 'Custodian'
VALID_ADDRESS = {
    'streetAddress': '123 A St',
    'addressCity': 'Vancouver',
    'addressRegion': 'BC',
    'addressCountry': 'CA',
    'postalCode': 'V5K0A1'
}

@pytest.mark.parametrize('test_name, legal_type, identifier, initial_filing, correction_filing', [
    ('AR', 'CP', 'CP1234567', ANNUAL_REPORT, CORRECTION_AR),
    ('COD', 'BC', 'BC1234567', CHANGE_OF_DIRECTORS, CORRECTION_COD),
    ('COL', 'BC', 'BC1234567', CHANGE_OF_LIQUIDATORS, CORRECTION_COL),
    ('COR', 'BC', 'BC1234567', CHANGE_OF_RECEIVERS, CORRECTION_COR)
])
def test_valid_correction(session, app, jwt, test_name, legal_type, identifier, initial_filing, correction_filing):
    """Test that a valid correction passes validation."""
    # setup
    filing_template = copy.deepcopy(FILING_TEMPLATE)
    initial_filing_type = correction_filing['filing']['correction']['correctedFilingType']
    filing_template['filing']['header']['name'] = initial_filing_type
    filing_template['filing'][initial_filing_type] = initial_filing
    business = factory_business(identifier, entity_type=legal_type)
    factory_business_mailing_address(business)
    corrected_filing = factory_completed_filing(business, filing_template)

    f = copy.deepcopy(correction_filing)
    f['filing']['header']['identifier'] = identifier
    f['filing']['correction']['correctedFilingId'] = corrected_filing.id
    f['filing']['correction']['type'] = "STAFF"
    if test_name == 'COD':
        f['filing']['correction']['type'] = "CLIENT"
        f['filing']['correction']['relationships'].append({
            'entity': {
                'givenName': 'Phillip Tandy',
                'familyName': 'Miller',
                'alternateName': 'Phil Miller'
            },
            'deliveryAddress': {
                'streetAddress': 'delivery_address - address line one',
                'addressCity': 'delivery_address city',
                'addressCountry': 'CA',
                'postalCode': 'H0H0H0',
                'addressRegion': 'BC'
            },
            'mailingAddress': {
                'streetAddress': 'mailing_address - address line one',
                'addressCity': 'mailing_address city',
                'addressCountry': 'CA',
                'postalCode': 'H0H0H0',
                'addressRegion': 'BC'
            },
            'roles': [
                {
                    'roleType': 'Completing Party'
                }
            ]
        })

    with jwt_request_context(app, jwt, [STAFF_ROLE]):
        if err := validate(business, f):
            print(err.msg)

    # check that validation passed
    assert None is err


def test_correction__does_not_own_corrected_filing(session, app, jwt):
    """Check that a business cannot correct a different business' filing."""
    # setup
    identifier = 'CP1234567'
    business = factory_business(identifier)
    business2 = factory_business('CP1111111')
    corrected_filing = factory_completed_filing(business2, ANNUAL_REPORT)

    f = copy.deepcopy(CORRECTION_AR)
    f['filing']['header']['identifier'] = identifier
    f['filing']['correction']['correctedFilingId'] = corrected_filing.id

    with jwt_request_context(app, jwt, [STAFF_ROLE]):
        if err := validate(business, f):
            print(err.msg)

    # check that validation failed as expected
    assert HTTPStatus.BAD_REQUEST == err.code
    assert 'Corrected filing is not a valid filing for this business.' == err.msg[0]['error']


def test_correction__corrected_filing_does_not_exist(session, app, jwt):
    """Check that a correction fails on a filing that does not exist."""
    # setup
    identifier = 'CP1234567'
    business = factory_business(identifier)

    f = copy.deepcopy(CORRECTION_AR)
    f['filing']['header']['identifier'] = identifier
    f['filing']['correction']['correctedFilingId'] = 1

    with jwt_request_context(app, jwt, [STAFF_ROLE]):
        if err := validate(business, f):
            print(err.msg)

    # check that validation failed as expected
    assert HTTPStatus.BAD_REQUEST == err.code
    assert 'Corrected filing is not a valid filing.' == err.msg[0]['error']


def test_correction__corrected_filing_is_not_complete(session, app, jwt):
    """Check that a correction fails on a filing that is not complete."""
    # setup
    identifier = 'CP1234567'
    business = factory_business(identifier)
    corrected_filing = factory_filing(business, ANNUAL_REPORT)

    f = copy.deepcopy(CORRECTION_AR)
    f['filing']['header']['identifier'] = identifier
    f['filing']['correction']['correctedFilingId'] = corrected_filing.id

    with jwt_request_context(app, jwt, [STAFF_ROLE]):
        if err := validate(business, f):
            print(err.msg)

    # check that validation failed as expected
    assert HTTPStatus.BAD_REQUEST == err.code
    assert 'Corrected filing is not a valid filing.' == err.msg[0]['error']


def test_correction__invalid_director_dates(session, app, jwt):
    """Check that a correction fails if the director appointment date is after cessation date."""
    # setup
    identifier = 'BC1234567'
    business = factory_business(identifier, entity_type='BC')
    factory_business_mailing_address(business)
    filing_template = copy.deepcopy(FILING_TEMPLATE)
    filing_template['filing']['header']['name'] = 'changeOfDirectors'
    filing_template['filing']['changeOfDirectors'] = CHANGE_OF_DIRECTORS
    corrected_filing = factory_completed_filing(business, filing_template)

    f = copy.deepcopy(CORRECTION_COD)
    f['filing']['header']['identifier'] = identifier
    f['filing']['correction']['correctedFilingId'] = corrected_filing.id
    f['filing']['correction']['type'] = "STAFF"
    
    # Set appointment date after cessation date
    f['filing']['correction']['relationships'][0]['roles'][0]['appointmentDate'] = '2025-02-01'
    f['filing']['correction']['relationships'][0]['roles'][0]['cessationDate'] = '2025-01-01'

    with jwt_request_context(app, jwt, [STAFF_ROLE]):
        err = validate(business, f)

    # check that validation failed as expected
    assert err is not None
    assert err.code == HTTPStatus.BAD_REQUEST
    assert err.msg[0]['error'] == 'Appointment date cannot be after cessation date.'


@pytest.mark.parametrize('test_name, orig_cessation_dt, corr_cessation_dt', [
    ('Correct later', '2025-10-01', '2025-11-01'),
    ('Correct before', '2025-10-01', '2025-09-01'),
])
def test_correction_director_cessation_dates(session, app, jwt, test_name, orig_cessation_dt, corr_cessation_dt):
    """Check that a correction of cessation date passes validation."""
    # setup
    identifier = 'BC1234567'
    business = factory_business(identifier, entity_type='BC')
    factory_business_mailing_address(business)
    filing_template = copy.deepcopy(FILING_TEMPLATE)
    filing_template['filing']['header']['name'] = 'changeOfDirectors'
    orig_dirs = copy.deepcopy(CHANGE_OF_DIRECTORS)
    orig_dirs['directors'][0]['cessationDate'] = orig_cessation_dt
    filing_template['filing']['changeOfDirectors'] = orig_dirs
    corrected_filing = factory_completed_filing(business, filing_template)
    party_id = _setup_existing_party(business, PartyRole.RoleTypes.DIRECTOR, orig_cessation_dt)

    f = copy.deepcopy(CORRECTION_COD)
    f['filing']['header']['identifier'] = identifier
    f['filing']['correction']['correctedFilingId'] = corrected_filing.id
    f['filing']['correction']['type'] = "STAFF"
    
    f['filing']['correction']['relationships'][0]['roles'][0]['appointmentDate'] = '2025-02-01'
    f['filing']['correction']['relationships'][0]['roles'][0]['cessationDate'] = corr_cessation_dt
    f['filing']['correction']['relationships'][0]['entity']['identifier'] = str(party_id)

    with jwt_request_context(app, jwt, [STAFF_ROLE]):
        err = validate(business, f)

    # check that validation passed as expected
    assert err is None


@pytest.mark.parametrize("date_label", ["Appointment", "Cessation"])
@pytest.mark.parametrize(
    "test_name, offset_days, earliest_allowed_offset, expected_error",
    [
        ("SUCCESS - Valid date", -5, -10, None),
        ("SUCCESS - Date is today", 0, -10, None),
        ("SUCCESS - Date is exactly earliest_allowed", -10, -10, None),
        ("FAIL - Future date", 1, -10, "{date_label} date cannot be in the future."),
        ("FAIL - Date before earliest allowed", -15, -10, "{date_label} date cannot be before the business founding date."),
        ("SUCCESS - None date", None, -10, None)
    ]
)
def test_validate_relationship_date(session, app, jwt, date_label, test_name, offset_days, earliest_allowed_offset, expected_error):
    """Test validation of relationship dates."""
    from business_common.utils import LegislationDatetime
    from datetime import timedelta
    
    today = LegislationDatetime.datenow()
    # If offset_days is None, we pass None. Otherwise compute date
    date_value = today + timedelta(days=offset_days) if offset_days is not None else None
    earliest_allowed_date = today + timedelta(days=earliest_allowed_offset)

    # setup
    identifier = 'BC1234567'
    business = factory_business(identifier, entity_type='BC', founding_date=earliest_allowed_date)
    factory_business_mailing_address(business)
    filing_template = copy.deepcopy(FILING_TEMPLATE)
    filing_template['filing']['header']['name'] = 'changeOfDirectors'
    filing_template['filing']['changeOfDirectors'] = CHANGE_OF_DIRECTORS
    corrected_filing = factory_completed_filing(business, filing_template)

    f = copy.deepcopy(CORRECTION_COD)
    f['filing']['header']['identifier'] = identifier
    f['filing']['correction']['correctedFilingId'] = corrected_filing.id
    f['filing']['correction']['type'] = "STAFF"


    # Set appointment date after cessation date
    if date_value:
        if date_label == "Appointment":
            f['filing']['correction']['relationships'][0]['roles'][0]['appointmentDate'] = date_value.isoformat()
        else:
            f['filing']['correction']['relationships'][0]['roles'][0]['appointmentDate'] = earliest_allowed_date.isoformat()
            f['filing']['correction']['relationships'][0]['roles'][0]['cessationDate'] = date_value.isoformat()

    with jwt_request_context(app, jwt, [STAFF_ROLE]):
        err = validate(business, f)

    # check that validation failed as expected
    if expected_error:
        assert HTTPStatus.BAD_REQUEST == err.code
        if date_label == "Cessation" and earliest_allowed_date > date_value:
            assert len(err.msg) == 2
        else:
            assert len(err.msg) == 1
        assert err.msg[0]["error"] == expected_error.format(date_label=date_label)
    else:
        assert not err


@pytest.mark.parametrize(
    'test_name, email, expected_msg',
    [
        ('Valid', 'test@gmail.com', None),
        ('Missing email', None, 'Custodian email is required.'),
        ('Invalid', 'test 2@gmail.com', 'Custodian email cannot contain any whitespaces.'),
    ]
)
def test_correction_custodian(session, app, jwt, test_name, email, expected_msg):
    """Check that correction validation allows a custodian edit."""
    # setup
    identifier = 'BC1234567'
    business = factory_business(identifier, entity_type='BC')

    business.state = 'HISTORICAL'
    factory_business_mailing_address(business)
    filing_template = copy.deepcopy(FILING_TEMPLATE)
    filing_template['filing']['header']['name'] = 'dissolution'
    filing_template['filing']['business']['legalType'] = 'BC'
    filing_template['filing']['dissolution'] = copy.deepcopy(DISSOLUTION)
    filing_template['filing']['dissolution']['dissolutionType'] = 'voluntary'

    corrected_filing = factory_completed_filing(business, filing_template)
    party_id = _setup_existing_party(business, PartyRole.RoleTypes.CUSTODIAN)

    f = copy.deepcopy(CORRECTION_DISS)
    f['filing']['header']['identifier'] = identifier
    f['filing']['correction']['correctedFilingId'] = corrected_filing.id
    f['filing']['correction']['type'] = "STAFF"
    f['filing']['correction']['relationships'][0]['entity']['identifier'] = str(party_id)
    if email:
        f['filing']['correction']['relationships'][0]['entity']['email'] = email

    with jwt_request_context(app, jwt, [STAFF_ROLE]):
        err = validate(business, f)

    # check that validation failed as expected
    if expected_msg:
        assert err is not None
        assert len(err.msg) == 1
        assert err.msg[0]["error"] == expected_msg
    else:
        assert err is None


def _setup_existing_party(business: Business, party_role: str, cessation_dt: str = None) -> int:
    """Create an active party with optional cessation date for the business and return the party id."""
    cess_date = date.fromisoformat(cessation_dt) if cessation_dt is not None else None
    officer = {
        'firstName': 'Joe',
        'lastName': 'Swanson',
        'middleInitial': 'P',
        'partyType': 'person',
        'organizationName': ''
    }
    role = factory_party_role(
        Address.create_address(VALID_ADDRESS),
        Address.create_address(VALID_ADDRESS),
        officer,
        (datetime.utcnow() - datedelta.datedelta(years=5)).date().isoformat(),
        cess_date,
        party_role)
    business.party_roles.append(role)
    business.save()
    return role.party_id


CORRECTION_NAME_REQUEST_ONLY = {
    'filing': {
        'header': {
            'name': 'correction',
            'date': '2024-01-01',
            'authorizationReceived': True,
        },
        'business': {},
        'correction': {
            'comment': 'Test comment',
            'nameRequest': {
                'legalType': 'BC',
                'legalName': 'legal name change - BC1234567 INC.',
            },
        },
    }
}


@pytest.mark.parametrize(
    'test_name, legal_type, current_name, submitted_name',
    [
        # Standard corporate suffix variations
        ('exact match unchanged', 'BC', 'ACME HOLDINGS INC.', 'ACME HOLDINGS INC.'),
        ('case-insensitive unchanged', 'BC', 'ACME HOLDINGS INC.', 'acme holdings inc.'),
        ('name changed, same designation', 'BC', 'ACME HOLDINGS INC.', 'SUMMIT LOGISTICS INC.'),
        ('abbreviation - dropped dot', 'BC', 'ACME HOLDINGS INC.', 'SUMMIT LOGISTICS INC'),
        ('abbreviation - added dot', 'BC', 'ACME HOLDINGS LTD', 'PACIFIC TRADING LTD.'),
        ('word designation preserved', 'BC', 'ACME TRADING LIMITED', 'PACIFIC TRADING LIMITED'),
        ('french designation preserved', 'BC', 'ACME SERVICES INCORPOREE', 'SUMMIT SERVICES INCORPOREE'),
        ('internal spacing normalized', 'BC', 'ACME HOLDINGS LTD.', '  SUMMIT   ENTERPRISES   LTD.  '),
        ('comma before suffix accepted', 'BC', 'ACME HOLDINGS INC.', 'SUMMIT LOGISTICS, INC.'),
        ('comma before suffix without space accepted', 'BC', 'ACME HOLDINGS INC.', 'SUMMIT LOGISTICS,INC.'),

        # Multi-designation / compound phrases allowed
        ('idiomatic compound word with designation', 'BC', 'ORIGINAL LIMITED EDITION LTD.', 'SUMMIT LIMITED EDITION LTD.'),
        ('company keyword with designation', 'BC', 'THE ELECTRIC COMPANY INC.', 'METRO COMPANY INC.'),
        ('extraprovincial or grandfathered dual designation', 'BC', 'PAT SECURITY LIMITED COMPANY LTD.', 'PAT PATROL LIMITED COMPANY LTD.'),
        ('interior/prefix designation - core unchanged', 'BC', 'LIMITED ADVENTURES LTD.', 'LIMITED ADVENTURES LTD.'),
        ('interior/prefix designation - core changed', 'BC', 'LIMITED ADVENTURES LTD.', 'LIMITED EXPEDITIONS LTD.'),
        ('interior ulc - core unchanged', 'BC', 'PACIFIC ULC INVESTMENTS LTD.', 'PACIFIC ULC INVESTMENTS LTD.'),
        ('interior ulc - core changed', 'BC', 'PACIFIC ULC INVESTMENTS LTD.', 'COASTAL ULC VENTURES LTD.'),

        # Numbered company preservation & dotted abbreviations
        ('numbered company preserved', 'BC', '1234567 B.C. LTD.', '1234567 B.C. LTD.'),
        ('numbered company dropped trailing dot', 'BC', '1234567 B.C. LTD.', '1234567 B.C. LTD'),
        ('numbered company core changed, B.C. LTD. intact', 'BC', '1234567 B.C. LTD.', '9999999 B.C. LTD.'),

        # Community Contribution Companies (CC & continuation-in CCC)
        ('ccc with trailing suffix - core changed', 'CC', 'BCOUTDOORZ CCC CORP.', 'NORTH OUTDOORS CCC CORP.'),
        ('ccc internal phrase preserved', 'CC', 'BCOUTDOORZ COMMUNITY CONTRIBUTION COMPANY LTD.', 'SUMMIT COMMUNITY CONTRIBUTION COMPANY LTD.'),
        ('ccc statutory interchangeability words to abbr', 'CC', 'ALPHA COMMUNITY CONTRIBUTION COMPANY LTD.', 'BETA CCC LTD.'),
        ('ccc statutory interchangeability abbr to words', 'CC', 'ALPHA CCC LTD.', 'BETA COMMUNITY CONTRIBUTION COMPANY LTD.'),
        ('ccc standalone designation at end', 'CC', 'COASTAL CLEAN ENERGY CCC', 'VALLEY CLEAN ENERGY CCC'),
        ('ccc continuation-in entity preserved', 'CCC', 'GLOBAL VENTURES CCC INC.', 'PACIFIC VENTURES CCC INC.'),
        ('ccc continuation-in statutory interchangeability', 'CCC', 'GLOBAL VENTURES COMMUNITY CONTRIBUTION COMPANY INC.', 'PACIFIC VENTURES CCC INC.'),

        # Benefit Companies (BEN & continuation-in CBEN)
        ('benefit company with trailing suffix - core changed', 'BEN', 'GREEN HORIZONS BENEFIT COMPANY INC.', 'ECO FUTURE BENEFIT COMPANY INC.'),
        ('benefit company continuation-in entity preserved', 'CBEN', 'GLOBAL BENEFIT COMPANY CORP.', 'ALLIANCE BENEFIT COMPANY CORP.'),

        # Non-prefix entities: Cooperatives (can be anywhere except prefix)
        ('coop designation in middle', 'CP', 'COASTAL COOPERATIVE SERVICES', 'VALLEY COOPERATIVE SERVICES'),
        ('coop designation at end', 'CP', 'COASTAL COMMUNITY CO-OP', 'VALLEY COMMUNITY CO-OP'),
        ('coop dot tolerance', 'CP', 'COASTAL COMMUNITY CO-OP.', 'VALLEY COMMUNITY CO-OP'),

        # Non-prefix entities: Societies
        ('society non-prefix preserved', 'S', 'HOPE COMMUNITY FOUNDATION', 'VALLEY COMMUNITY FOUNDATION'),
        ('society abbreviation with dot tolerance', 'S', 'PACIFIC WRITERS ASSN.', 'COASTAL WRITERS ASSN'),

        # Rule = none (unconstrained name changes)
        ('sole proprietorship free form', 'SP', 'JOHN SMITH CONSULTING', 'JOHN SMITH ENTERPRISES'),
        ('general partnership free form', 'GP', 'DOE AND PARTNERS', 'DOE AND ASSOCIATES'),

        # Word boundary edge cases
        ('embedded designation inside word', 'BC', 'ORIGINAL LOGISTICS INC.', 'ZINC RESOURCE DRILLING INC.'),
        ('corporation embedded in word', 'BC', 'ACME HOLDINGS CORP.', 'INCORPORATING SOLUTIONS CORP.'),
        ('whitespace does not cause false max-length failure', 'BC', 'ACME HOLDINGS INC.', f'   {"A" * 140} INC.   '),

        # Numbered name conversions
        (
            'convert BEN to numbered name',
            'BEN',
            'GREEN FUTURE CONSULTING INC.',
            '1234567 B.C. LTD.'
        ),
        (
            'convert standard BC (COMP) to numbered name',
            'BC',
            'ACME DEVELOPMENTS CORP.',
            '1234567 B.C. LTD.'
        ),
        (
            'convert ULC to numbered name',
            'ULC',
            'NORTHERN VENTURES UNLIMITED LIABILITY COMPANY',
            '1234567 B.C. UNLIMITED LIABILITY COMPANY'
        ),
        (
            'convert CCC to numbered name',
            'CC',
            'COMMUNITY ROOTS COMMUNITY CONTRIBUTION COMPANY LTD.',
            '1234567 B.C. COMMUNITY CONTRIBUTION COMPANY LTD.'
        ),
        (
            'convert numbered name case insensitively',
            'BEN',
            'GREEN FUTURE CONSULTING INC.',
            '1234567 b.c. ltd.'
        ),
    ],
)
def test_legal_name_correction_valid_variations(
    session, app, jwt, test_name, legal_type, current_name, submitted_name
):
    """Test that valid name corrections with preserved designations pass validation."""
    identifier = 'BC1234567'
    business = factory_business(identifier, entity_type=legal_type)
    business.legal_name = current_name

    initial_filing_name = 'registration' if legal_type in ('SP', 'GP') else 'incorporationApplication'

    filing_template = copy.deepcopy(INCORPORATION_FILING_TEMPLATE)
    filing_template['filing']['header']['name'] = initial_filing_name
    filing_template['filing']['business']['legalType'] = legal_type

    corrected_filing = factory_completed_filing(business, filing_template)

    f = copy.deepcopy(CORRECTION_NAME_REQUEST_ONLY)
    f['filing']['header']['identifier'] = identifier
    f['filing']['business']['legalName'] = current_name
    f['filing']['business']['legalType'] = legal_type
    f['filing']['business']['identifier'] = identifier
    f['filing']['correction']['correctedFilingId'] = corrected_filing.id
    f['filing']['correction']['correctedFilingType'] = initial_filing_name
    f['filing']['correction']['type'] = 'STAFF'
    f['filing']['correction']['nameRequest'] = {
        'legalName': submitted_name,
        'legalType': legal_type,
    }

    with jwt_request_context(app, jwt, [STAFF_ROLE]):
        err = validate(business, f)

    assert err is None


@pytest.mark.parametrize(
    'test_name, legal_type, current_name, name_request_dict, expected_error, expected_path',
    [
        (
            'missing legalName - whitespace',
            'BC',
            'ACME HOLDINGS INC.',
            {'legalName': '   ', 'legalType': 'BC'},
            'Company name is required.',
            '/filing/correction/nameRequest/legalName',
        ),
        (
            'missing legalName - None',
            'BC',
            'ACME HOLDINGS INC.',
            {'legalName': None, 'legalType': 'BC'},
            'Company name is required.',
            '/filing/correction/nameRequest/legalName',
        ),
        (
            'exceeds maximum length (155 for corps)',
            'BC',
            'ACME HOLDINGS INC.',
            {'legalName': f'{"A" * 153} INC.', 'legalType': 'BC'},
            'Company name cannot exceed 155 characters.',
            '/filing/correction/nameRequest/legalName',
        ),
        # ( Firms check is excluded
        #     'exceeds maximum length (150 for firms)',
        #     'SP',
        #     'OLD TRADING CO',
        #     {'legalName': f'{"A" * 148} CO', 'legalType': 'SP'},
        #     'Company name cannot exceed 150 characters.',
        #     '/filing/correction/nameRequest/legalName',
        # ),
        (
            'designation changed (swapped INC to LTD)',
            'BC',
            'ACME HOLDINGS INC.',
            {'legalName': 'SUMMIT HOLDINGS LTD.', 'legalType': 'BC'},
            "Company name must end with the designation 'INC.'.",
            '/filing/correction/nameRequest/legalName',
        ),
        (
            'designation omitted entirely (corps)',
            'BC',
            'ACME HOLDINGS INC.',
            {'legalName': 'SUMMIT HOLDINGS', 'legalType': 'BC'},
            "Company name must end with the designation 'INC.'.",
            '/filing/correction/nameRequest/legalName',
        ),
        (
            'designation as prefix (corps must end with designation)',
            'BC',
            'ACME HOLDINGS INC.',
            {'legalName': 'INC. SUMMIT HOLDINGS', 'legalType': 'BC'},
            "Company name must end with the designation 'INC.'.",
            '/filing/correction/nameRequest/legalName',
        ),
        (
            'designation in middle (corps must end with designation)',
            'BC',
            'ACME HOLDINGS INC.',
            {'legalName': 'SUMMIT INC. HOLDINGS', 'legalType': 'BC'},
            "Company name must end with the designation 'INC.'.",
            '/filing/correction/nameRequest/legalName',
        ),
        (
            'non-abbreviated word with invalid trailing period',
            'BC',
            'ACME TRADING LIMITED',
            {'legalName': 'SUMMIT TRADING LIMITED.', 'legalType': 'BC'},
            "Company name must end with the designation 'LIMITED'.",
            '/filing/correction/nameRequest/legalName',
        ),
        (
            'numbered company suffix mismatch',
            'BC',
            '1234567 B.C. LTD.',
            {'legalName': '1234567 B.C. INC.', 'legalType': 'BC'},
            "Company name must end with the designation 'B.C. LTD.'.",
            '/filing/correction/nameRequest/legalName',
        ),
        (
            'interior designation but trailing suffix dropped',
            'BC',
            'LIMITED ADVENTURES LTD.',
            {'legalName': 'LIMITED ADVENTURES', 'legalType': 'BC'},
            "Company name must end with the designation 'LTD.'.",
            '/filing/correction/nameRequest/legalName',
        ),
        (
            'interior ulc but trailing suffix swapped',
            'BC',
            'PACIFIC ULC INVESTMENTS LTD.',
            {'legalName': 'PACIFIC ULC INVESTMENTS INC.', 'legalType': 'BC'},
            "Company name must end with the designation 'LTD.'.",
            '/filing/correction/nameRequest/legalName',
        ),
        (
            'ccc marker dropped during correction',
            'CC',
            'BCOUTDOORZ CCC CORP.',
            {'legalName': 'BCOUTDOORZ CORP.', 'legalType': 'CC'},
            "Company name must contain 'CCC' or 'COMMUNITY CONTRIBUTION COMPANY'.",
            '/filing/correction/nameRequest/legalName',
        ),
        (
            'ccc continuation-in marker dropped during correction',
            'CCC',
            'GLOBAL CCC CORP.',
            {'legalName': 'GLOBAL CORP.', 'legalType': 'CCC'},
            "Company name must contain 'CCC' or 'COMMUNITY CONTRIBUTION COMPANY'.",
            '/filing/correction/nameRequest/legalName',
        ),
        (
            'benefit company marker dropped during correction',
            'BEN',
            'HORIZON BENEFIT COMPANY INC.',
            {'legalName': 'HORIZON HOLDINGS INC.', 'legalType': 'BEN'},
            "Company name must contain 'BENEFIT COMPANY'.",
            '/filing/correction/nameRequest/legalName',
        ),
        (
            'benefit company continuation-in marker dropped during correction',
            'CBEN',
            'HORIZON BENEFIT COMPANY INC.',
            {'legalName': 'HORIZON HOLDINGS INC.', 'legalType': 'CBEN'},
            "Company name must contain 'BENEFIT COMPANY'.",
            '/filing/correction/nameRequest/legalName',
        ),
        (
            'benefit company missing trailing statutory corporate suffix',
            'BEN',
            'CLEAN WATER BENEFIT COMPANY LTD.',
            {'legalName': 'PURE WATER BENEFIT COMPANY', 'legalType': 'BEN'},
            "Company name must end with the designation 'LTD.'.",
            '/filing/correction/nameRequest/legalName',
        ),
        (
            'name includes only the designation',
            'BC',
            'CLEANING MAGIC LTD.',
            {'legalName': 'LTD.', 'legalType': 'BC'},
            "Company name must end with the designation 'LTD.'.",
            '/filing/correction/nameRequest/legalName',
        ),
        # Mapped entity type providing an invalid numbered name format/suffix
        (
            'benefit company converting to invalid numbered suffix (missing LTD)',
            'BEN',
            'HORIZON BENEFIT COMPANY INC.',
            {'legalName': '1234567 B.C.', 'legalType': 'BEN'},
            "Company name must end with the designation 'INC.'.",
            '/filing/correction/nameRequest/legalName',
        ),
        (
            'numbered company wrong corporation number digits',
            'BC',
            'ACME HOLDINGS INC.',
            {'legalName': '9999999 B.C. LTD.', 'legalType': 'BC'},
            "Company name must end with the designation 'INC.'.",
            '/filing/correction/nameRequest/legalName',
        ),
        #  COOPS not yet supported (doesn't use designation check yet)
        # (
        #     'cooperative designation as prefix',
        #     'CP',
        #     'COASTAL COOPERATIVE SERVICES',
        #     {'legalName': 'COOPERATIVE COASTAL SERVICES', 'legalType': 'CP'},
        #     "Company name cannot start with the designation 'COOPERATIVE'.",
        #     '/filing/correction/nameRequest/legalName',
        # ),
        # (
        #     'cooperative abbreviation designation as prefix',
        #     'CP',
        #     'COASTAL CO-OP SERVICES',
        #     {'legalName': 'CO-OP COASTAL SERVICES', 'legalType': 'CP'},
        #     "Company name cannot start with the designation 'CO-OP.'.",
        #     '/filing/correction/nameRequest/legalName',
        # ),
        # (
        #     'cooperative designation omitted entirely',
        #     'CP',
        #     'COASTAL COOPERATIVE SERVICES',
        #     {'legalName': 'VALLEY ENTERPRISES', 'legalType': 'CP'},
        #     "Company name must contain the designation 'COOPERATIVE'.",
        #     '/filing/correction/nameRequest/legalName',
        # ),
        # ( nrNumber still allowed to support legacy corrections
        #     'nrNumber not permitted',
        #     'BC',
        #     'ACME HOLDINGS INC.',
        #     {'legalName': 'ACME TRADING INC.', 'legalType': 'BC', 'nrNumber': 'NR 1234567'},
        #     'nrNumber not allowed when correcting legal name',
        #     '/filing/correction/nameRequest/nrNumber',
        # ),
        # ( legalType still allowed to support legacyCorrections
        #     'legal type change attempted',
        #     'BC',
        #     'ACME HOLDINGS INC.',
        #     {'legalName': 'ACME TRADING INC.', 'legalType': 'BEN'},
        #     'Legal type is not correctable',
        #     '/filing/correction/nameRequest/legalType',
        # ),
    ],
)
def test_legal_name_correction_invalid_submissions(
    session, app, jwt, test_name, legal_type, current_name, name_request_dict, expected_error, expected_path
):
    """Test rejection of invalid name corrections."""
    identifier = 'BC1234567'
    business = factory_business(identifier, entity_type=legal_type)
    business.legal_name = current_name

    initial_filing_name = 'registration' if legal_type in ('SP', 'GP') else 'incorporationApplication'

    filing_template = copy.deepcopy(INCORPORATION_FILING_TEMPLATE)
    filing_template['filing']['header']['name'] = initial_filing_name
    filing_template['filing']['business']['legalType'] = legal_type

    corrected_filing = factory_completed_filing(business, filing_template)

    f = copy.deepcopy(CORRECTION_NAME_REQUEST_ONLY)
    f['filing']['header']['identifier'] = identifier
    f['filing']['business']['legalName'] = current_name
    f['filing']['business']['legalType'] = legal_type
    f['filing']['business']['identifier'] = identifier
    f['filing']['correction']['correctedFilingId'] = corrected_filing.id
    f['filing']['correction']['correctedFilingType'] = initial_filing_name
    f['filing']['correction']['type'] = 'STAFF'
    f['filing']['correction']['nameRequest'] = name_request_dict

    with jwt_request_context(app, jwt, [STAFF_ROLE]):
        err = validate(business, f)

    assert err is not None
    assert err.code == HTTPStatus.BAD_REQUEST
    assert any(
        e['error'] == expected_error and e['path'] == expected_path
        for e in err.msg
    )


def test_name_request_block_omitted_passes(session, app, jwt):
    """Test that a correction omitting the nameRequest block passes without triggering name validation."""
    identifier = 'BC1234567'
    business = factory_business(identifier, entity_type='BC')
    business.legal_name = 'EXISTING NAME INC.'
    business.save()
    factory_business_mailing_address(business)

    filing_template = copy.deepcopy(FILING_TEMPLATE)
    filing_template['filing']['header']['name'] = 'changeOfDirectors'
    filing_template['filing']['changeOfDirectors'] = CHANGE_OF_DIRECTORS
    corrected_filing = factory_completed_filing(business, filing_template)

    f = copy.deepcopy(CORRECTION_COD)
    f['filing']['header']['identifier'] = identifier
    f['filing']['correction']['correctedFilingId'] = corrected_filing.id
    f['filing']['correction']['type'] = 'STAFF'
    f['filing']['correction'].pop('nameRequest', None)

    with jwt_request_context(app, jwt, [STAFF_ROLE]):
        err = validate(business, f)

    assert err is None


def test_legal_name_correction_existing_db_name_lacks_designation(session, app, jwt):
    """Ensure correction fails cleanly if existing registered business lacks a valid designation."""
    identifier = 'BC1234567'
    business = factory_business(identifier, entity_type='BC')
    # Corrupt or legacy legal name missing INC/LTD/CORP etc.
    business.legal_name = 'LEGACY COMPANY WITHOUT SUFFIX'
    business.save()
    factory_business_mailing_address(business)

    filing_template = copy.deepcopy(FILING_TEMPLATE)
    filing_template['filing']['header']['name'] = 'changeOfDirectors'
    filing_template['filing']['changeOfDirectors'] = CHANGE_OF_DIRECTORS
    corrected_filing = factory_completed_filing(business, filing_template)

    f = copy.deepcopy(CORRECTION_COD)
    f['filing']['header']['identifier'] = identifier
    f['filing']['correction']['correctedFilingId'] = corrected_filing.id
    f['filing']['correction']['type'] = 'STAFF'
    f['filing']['correction']['nameRequest'] = {
        'legalName': 'NEW COMPANY INC.',
        'legalType': 'BC',
    }

    with jwt_request_context(app, jwt, [STAFF_ROLE]):
        err = validate(business, f)

    assert err is not None
    assert err.code == HTTPStatus.BAD_REQUEST
    assert any(
        e['error'] == 'Legal name edits are disabled: existing designation could not be verified.'
        for e in err.msg
    )