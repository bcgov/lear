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

from legal_api.models import Business
from legal_api.services import InvoluntaryDissolutionService
from legal_api.utils.datetime import datetime
from tests.unit.models import factory_business, factory_completed_filing, factory_pending_filing


RESTORATION_FILING = copy.deepcopy(FILING_HEADER)
RESTORATION_FILING['filing']['restoration'] = RESTORATION


def test_get_businesses_eligible_count(session):
    """Assert service returns the number of businesses eligible for involuntary dissolution."""
    count = InvoluntaryDissolutionService.get_businesses_eligible_count()
    assert count == 0


@pytest.mark.parametrize(
        'test_name, exclude', [
            ('RECOGNITION_OVERDUE', False),
            ('RESTORATION_OVERDUE', False),
            ('AR_OVERDUE', False),
            ('NO_OVERDUE', True)
        ]
)
def test_get_businesses_eligible_count_specific_filing_overdue(session, test_name, exclude):
    """Assert service returns eligible count including business which has specific filing overdue."""
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

    count = InvoluntaryDissolutionService.get_businesses_eligible_count()
    if exclude:
        assert count == 0
    else:
        assert count == 1


@pytest.mark.parametrize(
        'test_name, exclude', [
            ('TRANSITION', True),
            ('NO_NEED_TRANSITION', True),
            ('MISSING_TRANSITION', False)
        ]
)
def test_get_businesses_eligible_count_no_transition_filed(session, test_name, exclude):
    business = factory_business(identifier='BC1234567', entity_type=Business.LegalTypes.COMP.value, last_ar_date=datetime.utcnow())
    factory_completed_filing(business, RESTORATION_FILING, filing_type='restoration')
    if test_name == 'TRANSITION':
        factory_completed_filing(business, TRANSITION_FILING_TEMPLATE, filing_type='transition')
    elif test_name == 'NO_NEED_TRANSITION':
        business.founding_date = datetime.utcnow()
        business.save()

    count = InvoluntaryDissolutionService.get_businesses_eligible_count()
    if exclude:
        assert count == 0
    else:
        assert count == 1


@pytest.mark.parametrize(
        'test_name, exclude', [
            ('FED', True),
            ('NO_FED', False)
        ]
)
def test_get_businesses_eligible_count_fed_filing(session, test_name, exclude):
    """Assert service returns eligible count excluding business which has future effective filings."""
    bussiness = factory_business(identifier='BC1234567', entity_type=Business.LegalTypes.COMP.value)
    if test_name == 'FED':
        factory_pending_filing(bussiness, RESTORATION_FILING)
    
    count = InvoluntaryDissolutionService.get_businesses_eligible_count()
    if exclude:
        assert count == 0
    else:
        assert count == 1


@pytest.mark.parametrize(
        'test_name, exclude', [
            ('COA', True),
            ('NO_COA', False)
        ]
)
def test_get_businesses_eligible_count_coa_filing(session, test_name, exclude):
    """Assert service returns eligible count excluding business which has change of address within last 32 days."""
    bussiness = factory_business(identifier='BC1234567', entity_type=Business.LegalTypes.COMP.value)
    if test_name == 'COA':
        bussiness.last_coa_date = datetime.utcnow()
    bussiness.save()

    count = InvoluntaryDissolutionService.get_businesses_eligible_count()
    if exclude:
        assert count == 0
    else:
        assert count == 1


@pytest.mark.parametrize(
        'test_name, jurisdiction, region, exclude', [
            ('XPRO_NWPTA', 'CA', 'AB', True),
            ('XPRO_NON_NWPTA', 'CA', 'ON', False),
            ('NON_XPRO', None, None, False)
        ]
)
def test_get_businesses_eligible_count_xpro_from_nwpta(session, test_name, jurisdiction, region, exclude):
    """Assert service returns eligible count excluding expro from NWPTA jurisdictions."""
    if test_name == 'NON_XPRO':
        business = factory_business(identifier='BC1234567', entity_type=Business.LegalTypes.COMP.value)
    else:
        business = factory_business(identifier='BC1234567', entity_type=Business.LegalTypes.EXTRA_PRO_A.value)
    business.jurisdiction = jurisdiction
    business.foreign_jurisdiction_region = region
    business.save()

    count = InvoluntaryDissolutionService.get_businesses_eligible_count()
    if exclude:
        assert count == 0
    else:
        assert count == 1
