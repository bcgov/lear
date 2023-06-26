# Copyright © 2023 Province of British Columbia
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Test suite to ensure Continuation Out is validated correctly."""
import copy
import datedelta
from http import HTTPStatus

import pycountry
import pytest
from registry_schemas.example_data import FILING_HEADER, CONTINUATION_OUT

from legal_api.models import LegalEntity
from legal_api.services.filings.validations.validation import validate
from legal_api.utils.datetime import datetime
from legal_api.utils.legislation_datetime import LegislationDatetime

date_format = '%Y-%m-%d'
legal_name = 'Test name request'


@pytest.mark.parametrize(
    'test_name, expected_code, message',
    [
        ('FAIL_IN_FUTURE', HTTPStatus.BAD_REQUEST, 'Continuation out date must be today or past.'),
        ('FAIL_EXPIRED', HTTPStatus.BAD_REQUEST, 'Consent continuation of interest has expired.'),
        ('FAIL_NO_CCO', HTTPStatus.BAD_REQUEST, 'Did not find an active Consent continuation out for this business.'),
        ('SUCCESS', None, None)
    ]
)
def test_validate_continuation_out_date(session, test_name, expected_code, message):
    """Assert validate continuation_out_date."""
    business = LegalEntity(
        identifier='BC1234567',
        entity_type='BC',
        state=LegalEntity.State.ACTIVE,
        founding_date=datetime.utcnow(),
        cco_expiry_date=datetime.utcnow()
    )
    filing = copy.deepcopy(FILING_HEADER)
    filing['filing']['continuationOut'] = copy.deepcopy(CONTINUATION_OUT)
    filing['filing']['header']['name'] = 'continuationOut'

    if test_name == 'FAIL_IN_FUTURE':
        filing['filing']['continuationOut']['continuationOutDate'] = \
            (datetime.utcnow() + datedelta.datedelta(days=1)).strftime(date_format)
    elif test_name == 'FAIL_EXPIRED':
        filing['filing']['continuationOut']['continuationOutDate'] = \
            LegislationDatetime.now().strftime(date_format)
        business.cco_expiry_date = datetime.utcnow() - datedelta.datedelta(days=2)
    elif test_name == 'FAIL_NO_CCO':
        business.cco_expiry_date = None

    err = validate(business, filing)

    # validate outcomes
    if test_name != 'SUCCESS':
        assert expected_code == err.code
        assert message == err.msg[0]['error']
    else:
        assert not err


@pytest.mark.parametrize(
    'test_name, expected_code, message',
    [
        ('FAIL_NO_COUNTRY', HTTPStatus.UNPROCESSABLE_ENTITY, None),
        ('FAIL_INVALID_COUNTRY', HTTPStatus.BAD_REQUEST, 'Invalid country.'),
        ('FAIL_REGION_BC', HTTPStatus.BAD_REQUEST, 'Region should not be BC.'),
        ('FAIL_INVALID_REGION', HTTPStatus.BAD_REQUEST, 'Invalid region.'),
        ('FAIL_INVALID_US_REGION', HTTPStatus.BAD_REQUEST, 'Invalid region.'),
        ('SUCCESS', None, None)
    ]
)
def test_validate_foreign_jurisdiction(session, test_name, expected_code, message):
    """Assert validate foreign jurisdiction."""
    business = LegalEntity(
        identifier='BC1234567',
        entity_type='BC',
        state=LegalEntity.State.ACTIVE,
        founding_date=datetime.utcnow(),
        cco_expiry_date=datetime.utcnow()
    )
    filing = copy.deepcopy(FILING_HEADER)
    filing['filing']['continuationOut'] = copy.deepcopy(CONTINUATION_OUT)
    filing['filing']['header']['name'] = 'continuationOut'

    if test_name == 'FAIL_NO_COUNTRY':
        del filing['filing']['continuationOut']['foreignJurisdiction']['country']
    elif test_name == 'FAIL_INVALID_COUNTRY':
        filing['filing']['continuationOut']['foreignJurisdiction']['country'] = 'NONE'
    elif test_name == 'FAIL_REGION_BC':
        filing['filing']['continuationOut']['foreignJurisdiction']['region'] = 'BC'
    elif test_name == 'FAIL_INVALID_REGION':
        filing['filing']['continuationOut']['foreignJurisdiction']['region'] = 'NONE'
    elif test_name == 'FAIL_INVALID_US_REGION':
        filing['filing']['continuationOut']['foreignJurisdiction']['country'] = 'US'
        filing['filing']['continuationOut']['foreignJurisdiction']['region'] = 'NONE'

    err = validate(business, filing)

    # validate outcomes
    if test_name != 'SUCCESS':
        assert expected_code == err.code
        if message:
            assert message == err.msg[0]['error']
    else:
        assert not err


def test_valid_foreign_jurisdiction(session):
    """Assert valid foreign jurisdiction."""
    business = LegalEntity(
        identifier='BC1234567',
        entity_type='BC',
        state=LegalEntity.State.ACTIVE,
        founding_date=datetime.utcnow(),
        cco_expiry_date=datetime.utcnow()
    )
    filing = copy.deepcopy(FILING_HEADER)
    filing['filing']['header']['name'] = 'continuationOut'

    for country in pycountry.countries:
        filing['filing']['continuationOut'] = copy.deepcopy(CONTINUATION_OUT)
        filing['filing']['continuationOut']['foreignJurisdiction']['country'] = country.alpha_2
        if country.alpha_2 in ('CA', 'US'):
            for region in pycountry.subdivisions.get(country_code=country.alpha_2):
                region_code = region.code.replace(f'{country.alpha_2}-', '')
                if country.alpha_2 == 'CA' and region_code == 'BC':
                    region_code = 'FEDERAL'  # Testing Federal code instead of invalid code BC

                filing['filing']['continuationOut']['foreignJurisdiction']['region'] = region_code
        else:
            del filing['filing']['continuationOut']['foreignJurisdiction']['region']

        err = validate(business, filing)
        assert not err


@pytest.mark.parametrize(
    'test_status, file_number, expected_code',
    [
        ('FAIL', None, HTTPStatus.UNPROCESSABLE_ENTITY),
        ('SUCCESS', '12345678901234567890', None)
    ]
)
def test_continuation_out_court_order(session, test_status, file_number, expected_code):
    """Assert valid court order."""
    business = LegalEntity(
        identifier='BC1234567',
        entity_type='BC',
        state=LegalEntity.State.ACTIVE,
        founding_date=datetime.utcnow(),
        cco_expiry_date=datetime.utcnow()
    )
    filing = copy.deepcopy(FILING_HEADER)
    filing['filing']['continuationOut'] = copy.deepcopy(CONTINUATION_OUT)
    filing['filing']['header']['name'] = 'continuationOut'

    if file_number:
        court_order = {}
        court_order['fileNumber'] = file_number
        filing['filing']['continuationOut']['courtOrder'] = court_order
    else:
        del filing['filing']['continuationOut']['courtOrder']['fileNumber']

    err = validate(business, filing)

    # validate outcomes
    if test_status == 'FAIL':
        assert expected_code == err.code
    else:
        assert not err
