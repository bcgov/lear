# Copyright © 2021 Province of British Columbia
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

"""Tests to assure the Filing Domain is working as expected."""
import copy

import datedelta
import pytest
from registry_schemas.example_data import FILING_TEMPLATE

from legal_api.core import Filing as CoreFiling
from legal_api.models import Business, Comment, Filing, UserRoles
from legal_api.models.user import UserRoles
from legal_api.utils.datetime import datetime
from tests.unit.models import factory_business, factory_completed_filing, factory_user
from tests.unit.services.utils import helper_create_jwt


def load_ledger(business, founding_date):
    """Create a ledger of all filing types."""
    i = 0
    for k, filing_meta in Filing.FILINGS.items():
        filing = copy.deepcopy(FILING_TEMPLATE)
        filing['filing']['header']['name'] = filing_meta['name']
        if filing_meta['name'] == 'restoration':
            filing['filing']['restoration'] = {}
            filing['filing']['restoration']['type'] = 'fullRestoration'
        elif filing_meta['name'] == 'dissolution':
            filing['filing']['dissolution'] = {}
            filing['filing']['dissolution']['dissolutionType'] = 'voluntary'
        elif filing_meta['name'] == 'amalgamationApplication':
            filing['filing']['amalgamationApplication'] = {}
            filing['filing']['amalgamationApplication']['type'] = 'regular'
        elif filing_meta['name'] == 'transparencyRegister':
            filing['filing']['transparencyRegister'] = {
                'type': 'initial',
                'ledgerReferenceNumber': '123ewd2'
            }
        elif filing_meta['name'] == 'changeOfReceivers':
            filing['filing']['changeOfReceivers'] = {
                'type': 'appointReceiver'
            }
        f = factory_completed_filing(business, filing, filing_date=founding_date + datedelta.datedelta(months=i))
        for c in range(i):
            comment = Comment()
            comment.comment = f'this comment {c}'
            f.comments.append(comment)
        f.save()
        i += 1
    return i


def test_simple_ledger_search(session):
    """Assert that the ledger returns values for all the expected keys."""
    # setup
    identifier = 'BC1234567'
    founding_date = datetime.utcnow() - datedelta.datedelta(months=len(Filing.FILINGS.keys()))
    business = factory_business(identifier=identifier, founding_date=founding_date, last_ar_date=None, entity_type=Business.LegalTypes.BCOMP.value)
    num_of_files = load_ledger(business, founding_date)

    # test
    ledger = CoreFiling.ledger(business.id)

    # Did we get the full set
    assert len(ledger) == num_of_files

    # Fully examine 1 filing - alteration
    alteration = next((f for f in ledger if f.get('name') == 'alteration'), None)

    assert alteration
    assert 18 == len(alteration.keys())
    assert 'availableOnPaperOnly' in alteration
    assert 'effectiveDate' in alteration
    assert 'filingId' in alteration
    assert 'name' in alteration
    assert 'paymentStatusCode' in alteration
    assert 'paymentDate' in alteration
    assert 'status' in alteration
    assert 'submittedDate' in alteration
    assert 'submitter' in alteration
    assert 'displayLedger' in alteration
    assert 'withdrawalPending' in alteration
    # assert alteration['commentsLink']
    # assert alteration['correctionLink']
    # assert alteration['filingLink']


def test_common_ledger_items(session):
    """Assert that common ledger items works as expected."""
    identifier = 'BC1234567'
    founding_date = datetime.utcnow() - datedelta.datedelta(months=len(Filing.FILINGS.keys()))
    business = factory_business(identifier=identifier, founding_date=founding_date, last_ar_date=None,
                                entity_type=Business.LegalTypes.BCOMP.value)
    filing = copy.deepcopy(FILING_TEMPLATE)
    filing['filing']['header']['name'] = 'Involuntary Dissolution'
    completed_filing = \
        factory_completed_filing(business, filing, filing_date=founding_date + datedelta.datedelta(months=1))
    common_ledger_items = CoreFiling.common_ledger_items(identifier, completed_filing)
    assert common_ledger_items['documentsLink'] is None

    filing['filing']['header']['name'] = 'dissolution'
    filing['filing']['dissolution'] = {}
    filing['filing']['dissolution']['dissolutionType'] = 'voluntary'
    completed_filing = \
        factory_completed_filing(business, filing, filing_date=founding_date + datedelta.datedelta(months=1))
    common_ledger_items = CoreFiling.common_ledger_items(identifier, completed_filing)
    assert common_ledger_items['documentsLink'] is not None
    assert common_ledger_items['displayLedger'] is True

    filing['filing']['dissolution']['dissolutionType'] = 'involuntary'
    completed_filing = \
        factory_completed_filing(business, filing, filing_date=founding_date + datedelta.datedelta(months=1))
    common_ledger_items = CoreFiling.common_ledger_items(identifier, completed_filing)
    assert common_ledger_items['documentsLink'] is not None
    assert common_ledger_items['displayLedger'] is False

    filing['filing']['header']['name'] = 'adminFreeze'
    completed_filing = \
        factory_completed_filing(business, filing, filing_date=founding_date + datedelta.datedelta(months=1), filing_type='adminFreeze')
    common_ledger_items = CoreFiling.common_ledger_items(identifier, completed_filing)
    assert common_ledger_items['displayLedger'] is False

    completed_filing.withdrawal_pending = True
    common_ledger_items = CoreFiling.common_ledger_items(identifier, completed_filing)
    assert common_ledger_items['withdrawalPending'] is True
