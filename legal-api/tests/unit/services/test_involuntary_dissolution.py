# Copyright © 2024 Province of British Columbia
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

"""Tests for the Involuntary Dissolution Service.

Test suite to ensure that the Involuntary Dissolution Service is working as expected.
"""
import copy

import pytest
from datedelta import datedelta
from registry_schemas.example_data import FILING_HEADER, RESTORATION, TRANSITION_FILING_TEMPLATE

from legal_api.models import Batch, Business
from legal_api.services import InvoluntaryDissolutionService
from legal_api.utils.datetime import datetime
from tests.unit.models import (
    factory_batch,
    factory_batch_processing,
    factory_business,
    factory_completed_filing,
    factory_pending_filing,
)


RESTORATION_FILING = copy.deepcopy(FILING_HEADER)
RESTORATION_FILING['filing']['restoration'] = RESTORATION


@pytest.mark.parametrize(
        'test_name, eligible', [
            ('TEST_ELIGIBLE', True),
            ('TEST_INELIGIBLE', False)
        ]
)
def test_check_business_eligibility(session, test_name, eligible):
    """Assert service returns check of business eligibility for involuntary dissolution."""
    identifier = 'BC7654321'
    business = factory_business(identifier=identifier, entity_type=Business.LegalTypes.COMP.value)
    if not eligible:
        business.no_dissolution = True
        business.save()

    result = InvoluntaryDissolutionService.check_business_eligibility(identifier)
    assert result == eligible 


def test_get_businesses_eligible_count(session):
    """Assert service returns the number of businesses eligible for involuntary dissolution."""
    count = InvoluntaryDissolutionService.get_businesses_eligible_count()
    assert count == 0


@pytest.mark.parametrize(
        'test_name, state, exclude', [
            ('TEST_ACTIVE', 'ACTIVE', False),
            ('TEST_HISTORICAL', 'HISTORICAL', True),
            ('TEST_LIQUIDATION', 'LIQUIDATION', True)
        ]
)
def test_get_businesses_eligible_query_active_business(session, test_name, state, exclude):
    """Assert service returns eligible business for active businesses."""
    business = factory_business(identifier='BC1234567', entity_type=Business.LegalTypes.COMP.value, state=state)
    result = InvoluntaryDissolutionService._get_businesses_eligible_query().all()
    if exclude:
        assert not result
    else:
        assert result
        assert result[0] == business


@pytest.mark.parametrize(
        'test_name, legal_type, exclude', [
            ('TEST_BC', 'BC', False),
            ('TEST_ULC', 'ULC', False),
            ('TEST_CCC', 'CC', False),
            ('TEST_BEN', 'BEN', False),
            ('TEST_CONTINUE_IN', 'C', False),
            ('TEST_ULC_CONTINUE_IN', 'CUL', False),
            ('TEST_CCC_CONTINUE_IN', 'CCC', False),
            ('TEST_BEN_CONTINUE_IN', 'CBEN', False),
            ('TEST_XPRO', 'A', False),
            ('TEST_LLC', 'LLC', False),
            ('TEST_COOP', 'CP', True),
            ('TEST_SP', 'SP', True),
            ('TEST_GP', 'GP', True)
        ]
)
def test_get_businesses_eligible_query_eligible_type(session, test_name, legal_type, exclude):
    """Assert service returns eligible business for businesses with eligible types."""
    business = factory_business(identifier='BC1234567', entity_type=legal_type)

    result = InvoluntaryDissolutionService._get_businesses_eligible_query().all()
    if exclude:
        assert not result
    else:
        assert result
        assert result[0] == business


@pytest.mark.parametrize(
        'test_name, no_dissolution, exclude', [
            ('TEST_NO_DISSOLUTION', True, True),
            ('TEST_DISSOLUTION', False, False),
        ]
)
def test_get_businesses_eligible_query_no_dissolution(session, test_name, no_dissolution, exclude):
    """Assert service returns eligible business for businesses with no_dissolution flag off."""
    business = factory_business(identifier='BC1234567', entity_type=Business.LegalTypes.COMP.value)
    business.no_dissolution = no_dissolution
    business.save()

    result = InvoluntaryDissolutionService._get_businesses_eligible_query().all()
    if exclude:
        assert not result
    else:
        assert result
        assert result[0] == business


@pytest.mark.parametrize(
        'test_name, batch_status, batch_processing_status, exclude', [
            ('IN_DISSOLUTION', 'PROCESSING', 'PROCESSING', True),
            ('IN_DISSOLUTION_BATCH_COMPLETE', 'COMPLETED', 'WITHDRAWN', False),
            ('IN_DISSOLUTION_COMPLETED', 'PROCESSING', 'COMPLETED', False),
            ('IN_DISSOLUTION_WITHDRAWN', 'PROCESSING', 'WITHDRAWN', False),
            ('NOT_IN_DISSOLUTION', None, None, False),
        ]
)
def test_get_businesses_eligible_query_in_dissolution(session, test_name, batch_status, batch_processing_status, exclude):
    """Assert service returns eligible business for businesses not already in dissolution."""
    business = factory_business(identifier='BC1234567', entity_type=Business.LegalTypes.COMP.value)
    if test_name.startswith('IN_DISSOLUTION'):
        batch = factory_batch(
            batch_type = Batch.BatchType.INVOLUNTARY_DISSOLUTION,
            status = batch_status,
        )
        factory_batch_processing(
            batch_id = batch.id,
            business_id = business.id,
            identifier = business.identifier,
            status = batch_processing_status
        )
    
    result = InvoluntaryDissolutionService._get_businesses_eligible_query().all()
    if exclude:
        assert not result
    else:
        assert result
        assert result[0] == business


