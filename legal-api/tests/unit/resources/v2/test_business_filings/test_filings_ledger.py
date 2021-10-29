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
from datetime import date, datetime
from http import HTTPStatus
from typing import Final, Tuple

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
    FILING_TEMPLATE,
    INCORPORATION,
    INCORPORATION_FILING_TEMPLATE,
    SPECIAL_RESOLUTION,
    TRANSITION_FILING_TEMPLATE,
)

from legal_api.core import Filing, FilingMeta, FILINGS
from legal_api.models import Business, Comment, Filing as FilingStorage, UserRoles
from legal_api.resources.v1.business.business_filings import ListFilingResource
from legal_api.services.authz import BASIC_USER, STAFF_ROLE
from legal_api.utils.legislation_datetime import LegislationDatetime
from tests import api_v2, integration_payment
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

    rv = client.get(f'/api/v2/businesses/{identifier}/filings',
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

    rv = client.get(f'/api/v2/businesses/{identifier}/filings',
                    headers=create_header(jwt, [STAFF_ROLE], identifier))

    assert rv.status_code == HTTPStatus.OK
    assert len(rv.json.get('filings')) == 0


def test_ledger_search(session, client, jwt):
    """Assert that the ledger returns values for all the expected keys."""
    # setup
    identifier = 'BC1234567'
    founding_date = datetime.utcnow() - datedelta.datedelta(months=len(FILINGS.keys()))
    business = factory_business(identifier=identifier, founding_date=founding_date, last_ar_date=None, entity_type=Business.LegalTypes.BCOMP.value)
    num_of_files = load_ledger(business, founding_date)

    # test
    rv = client.get(f'/api/v2/businesses/{identifier}/filings',
                headers=create_header(jwt, [UserRoles.SYSTEM.value], identifier))

    ledger = rv.json

    # Did we get the full set
    assert len(ledger['filings']) == num_of_files

    # Fully examine 1 filing - alteration
    alteration = next((f for f in ledger['filings'] if f.get('name')=='alteration'), None)

    assert alteration
    assert 15 == len(alteration.keys())
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


###
#  Check elements of the ledger search
###

def ledger_element_setup_help(identifier: str, filing_name: str = 'brokenFiling') -> Tuple[Business, FilingStorage]:
    """Render common setup for the element tests."""
    founding_date = datetime.utcnow()
    business = factory_business(identifier=identifier, founding_date=founding_date, last_ar_date=None, entity_type=Business.LegalTypes.BCOMP.value)
    return business, ledger_element_setup_filing(business, filing_name, filing_date=founding_date + datedelta.datedelta(months=1))

def ledger_element_setup_filing(business, filing_name, filing_date):
    filing = copy.deepcopy(FILING_TEMPLATE)
    filing['filing']['header']['name'] = filing_name
    f = factory_completed_filing(business, filing, filing_date=filing_date)
    return f
 

def test_ledger_comment_count(session, client, jwt):
    """Assert that the ledger returns the correct number of comments."""
    # setup
    identifier = 'BC1234567'
    number_of_comments = 10
    business, filing_storage = ledger_element_setup_help(identifier)
    for c in range(number_of_comments):
        comment = Comment()
        comment.comment = f'this comment {c}'
        filing_storage.comments.append(comment)
    filing_storage.save()

    # test
    rv = client.get(f'/api/v2/businesses/{identifier}/filings',
                headers=create_header(jwt, [UserRoles.SYSTEM.value], identifier))
    
    # validate
    assert rv.json['filings'][0]['commentsCount'] == number_of_comments

@pytest.mark.parametrize('test_name, file_number, order_date, effect_of_order, order_details, expected',[
    ('all_elements', 'ABC123', datetime.utcnow(), 'effect', 'details',
        ['effectOfOrder', 'fileNumber', 'orderDate', 'orderDetails']),
    ('no_elements', None, None, None, None,
        []),
    ('no-file-number-or-details', None, datetime.utcnow(), None, None,
        []),
    ('date', 'ABC123', datetime.utcnow(), None, None,
        ['fileNumber', 'orderDate']),
    ('effect', 'ABC123', None, 'effect', None,
        ['effectOfOrder', 'fileNumber']),
    ('details', 'ABC123', None, None, 'details',
        ['fileNumber', 'orderDetails']),

])
def test_ledger_court_order(session, client, jwt, test_name, file_number, order_date, effect_of_order, order_details, expected):
    """Assert that the ledger returns court_order values."""
    # setup
    identifier = 'BC1234567'
    business, filing_storage = ledger_element_setup_help(identifier)

    filing_storage.court_order_file_number = file_number
    filing_storage.court_order_date = order_date
    filing_storage.court_order_effect_of_order = effect_of_order
    filing_storage.order_details = order_details

    filing_storage.save()

    # test
    rv = client.get(f'/api/v2/businesses/{identifier}/filings',
                headers=create_header(jwt, [UserRoles.SYSTEM.value], identifier))
    
    # validate
    assert rv.json['filings'][0]
    filing_json = rv.json['filings'][0]
    if expected:
        assert filing_json['data']['order']['fileNumber']
        assert set(filing_json['data']['order'].keys()) == set(expected)
    else:
        assert not filing_json.get('data')


def test_ledger_display_name_annual_report(session, client, jwt):
    """Assert that the ledger returns the correct number of comments."""
    # setup
    identifier = 'BC1234567'
    today = date.today().isoformat()
    annual_report_meta = {'annualReport':{
        'annualReportDate': today,
        'annualGeneralMeetingDate': today
    }}
    meta_data = {**{'applicationDate': today}, **annual_report_meta}

    business, filing_storage = ledger_element_setup_help(identifier, 'annualReport')
    filing_storage._meta_data = meta_data
    filing_storage.save()

    # test
    rv = client.get(f'/api/v2/businesses/{identifier}/filings',
                headers=create_header(jwt, [UserRoles.SYSTEM.value], identifier))
    
    # validate
    assert rv.json['filings'][0]
    filing_json = rv.json['filings'][0]
    assert filing_json['data'] == meta_data
    assert filing_json['displayName'] == f'Annual Report ({date.fromisoformat(today).year})'


def test_ledger_display_unknown_name(session, client, jwt):
    """Assert that the ledger returns the correct number of comments."""
    # setup
    identifier = 'BC1234567'
    meta_data = {'applicationDate': None}

    business, filing_storage = ledger_element_setup_help(identifier, 'someAncientNamedReport')
    filing_storage._meta_data = meta_data
    filing_storage.save()

    # test
    rv = client.get(f'/api/v2/businesses/{identifier}/filings',
                headers=create_header(jwt, [UserRoles.SYSTEM.value], identifier))

    # validate
    assert rv.json['filings'][0]
    filing_json = rv.json['filings'][0]
    assert filing_json['data'] == meta_data
    assert filing_json['displayName'] == 'Some Ancient Named Report'


def test_ledger_display_alteration_report(session, client, jwt):
    """Assert that the ledger returns the correct number of comments."""
    # setup
    identifier = 'BC1234567'
    today = date.today().isoformat()
    alteration_meta = {'alteration':{
        'fromLegalType': 'BC',
        'toLegalType': 'BEN'
    }}
    meta_data = {**{'applicationDate': today}, **alteration_meta}

    business, filing_storage = ledger_element_setup_help(identifier, 'alteration')
    filing_storage._meta_data = meta_data
    filing_storage.save()

    # test
    rv = client.get(f'/api/v2/businesses/{identifier}/filings',
                headers=create_header(jwt, [UserRoles.SYSTEM.value], identifier))
    
    # validate
    assert rv.json['filings'][0]
    filing_json = rv.json['filings'][0]
    assert filing_json['data'] == meta_data
    assert filing_json['displayName'] == f'Alteration'


def test_ledger_display_incorporation(session, client, jwt):
    """Assert that the ledger returns the correct number of comments."""
    # setup
    identifier = 'BC1234567'
    nr_number = 'NR000001'
    founding_date = datetime.utcnow()
    filing_date = founding_date
    filing_name = 'incorporationApplication'
    business_name = 'The Truffle House'
    entity_type = Business.LegalTypes.BCOMP.value

    business = factory_business(identifier=identifier, founding_date=founding_date, last_ar_date=None, entity_type=entity_type)
    business.legal_name = business_name
    business.save()

    filing = copy.deepcopy(FILING_HEADER)
    filing['filing'].pop('business')
    filing['filing']['header']['name'] = filing_name
    filing['filing'][filing_name] = INCORPORATION
    filing['filing'][filing_name]['nameRequest'] = 'NR0000001'
    filing['filing'][filing_name]['legalName'] = business_name

    f = factory_completed_filing(business, filing, filing_date=filing_date)
    today = filing_date.isoformat()
    ia_meta = {'legalFilings':[filing_name,],
               filing_name: {'nrNumber': nr_number,
                             'legalName': business_name}
    }
    f._meta_data = {**{'applicationDate': today}, **ia_meta}

    # test
    rv = client.get(f'/api/v2/businesses/{identifier}/filings',
                headers=create_header(jwt, [UserRoles.SYSTEM.value], identifier))

    # validate
    assert rv.json['filings']
    assert rv.json['filings'][0]['displayName'] == f'BC Benefit Company Incorporation Application'


def test_ledger_display_corrected_incorporation(session, client, jwt):
    """Assert that the ledger returns the correct number of comments."""
    # setup
    identifier = 'BC1234567'
    business, original = ledger_element_setup_help(identifier, 'incorporationApplication')
    correction = ledger_element_setup_filing(business, 'correction', filing_date=business.founding_date + datedelta.datedelta(months=3))
    original.parent_filing_id = correction.id
    original.save()

    # test
    rv = client.get(f'/api/v2/businesses/{identifier}/filings',
                headers=create_header(jwt, [UserRoles.SYSTEM.value], identifier))
    
    # validate
    assert rv.json['filings']
    for filing_json in rv.json['filings']:
        if filing_json['name'] == 'correction':
            assert filing_json['displayName'] == f'Correction'
        elif filing_json['name'] == 'incorporationApplication':
            assert filing_json['displayName'] == f'BC Benefit Company Incorporation Application - Corrected'
        else:
            assert False

def test_ledger_display_corrected_annual_report(session, client, jwt):
    """Assert that the ledger returns the correct number of comments."""
    # setup
    identifier = 'BC1234567'
    business, original = ledger_element_setup_help(identifier, 'annualReport')
    correction = ledger_element_setup_filing(business, 'correction', filing_date=business.founding_date + datedelta.datedelta(months=3))
    original.parent_filing_id = correction.id
    original.save()

    today = date.today().isoformat()
    correction_meta = {'legalFilings':['annualReport','correction']}
    correction._meta_data = {**{'applicationDate': today}, **correction_meta}
    correction.save()

    # test
    rv = client.get(f'/api/v2/businesses/{identifier}/filings',
                headers=create_header(jwt, [UserRoles.SYSTEM.value], identifier))
    
    # validate
    assert rv.json['filings']
    for filing_json in rv.json['filings']:
        if filing_json['name'] == 'correction':
            assert filing_json['displayName'] == f'Correction - Annual Report'
        elif filing_json['name'] == 'annualReport':
            assert filing_json['displayName'] == f'Annual Report - Corrected'
        else:
            assert False



@pytest.mark.parametrize(
    'test_name, submitter_role, jwt_role, username, expected',
    [
        ('staff-staff', UserRoles.STAFF.value, UserRoles.STAFF.value, 'idir/staff-user', 'idir/staff-user'),
        ('system-staff', UserRoles.SYSTEM.value, UserRoles.STAFF.value, 'system', 'system'),
        ('unknown-staff', None, UserRoles.STAFF.value, 'some-user', 'some-user'),
        ('system-public', UserRoles.SYSTEM.value, UserRoles.PUBLIC_USER.value, 'system', 'Registry Staff'),
        ('staff-public', UserRoles.STAFF.value, UserRoles.PUBLIC_USER.value, 'idir/staff-user', 'Registry Staff'),
        ('public-staff', UserRoles.PUBLIC_USER.value, UserRoles.STAFF.value, 'bcsc/public_user', 'bcsc/public_user'),
        ('public-public', UserRoles.PUBLIC_USER.value, UserRoles.PUBLIC_USER.value, 'bcsc/public_user', 'bcsc/public_user'),
        ('unknown-public', None, UserRoles.PUBLIC_USER.value, 'some-user', 'some-user'),
    ]
)
def test_ledger_redaction(session, client, jwt, test_name, submitter_role, jwt_role, username, expected):
    """Assert that the core filing is saved to the backing store."""
    from legal_api.core.filing import Filing as CoreFiling
    try:
        identifier = 'BC1234567'
        founding_date = datetime.utcnow()
        business_name = 'The Truffle House'
        entity_type = Business.LegalTypes.BCOMP.value

        business = factory_business(identifier=identifier, founding_date=founding_date, last_ar_date=None, entity_type=entity_type)
        business.legal_name = business_name
        business.save()

        filing_name = 'specialResolution'
        filing_date = founding_date
        filing_submission = {
            'filing': {
                'header': {
                    'name': filing_name,
                    'date': '2019-04-08'
                },
                filing_name: {
                    'resolution': 'Year challenge is hitting oppo for the win.'
                }}}
        user = factory_user(username)
        new_filing = factory_completed_filing(business, filing_submission, filing_date=filing_date)
        new_filing.submitter_id = user.id
        new_filing.submitter_roles = submitter_role
        setattr(new_filing, 'skip_status_listener', True)  # skip status listener
        new_filing.save()

        rv = client.get(f'/api/v2/businesses/{identifier}/filings',
                        headers=create_header(jwt, [jwt_role], identifier))
    except Exception as err:
        print(err)

    assert rv.status_code == HTTPStatus.OK
    assert rv.json['filings'][0]['submitter'] == expected
