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
import pytest
from http import HTTPStatus

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
    FILING_TEMPLATE)

from tests.unit.models import factory_business, factory_business_mailing_address, factory_completed_filing, factory_filing
from tests.unit.services.utils import jwt_request_context


CORRECTION_COD = copy.deepcopy(CORRECTION_COL)
CORRECTION_COD['filing']['correction']['correctedFilingType'] = 'changeOfDirectors'
CORRECTION_COD['filing']['correction']['relationships'][0]['roles'][0]['roleType'] = 'Director'


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
