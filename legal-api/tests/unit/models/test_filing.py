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

"""Tests to assure the Filing Model.

Test-Suite to ensure that the Business Model is working as expected.
"""
import datetime
import json
from http import HTTPStatus

import pytest

from legal_api.exceptions import BusinessException
from legal_api.models import Business, Filing
from tests import EPOCH_DATETIME, FROZEN_DATETIME


def factory_business(identifier):
    """Create a business entity."""
    business = Business(legal_name=f'legal_name-{identifier}',
                        founding_date=EPOCH_DATETIME,
                        dissolution_date=EPOCH_DATETIME,
                        identifier=identifier,
                        tax_id='BN123456789',
                        fiscal_year_end_date=FROZEN_DATETIME)
    business.save()
    return business


def test_minimal_filing_json(session):
    """Assert that a minimal filing can be created."""
    b = factory_business('CP1234567')

    data = {'filing': 'not a real filing, fail validation'}

    filing = Filing()
    filing.business_id = b.id
    filing.filing_date = datetime.datetime.utcnow()
    filing.filing_data = json.dumps(data)
    filing.save()

    assert filing.id is not None


def test_filing_block_orm_delete(session):
    """Assert that attempting to delete a filing will raise a BusinessException."""
    from legal_api.exceptions import BusinessException

    b = factory_business('CP1234567')

    data = {'filing': 'not a real filing, fail validation'}

    filing = Filing()
    filing.business_id = b.id
    filing.filing_date = datetime.datetime.utcnow()
    filing.filing_data = json.dumps(data)
    filing.save()

    with pytest.raises(BusinessException) as excinfo:
        session.delete(filing)
        session.commit()

    assert excinfo.value.status_code == HTTPStatus.FORBIDDEN
    assert excinfo.value.error == 'Deletion not allowed.'


AR_FILING = {
    'filing': {
        'header': {
            'name': 'annual_report',
            'date': '2019-04-08'
        },
        'business': {
            'cacheId': 1,
            'foundingDate': '2007-04-08',
            'identifier': 'CP1234567',
            'lastLedgerTimestamp': '2019-04-15T20:05:49.068272+00:00',
            'legalName': 'legal name - CP1234567'
        },
        'annualReport': {
            'annualGeneralMeetingDate': '2019-04-08',
            'certifiedBy': 'full name',
            'email': 'no_one@never.get'
        }
    }
}


def factory_filing(business, data_dict):
    """Create a filing."""
    filing = Filing()
    filing.business_id = business.id
    filing.filing_date = FROZEN_DATETIME
    filing.filing_json = data_dict
    filing.save()
    return filing


def test_filing_json(session):
    """Assert that an AR filing can be saved."""
    b = factory_business('CP1234567')
    filing = factory_filing(b, AR_FILING)

    assert filing.id
    assert filing.json() == {'filingDate': filing.filing_date.isoformat(),
                             'filingType': 'annual_report',
                             'jsonSubmission': AR_FILING}


def test_filing_delete_is_blocked(session):
    """Assert that an AR filing can be saved."""
    b = factory_business('CP1234567')
    filing = factory_filing(b, AR_FILING)

    with pytest.raises(BusinessException) as excinfo:
        filing.delete()

    assert excinfo.value.status_code == HTTPStatus.FORBIDDEN
    assert excinfo.value.error == 'Deletion not allowed.'


def test_filing_missing_name(session):
    """Assert that an AR filing can be saved."""
    import copy
    identifier = 'CP7654321'
    b = factory_business(identifier)
    ar = copy.deepcopy(AR_FILING)
    ar['filing']['header'].pop('name', None)

    with pytest.raises(BusinessException) as excinfo:
        factory_filing(b, ar)

    assert excinfo.value.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert excinfo.value.error == 'No filings found.'


def test_ar_payment_invalid_filing(session):
    """Assert that an AR filing can be saved."""
    import copy
    identifier = 'CP7654321'
    b = factory_business(identifier)
    ar = copy.deepcopy(AR_FILING)
    ar['filing'].pop('business', None)
    ar['filing']['header']['paymentToken'] = 'token'

    with pytest.raises(BusinessException) as excinfo:
        factory_filing(b, ar)

    assert excinfo.value.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert excinfo.value.error.startswith('Invalid filing')


def test_filing_dump_json(session):
    """Assert the filing json serialization works correctly."""
    import copy
    identifier = 'CP7654321'
    b = factory_business(identifier)

    # Check base JSON
    ar = copy.deepcopy(AR_FILING)
    filings = factory_filing(b, ar)
    ab = {'filingDate': '2001-08-05T07:07:58.272362+00:00',
          'filingType': 'annual_report'
          }
    ab['jsonSubmission'] = ar
    assert filings.json() == ab

    # Check payment token
    ar = copy.deepcopy(AR_FILING)
    ar['filing']['header']['paymentToken'] = 'token'
    filings = factory_filing(b, ar)
    ab = {'filingDate': '2001-08-05T07:07:58.272362+00:00',
          'filingType': 'annual_report',
          'paymentToken': 'token'
          }
    ab['jsonSubmission'] = ar
    assert filings.json() == ab

    # check submitter
    ar = copy.deepcopy(AR_FILING)
    filings = factory_filing(b, ar)
    ab = {'filingDate': '2001-08-05T07:07:58.272362+00:00',
          'filingType': 'annual_report',
          'submitter': 'submitter id'
          }
    ab['jsonSubmission'] = ar
    filings.submitter = 'submitter id'
    assert filings.json() == ab


def test_filing_save_to_session(session):
    """Assert that the filing is saved to the session but not committed."""
    from sqlalchemy.orm.session import Session
    # b = factory_business('CP1234567')
    # filing = factory_filing(b, AR_FILING)

    filing = Filing()

    assert not session.new
    assert not Session.object_session(filing)

    filing.save_to_session()

    assert filing.id is None
    assert session.new
    assert Session.object_session(filing)
