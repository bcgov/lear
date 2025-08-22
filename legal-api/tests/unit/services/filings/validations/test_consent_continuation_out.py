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
"""Test suite to ensure Consent Continuation Out is validated correctly."""
import copy
import datedelta
from http import HTTPStatus

import pycountry
import pytest
from registry_schemas.example_data import FILING_HEADER, CONSENT_CONTINUATION_OUT

from legal_api.models import Business, ConsentContinuationOut
from legal_api.services.filings.validations.validation import validate
from legal_api.utils.datetime import datetime
from tests.unit.models import factory_business, factory_completed_filing

from tests.unit.models.test_consent_continuation_out import get_cco_expiry_date
legal_name = 'Test name request'


@pytest.mark.parametrize(
    'test_name, expected_code',
    [
        ('FAIL_NOT_ACTIVE', HTTPStatus.BAD_REQUEST),
        ('FAIL_NOT_IN_GOOD_STANDING', HTTPStatus.BAD_REQUEST),
        ('SUCCESS', None)
    ]
)
def test_consent_continuation_out_active_and_good_standing(session, test_name, expected_code, monkeypatch):
    """Assert Consent Continuation Out can be filed."""
    monkeypatch.setattr(
        'legal_api.services.flags.value',
        lambda flag: "BC BEN CC ULC C CBEN CCC CUL"  if flag == 'supported-consent-continuation-out-entities' else {}
    )
    business = Business(
        identifier='BC1234567',
        legal_type='BC',
        state=Business.State.ACTIVE,
        founding_date=datetime.utcnow()
    )
    if test_name == 'FAIL_NOT_ACTIVE':
        business.state = Business.State.HISTORICAL
    elif test_name == 'FAIL_NOT_IN_GOOD_STANDING':
        business.founding_date = datetime.utcnow() - datedelta.datedelta(years=2)

    filing = copy.deepcopy(FILING_HEADER)
    filing['filing']['consentContinuationOut'] = copy.deepcopy(CONSENT_CONTINUATION_OUT)
    filing['filing']['header']['name'] = 'consentContinuationOut'

    err = validate(business, filing)

    # validate outcomes
    if test_name != 'SUCCESS':
        assert expected_code == err.code
        assert 'Business should be Active and in Good Standing to file Consent Continuation Out.' == err.msg[0]['error']
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
def test_validate_foreign_jurisdiction(session, test_name, expected_code, message, monkeypatch):
    """Assert validate foreign jurisdiction."""
    monkeypatch.setattr(
        'legal_api.services.flags.value',
        lambda flag: "BC BEN CC ULC C CBEN CCC CUL"  if flag == 'supported-consent-continuation-out-entities' else {}
    )
    business = Business(
        identifier='BC1234567',
        legal_type='BC',
        state=Business.State.ACTIVE,
        founding_date=datetime.utcnow()
    )
    filing = copy.deepcopy(FILING_HEADER)
    filing['filing']['consentContinuationOut'] = copy.deepcopy(CONSENT_CONTINUATION_OUT)
    filing['filing']['header']['name'] = 'consentContinuationOut'

    if test_name == 'FAIL_NO_COUNTRY':
        del filing['filing']['consentContinuationOut']['foreignJurisdiction']['country']
    elif test_name == 'FAIL_INVALID_COUNTRY':
        filing['filing']['consentContinuationOut']['foreignJurisdiction']['country'] = 'NONE'
    elif test_name == 'FAIL_REGION_BC':
        filing['filing']['consentContinuationOut']['foreignJurisdiction']['region'] = 'BC'
    elif test_name == 'FAIL_INVALID_REGION':
        filing['filing']['consentContinuationOut']['foreignJurisdiction']['region'] = 'NONE'
    elif test_name == 'FAIL_INVALID_US_REGION':
        filing['filing']['consentContinuationOut']['foreignJurisdiction']['country'] = 'US'
        filing['filing']['consentContinuationOut']['foreignJurisdiction']['region'] = 'NONE'

    err = validate(business, filing)

    # validate outcomes
    if test_name != 'SUCCESS':
        assert expected_code == err.code
        if message:
            assert message == err.msg[0]['error']
    else:
        assert not err