@pytest.mark.parametrize(
        'test_name, exclude', [
            ('RECOGNITION_OVERDUE', False),
            ('RESTORATION_OVERDUE', False),
            ('AR_OVERDUE', False),
            ('NO_OVERDUE', True)
        ]
)
def test_get_businesses_eligible_query_specific_filing_overdue(session, test_name, exclude):
    """Assert service returns eligible business including business which has specific filing overdue."""
    if test_name == 'RECOGNITION_OVERDUE':
        business = factory_business(identifier='BC1234567', entity_type=Business.LegalTypes.COMP.value)
    elif test_name == 'RESTORATION_OVERDUE':
        business = factory_business(identifier='BC1234567', entity_type=Business.LegalTypes.COMP.value)
        effective_date = datetime.utcnow() - datedelta(years=3)
        factory_completed_filing(business, RESTORATION_FILING, filing_type='restoration', filing_date=effective_date)
    elif test_name == 'AR_OVERDUE':
        last_ar_date = datetime.utcnow() - datedelta(years=3)
        business = factory_business(identifier='BC1234567', entity_type=Business.LegalTypes.COMP.value, last_ar_date=last_ar_date)
    else:
        business = factory_business(identifier='BC1234567', entity_type=Business.LegalTypes.COMP.value, founding_date=datetime.utcnow())

    business.save()

    result = InvoluntaryDissolutionService._get_businesses_eligible_query().all()
    if exclude:
        assert not result
    else:
        assert result
        assert result[0] == business


@pytest.mark.parametrize(
        'test_name, exclude', [
            ('TRANSITION', True),
            ('NO_NEED_TRANSITION_NEW_ACT', True),
            ('NO_NEED_TRANSITION_1_YEAR', True),
            ('MISSING_TRANSITION', False)
        ]
)
def test_get_businesses_eligible_query_no_transition_filed(session, test_name, exclude):
    """Assert service returns eligible business excluding business which doesn't file transition."""
    business = factory_business(identifier='BC1234567', entity_type=Business.LegalTypes.COMP.value, last_ar_date=datetime.utcnow())
    restoration_filing = factory_completed_filing(business, RESTORATION_FILING, filing_type='restoration')
    if test_name == 'TRANSITION':
        factory_completed_filing(business, TRANSITION_FILING_TEMPLATE, filing_type='transition')
    elif test_name == 'NO_NEED_TRANSITION_NEW_ACT':
        business.founding_date = datetime.utcnow()
        business.save()
    elif test_name == 'NO_NEED_TRANSITION_1_YEAR':
        restoration_filing.effective_date = datetime.utcnow()
        restoration_filing.save()

    result = InvoluntaryDissolutionService._get_businesses_eligible_query().all()
    if exclude:
        assert not result
    else:
        assert result
        assert result[0] == business


@pytest.mark.parametrize(
        'test_name, exclude', [
            ('FED', True),
            ('NO_FED', False)
        ]
)
def test_get_businesses_eligible_query_fed_filing(session, test_name, exclude):
    """Assert service returns eligible business excluding business which has future effective filings."""
    business = factory_business(identifier='BC1234567', entity_type=Business.LegalTypes.COMP.value)
    if test_name == 'FED':
        factory_pending_filing(business, RESTORATION_FILING)
    
    result = InvoluntaryDissolutionService._get_businesses_eligible_query().all()
    if exclude:
        assert not result
    else:
        assert result
        assert result[0] == business


@pytest.mark.parametrize(
    'test_name, exclude', [
        ('LIMITED_RESTORATION', True),
        ('LIMITED_RESTORATION_EXPIRED', False),
        ('NON_LIMITED_RESTORATION', False)
    ]
)
def test_get_businesses_eligible_query_limited_restored(session, test_name, exclude):
    """Assert service returns eligible business excluding business which is in limited restoration status."""
    business = factory_business(identifier='BC1234567', entity_type=Business.LegalTypes.COMP.value)
    if test_name == 'LIMITED_RESTORATION':
        business.restoration_expiry_date = datetime.utcnow() + datedelta(years=1)
    elif test_name == 'LIMITED_RESTORATION_EXPIRED':
        business.restoration_expiry_date = datetime.utcnow() + datedelta(years=-1)
    business.save()

    result = InvoluntaryDissolutionService._get_businesses_eligible_query().all()
    if exclude:
        assert not result
    else:
        assert result
        assert result[0] == business


@pytest.mark.parametrize(
        'test_name, jurisdiction, region, exclude', [
            ('XPRO_NWPTA', 'CA', 'AB', True),
            ('XPRO_NON_NWPTA', 'CA', 'ON', False),
            ('NON_XPRO', None, None, False)
        ]
)
def test_get_businesses_eligible_query_xpro_from_nwpta(session, test_name, jurisdiction, region, exclude):
    """Assert service returns eligible business excluding expro from NWPTA jurisdictions."""
    if test_name == 'NON_XPRO':
        business = factory_business(identifier='BC1234567', entity_type=Business.LegalTypes.COMP.value)
    else:
        business = factory_business(identifier='BC1234567', entity_type=Business.LegalTypes.EXTRA_PRO_A.value)
    business.jurisdiction = jurisdiction
    business.foreign_jurisdiction_region = region
    business.save()

    result = InvoluntaryDissolutionService._get_businesses_eligible_query().all()
    if exclude:
        assert not result
    else:
        assert result
        assert result[0] == business
