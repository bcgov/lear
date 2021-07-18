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

"""Tests to assure the business-filing end-point - LEDGER SEARCH

Test-Suite to ensure that the /businesses/_id_/filings LEDGER SEARCH endpoint is working as expected.
"""
import copy
import json
from datetime import datetime
from http import HTTPStatus
from typing import Final

import datedelta
import pytest
from dateutil.parser import parse
from flask import current_app
from registry_schemas.example_data import (
    ALTERATION_FILING_TEMPLATE,
    ANNUAL_REPORT,
    CHANGE_OF_ADDRESS,
    CHANGE_OF_DIRECTORS,
    CORRECTION_AR,
    CORRECTION_INCORPORATION,
    FILING_HEADER,
    INCORPORATION_FILING_TEMPLATE,
    SPECIAL_RESOLUTION,
    TRANSITION_FILING_TEMPLATE,
)

from legal_api.models import Business, UserRoles
from legal_api.resources.business.business_filings import Filing, ListFilingResource
from legal_api.services.authz import BASIC_USER, STAFF_ROLE
from legal_api.utils.legislation_datetime import LegislationDatetime
from tests import integration_payment
from tests.unit.core.test_filing_ledger import load_ledger
from tests.unit.models import (  # noqa:E501,I001
    factory_business,
    factory_business_mailing_address,
    factory_completed_filing,
    factory_filing,
    factory_user,
)
from tests.unit.services.utils import create_header

def test_get_all_business_filings_only_one_in_ledger(session, client, jwt):
    """Assert that the business info can be received in a valid JSONSchema format."""
    import copy
    identifier = 'CP7654321'
    b = factory_business(identifier)
    filings = factory_filing(b, ANNUAL_REPORT)

    ar = copy.deepcopy(ANNUAL_REPORT)
    ar['filing']['header']['filingId'] = filings.id
    ar['filing']['header']['colinIds'] = []

    print('test_get_all_business_filings - filing:', filings)

    rv = client.get(f'/api/v1/businesses/{identifier}/filings',
                    headers=create_header(jwt, [STAFF_ROLE], identifier))

    assert rv.status_code == HTTPStatus.OK
    assert len(rv.json.get('filings')) == 0  # The endpoint will return only completed filings


def test_get_all_business_filings_multi_in_ledger(session, client, jwt):
    """Assert that the business info can be received in a valid JSONSchema format."""
    import copy
    from tests import add_years

    ar = copy.deepcopy(ANNUAL_REPORT)
    identifier = 'CP7654321'

    # create business
    b = factory_business(identifier)

    # add 3 filings, add a year onto the AGM date
    for i in range(0, 3):
        ar['filing']['annualReport']['annualGeneralMeetingDate'] = \
            datetime.date(add_years(datetime(2001, 8, 5, 7, 7, 58, 272362), i)).isoformat()
        factory_filing(b, ar)

    rv = client.get(f'/api/v1/businesses/{identifier}/filings',
                    headers=create_header(jwt, [STAFF_ROLE], identifier))

    assert rv.status_code == HTTPStatus.OK
    assert len(rv.json.get('filings')) == 0


def test_ledger_search(session, client, jwt):
    """Assert that the ledger returns values for all the expected keys."""
    # setup
    identifier = 'BC1234567'
    founding_date = datetime.utcnow() - datedelta.datedelta(months=len(Filing.FILINGS.keys()))
    business = factory_business(identifier=identifier, founding_date=founding_date, last_ar_date=None, entity_type=Business.LegalTypes.BCOMP.value)
    num_of_files = load_ledger(business, founding_date)

    # test
    rv = client.get(f'/api/v1/businesses/{identifier}/filings',
                headers=create_header(jwt, [UserRoles.SYSTEM.value], identifier))

    ledger = rv.json

    with open("ledger.json", "w") as outfile:
        json.dump(ledger, outfile)

    # Did we get the full set
    assert len(ledger['filings']) == num_of_files

    # Fully examine 1 filing - alteration
    alteration = next((f for f in ledger['filings'] if f.get('name')=='alteration'), None)

    assert alteration
    assert 16 == len(alteration.keys())
    assert 'availableOnPaperOnly' in alteration
    assert 'effectiveDate' in alteration
    assert 'filingId' in alteration
    assert 'name' in alteration
    assert 'paymentStatusCode' in alteration
    assert 'status' in alteration
    assert 'submittedDate' in alteration
    assert 'submitter' in alteration
    # assert alteration['commentsLink']
    # assert alteration['correctionLink']
    # assert alteration['filingLink']