def test_valid_foreign_jurisdiction(session, monkeypatch):
    """Assert valid foreign jurisdiction."""
    monkeypatch.setattr(
        'legal_api.services.flags.value',
        lambda flag: "BC BEN CC ULC C CBEN CCC CUL"  if flag == 'supported-consent-continuation-out-entities' else {}
    )
    business = Business(
        identifier='BC1234567',
        legal_type='BC',
        state=Business.State.ACTIVE,
        founding_date=datetime.utcnow()
    )
    filing = copy.deepcopy(FILING_HEADER)
    filing['filing']['header']['name'] = 'consentContinuationOut'

    for country in pycountry.countries:
        filing['filing']['consentContinuationOut'] = copy.deepcopy(CONSENT_CONTINUATION_OUT)
        filing['filing']['consentContinuationOut']['foreignJurisdiction']['country'] = country.alpha_2
        if country.alpha_2 in ('CA', 'US'):
            for region in pycountry.subdivisions.get(country_code=country.alpha_2):
                region_code = region.code.replace(f'{country.alpha_2}-', '')
                if country.alpha_2 == 'CA' and region_code == 'BC':
                    region_code = 'FEDERAL'  # Testing Federal code instead of invalid code BC

                filing['filing']['consentContinuationOut']['foreignJurisdiction']['region'] = region_code
        else:
            del filing['filing']['consentContinuationOut']['foreignJurisdiction']['region']

        err = validate(business, filing)
        assert not err


@pytest.mark.parametrize(
    'test_name, expected_code, message',
    [
        ('FAIL_EXIST', HTTPStatus.BAD_REQUEST,
         "Can't have new consent for same jurisdiction if an unexpired one already exists"),
        ('SUCCESS', None, None)
    ]
)
def test_validate_existing_cco(session, test_name, expected_code, message, monkeypatch):
    """Assert validate foreign jurisdiction exist."""
    monkeypatch.setattr(
        'legal_api.services.flags.value',
        lambda flag: "BC BEN CC ULC C CBEN CCC CUL"  if flag == 'supported-consent-continuation-out-entities' else {}
    )
    business = factory_business(identifier='BC1234567', entity_type='BC', founding_date=datetime.utcnow())
    filing = copy.deepcopy(FILING_HEADER)
    filing['filing']['consentContinuationOut'] = copy.deepcopy(CONSENT_CONTINUATION_OUT)
    filing['filing']['header']['name'] = 'consentContinuationOut'
    effective_date = datetime.utcnow()
    if test_name == 'SUCCESS':
        effective_date -= datedelta.datedelta(months=6, days=5)

    previous_filing = factory_completed_filing(business, filing, filing_date=effective_date)

    foreign_jurisdiction = filing['filing']['consentContinuationOut']['foreignJurisdiction']

    consent_continuation_out = ConsentContinuationOut()
    consent_continuation_out.consent_type = ConsentContinuationOut.ConsentTypes.continuation_out
    consent_continuation_out.foreign_jurisdiction = foreign_jurisdiction.get('country')
    consent_continuation_out.foreign_jurisdiction_region = foreign_jurisdiction.get('region').upper()
    consent_continuation_out.expiry_date = get_cco_expiry_date(effective_date)

    consent_continuation_out.filing_id = previous_filing.id
    consent_continuation_out.business_id = business.id
    business.consent_continuation_outs.append(consent_continuation_out)
    business.save()

    err = validate(business, filing)

    # validate outcomes
    if test_name != 'SUCCESS':
        assert expected_code == err.code
        if message:
            assert message == err.msg[0]['error']
    else:
        assert not err


@pytest.mark.parametrize(
    'test_status, file_number, expected_code',
    [
        ('FAIL', None, HTTPStatus.UNPROCESSABLE_ENTITY),
        ('SUCCESS', '12345678901234567890', None)
    ]
)
def test_consent_continuation_out_court_order(session, test_status, file_number, expected_code, monkeypatch):
    """Assert valid court order."""
    monkeypatch.setattr(
        'legal_api.services.flags.value',
        lambda flag: "BC BEN CC ULC C CBEN CCC CUL"  if flag == 'supported-consent-continuation-out-entities' else {}
    )
    business = Business(
        identifier='BC1234567',
        legal_type='BC',
        state=Business.State.ACTIVE,
        founding_date=datetime.utcnow()
    )
    filing = copy.deepcopy(FILING_HEADER)
    filing['filing']['consentContinuationOut'] = copy.deepcopy(CONSENT_CONTINUATION_OUT)
    filing['filing']['header']['name'] = 'consentContinuationOut'

    if file_number:
        court_order = {}
        court_order['fileNumber'] = file_number
        filing['filing']['consentContinuationOut']['courtOrder'] = court_order
    else:
        del filing['filing']['consentContinuationOut']['courtOrder']['fileNumber']

    err = validate(business, filing)

    # validate outcomes
    if test_status == 'FAIL':
        assert expected_code == err.code
    else:
        assert not err
