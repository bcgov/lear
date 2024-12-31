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

"""Tests to assure the business-tasks end-point.

Test-Suite to ensure that the /tasks endpoint is working as expected.
"""
import copy
from datetime import datetime
from http import HTTPStatus
from unittest.mock import patch

import datedelta
import pytest
from freezegun import freeze_time
from registry_schemas.example_data import ANNUAL_REPORT

from legal_api.models import Business
from legal_api.services.authz import STAFF_ROLE
from tests import integration_payment
from tests.unit.models import factory_business, factory_business_mailing_address, factory_filing, factory_pending_filing
from tests.unit.services.utils import create_header
from tests.unit.services.warnings import create_business


AR_FILING_CURRENT_YEAR = {
    'filing': {
        'header': {
            'name': 'annualReport',
            'date': '2019-08-13',
            'certifiedBy': 'full name'
        },
        'business': {
            'cacheId': 1,
            'foundingDate': '2007-04-08',
            'identifier': 'CP1234567',
            'legalName': 'legal name - CP1234567'
        },
        'annualReport': {
            'annualGeneralMeetingDate': str(datetime.today()).split()[0],
            'annualReportDate': str(datetime.today()).split()[0],
            'certifiedBy': 'full name',
            'email': 'no_one@never.get'
        }
    }
}

AR_FILING_PREVIOUS_YEAR = {
    'filing': {
        'header': {
            'name': 'annualReport',
            'date': '2001-08-05',
            'certifiedBy': 'full name',
            'email': 'no_one@never.get'
        },
        'business': {
            'cacheId': 1,
            'foundingDate': '2007-04-08T00:00:00+00:00',
            'identifier': 'CP1234567',
            'legalName': 'legal name - CP1234567',
            'lastPreBobFilingTimestamp': '2019-01-01T20:05:49.068272+00:00'
        },
        'annualReport': {
            'annualGeneralMeetingDate': str(datetime.today() - datedelta.datedelta(years=1)).split()[0],
            'annualReportDate': str(datetime.today() - datedelta.datedelta(years=1)).split()[0],
            'certifiedBy': 'full name',
            'email': 'no_one@never.get'
        }
    }
}


def test_get_tasks_no_filings(session, client, jwt):
    """Assert that to-do for the year after incorporation is returned when there are no filings."""
    identifier = 'CP7654321'
    factory_business(identifier, founding_date=datetime(2017, 2, 1))  # incorporation in 2017

    # To-do are all years from the year after incorporation until this year
    this_year = datetime.now().year
    num_filings_owed = this_year - 2017

    rv = client.get(f'/api/v2/businesses/{identifier}/tasks', headers=create_header(jwt, [STAFF_ROLE], identifier))
    assert rv.status_code == HTTPStatus.OK
    assert num_filings_owed == len(rv.json.get('tasks'))


def test_get_tasks_next_year(session, client, jwt):
    """Assert that one todo item is returned in the calendar year following incorporation."""
    identifier = 'CP7654321'
    founding_date = datetime.today() - datedelta.datedelta(years=1)
    factory_business(identifier, founding_date=founding_date)  # incorporation 1 year

    # To-do are all years from the year after incorporation until this year

    rv = client.get(f'/api/v2/businesses/{identifier}/tasks', headers=create_header(jwt, [STAFF_ROLE], identifier))
    assert rv.status_code == HTTPStatus.OK
    assert 1 == len(rv.json.get('tasks'))


def test_bcorps_get_tasks_no_filings(session, client, jwt):
    """Assert that to-do for the current year is returned when there are no filings."""
    identifier = 'CP7654321'
    factory_business(identifier, datetime.now(), None, Business.LegalTypes.BCOMP.value)

    rv = client.get(f'/api/v2/businesses/{identifier}/tasks', headers=create_header(jwt, [STAFF_ROLE], identifier))

    assert rv.status_code == HTTPStatus.OK
    assert len(rv.json.get('tasks')) == 0  # To-do for the current year


@integration_payment
def test_bcorps_get_tasks_pending_filings(session, client, jwt):
    """Assert the correct number of todo items are returned when there is an AR filing pending."""
    identifier = 'CP7654321'
    business = factory_business(
        identifier, datetime.today() - datedelta.datedelta(years=3), None, Business.LegalTypes.BCOMP.value)
    factory_business_mailing_address(business)
    rv = client.get(
        f'/api/v2/businesses/{identifier}/tasks',
        headers=create_header(jwt, [STAFF_ROLE], identifier)
    )

    assert rv.status_code == HTTPStatus.OK
    assert len(rv.json.get('tasks')) == 3  # To-do for the current year
    assert rv.json['tasks'][0]['task']['todo']['header']['status'] == 'NEW'

    filing = copy.deepcopy(ANNUAL_REPORT)
    rv = client.post(f'/api/v2/businesses/{identifier}/filings',
                     json=filing,
                     headers=create_header(jwt, [STAFF_ROLE], identifier)
                     )
    assert rv.status_code >= 400
    assert rv.status_code < 500

    filing['filing']['annualReport']['annualReportDate'] = str((datetime.today() - datedelta.datedelta(years=2)).date())
    filing['filing']['business']['legalType'] = Business.LegalTypes.BCOMP.value
    rv = client.post(f'/api/v2/businesses/{identifier}/filings',
                     json=filing,
                     headers=create_header(jwt, [STAFF_ROLE], identifier)
                     )

    assert rv.status_code == HTTPStatus.CREATED

    rv = client.get(f'/api/v2/businesses/{identifier}/tasks', headers=create_header(jwt, [STAFF_ROLE], identifier))
    assert len(rv.json.get('tasks')) == 3
    assert rv.json['tasks'][0]['task']['filing']['header']['status'] == 'PENDING'


def test_get_tasks_current_year_filing_exists(session, client, jwt):
    """Assert that only the filing for the current year is returned when only current year filing exists."""
    identifier = 'CP7654321'
    b = factory_business(identifier=identifier, last_ar_date=datetime(2018, 8, 13))
    filings = factory_filing(b, AR_FILING_CURRENT_YEAR, datetime(2019, 8, 5, 7, 7, 58, 272362), 'annualReport')

    print('test_get_all_business_filings - filing:', filings)

    rv = client.get(f'/api/v2/businesses/{identifier}/tasks', headers=create_header(jwt, [STAFF_ROLE], identifier))

    assert rv.status_code == HTTPStatus.OK
    # assert len(rv.json.get('tasks')) == 1  # Current year incomplete filing only


def test_get_tasks_prev_year_incomplete_filing_exists(session, client, jwt):
    """Assert that the one incomplete filing for previous year and a to-do for current year are returned."""
    identifier = 'CP7654321'
    b = factory_business(identifier, last_ar_date=datetime(2018, 3, 3))
    filings = factory_filing(b, AR_FILING_PREVIOUS_YEAR, datetime(2018, 8, 5, 7, 7, 58, 272362))

    print('test_get_all_business_filings - filing:', filings)

    rv = client.get(f'/api/v2/businesses/{identifier}/tasks', headers=create_header(jwt, [STAFF_ROLE], identifier))

    assert rv.status_code == HTTPStatus.OK
    # assert len(rv.json.get('tasks')) == 2  # Previous year filing and a disabled to-do for current year.


def test_bcorp_get_tasks_prev_year_incomplete_filing_exists(session, client, jwt):
    """Assert that the one incomplete filing for previous year and a to-do for current year are returned."""
    identifier = 'CP7654321'
    b = factory_business(identifier, datetime.now() - datedelta.datedelta(years=2), last_ar_date=datetime(2018, 3, 3))
    filings = factory_filing(b, AR_FILING_PREVIOUS_YEAR, datetime(2018, 8, 5, 7, 7, 58, 272362))
    print('test_get_all_business_filings - filing:', filings)

    rv = client.get(f'/api/v2/businesses/{identifier}/tasks', headers=create_header(jwt, [STAFF_ROLE], identifier))

    assert rv.status_code == HTTPStatus.OK
    # assert len(rv.json.get('tasks')) == 2  # Previous year filing and a disabled to-do for current year.


def test_get_empty_tasks_with_invalid_business(session, client, jwt):
    """Assert that an empty filings array is returned when business does not exist."""
    identifier = 'CP7654321'

    rv = client.get(f'/api/v2/businesses/{identifier}/tasks', headers=create_header(jwt, [STAFF_ROLE], identifier))

    assert rv.status_code == HTTPStatus.OK
    print('rv json', rv.json)
    assert rv.json == {'tasks': []}


def test_get_tasks_error_filings(session, client, jwt):
    """Assert that to-do list returns the error filings."""
    from legal_api.models import Filing
    from tests.unit.models import AR_FILING, factory_business_mailing_address
    # setup
    identifier = 'CP7654321'
    b = factory_business(identifier, last_ar_date=datetime(2019, 8, 13))
    factory_business_mailing_address(b)
    filing = factory_pending_filing(b, AR_FILING, datetime(2019, 8, 5, 7, 7, 58, 272362))
    filing.save()
    assert filing.status == Filing.Status.PENDING.value

    # test endpoint returned filing in tasks call
    rv = client.get(f'/api/v2/businesses/{identifier}/tasks', headers=create_header(jwt, [STAFF_ROLE], identifier))
    assert rv.status_code == HTTPStatus.OK
    # assert len(rv.json['tasks']) == 3
    assert rv.json['tasks'][0]['task']['filing']['header']['filingId'] == filing.id


def test_get_tasks_pending_correction_filings(session, client, jwt):
    """Assert that to-do list returns the error filings."""
    from freezegun import freeze_time
    from legal_api.models import Filing
    from tests import FROZEN_2018_DATETIME
    from registry_schemas.example_data import CORRECTION_AR
    # setup
    identifier = 'CP7654321'
    b = factory_business(identifier, last_ar_date=datetime(2016, 8, 13))
    filing = factory_pending_filing(b, CORRECTION_AR)
    filing.save()
    filing._status = Filing.Status.PENDING_CORRECTION.value
    setattr(filing, 'skip_status_listener', True)
    filing.save()
    assert filing.status == Filing.Status.PENDING_CORRECTION.value

    # freeze time so we get the same number of tasks in the to-do list regardless of when this test is run
    with freeze_time(FROZEN_2018_DATETIME):
        # test endpoint returned filing in tasks call
        rv = client.get(f'/api/v2/businesses/{identifier}/tasks', headers=create_header(jwt, [STAFF_ROLE], identifier))
        assert rv.status_code == HTTPStatus.OK
        assert len(rv.json['tasks']) == 3
        assert rv.json['tasks'][0]['task']['filing']['header']['filingId'] == filing.id


@freeze_time('Jul 2nd, 2022')
@pytest.mark.parametrize('test_name, identifier, founding_date, previous_ar_date, legal_type, tasks_length', [
    ('BEN first AR to be issued', 'BC1234567', '2021-07-02', None, Business.LegalTypes.BCOMP.value, 1),
    ('BEN no AR due yet', 'BC1234567', '2021-07-03', None, Business.LegalTypes.BCOMP.value, 0),
    ('BEN 3 ARs overdue', 'BC1234567', '2019-05-15', None, Business.LegalTypes.BCOMP.value, 3),
    ('BEN current AR year issued', 'BC1234567', '1900-07-01', '2022-03-03', Business.LegalTypes.BCOMP.value, 0),

    ('BC first AR to be issued', 'BC1234567', '2021-07-02', None, Business.LegalTypes.COMP.value, 1),
    ('BC no AR due yet', 'BC1234567', '2021-07-03', None, Business.LegalTypes.COMP.value, 0),
    ('BC 3 ARs overdue', 'BC1234567', '2019-05-15', None, Business.LegalTypes.COMP.value, 3),
    ('BC current AR year issued', 'BC1234567', '1900-07-01', '2022-03-03', Business.LegalTypes.COMP.value, 0),

    ('ULC first AR to be issued', 'BC1234567', '2021-07-02', None, Business.LegalTypes.BC_ULC_COMPANY.value, 1),
    ('ULC no AR due yet', 'BC1234567', '2021-07-03', None, Business.LegalTypes.BC_ULC_COMPANY.value, 0),
    ('ULC 3 ARs overdue', 'BC1234567', '2019-05-15', None, Business.LegalTypes.BC_ULC_COMPANY.value, 3),
    ('ULC current AR year issued', 'BC1234567', '1900-07-01', '2022-03-03',
     Business.LegalTypes.BC_ULC_COMPANY.value, 0),

    ('CC first AR to be issued', 'BC1234567', '2021-07-02', None, Business.LegalTypes.BC_CCC.value, 1),
    ('CC no AR due yet', 'BC1234567', '2021-07-03', None, Business.LegalTypes.BC_CCC.value, 0),
    ('CC 3 ARs overdue', 'BC1234567', '2019-05-15', None, Business.LegalTypes.BC_CCC.value, 3),
    ('CC current AR year issued', 'BC1234567', '1900-07-01', '2022-03-03', Business.LegalTypes.BC_CCC.value, 0),

    ('CP founded in the end of the year', 'CP1234567', '2021-12-31', None, Business.LegalTypes.COOP.value, 1),
    ('CP current year AR pending', 'CP1234567', '1900-07-01', '2021-03-03', Business.LegalTypes.COOP.value, 1),
    ('CP 3 ARs overdue', 'CP1234567', '2019-05-15', None, Business.LegalTypes.COOP.value, 3),

    ('SP no AR', 'FM1234567', '2019-05-15', None, Business.LegalTypes.SOLE_PROP.value, 0),
    ('GP no AR', 'FM1234567', '2019-05-15', None, Business.LegalTypes.PARTNERSHIP.value, 0)
])
def test_construct_task_list(session, client, jwt, test_name, identifier, founding_date, previous_ar_date, legal_type,
                             tasks_length):
    """Assert that construct_task_list returns the correct number of AR to be filed."""
    from legal_api.resources.v2.business.business_tasks import construct_task_list
    with patch('legal_api.resources.v2.business.business_tasks.check_warnings', return_value=[]):
        previous_ar_datetime = datetime.fromisoformat(previous_ar_date) if previous_ar_date else None
        business = factory_business(
            identifier, founding_date, previous_ar_datetime, legal_type)
        tasks = construct_task_list(business)
        assert len(tasks) == tasks_length

        # nextAnnualReport should be in UTC and have the time should have the offset: 7 or 8 hours late
        if tasks_length:
            assert tasks[0]['task']['todo']['business']['nextAnnualReport'][-14:] != '00:00:00+00:00'


@pytest.mark.parametrize('test_name, legal_type, identifier, has_missing_business_info, conversion_task_expected', [
    ('CONVERSION_TODO_EXISTS_MISSING_DATA', 'SP', 'FM0000001', True, True),
    ('CONVERSION_TODO_EXISTS_MISSING_DATA', 'GP', 'FM0000002', True, True),
    ('NO_CONVERSION_TODO_NO_MISSING_DATA', 'SP', 'FM0000003', False, False),
    ('NO_CONVERSION_TODO_NO_MISSING_DATA', 'GP', 'FM0000004', False, False),
    ('NO_CONVERSION_TODO_NON_FIRM', 'CP', 'CP7654321', True, False),
    ('NO_CONVERSION_TODO_NON_FIRM', 'BEN', 'CP7654321', True, False),
    ('NO_CONVERSION_TODO_NON_FIRM', 'BC', 'BC7654321', True, False),
    ('NO_CONVERSION_TODO_NON_FIRM', 'ULC', 'BC7654321', True, False),
    ('NO_CONVERSION_TODO_NON_FIRM', 'CC', 'BC7654321', True, False),
])
def test_conversion_filing_task(session, client, jwt, test_name, legal_type, identifier, has_missing_business_info,
                                conversion_task_expected):
    """Assert conversion todo shows up for only SP/GPs with missing business info."""
    if has_missing_business_info:
        factory_business(entity_type=legal_type, identifier=identifier)
    else:
        create_business(legal_type=legal_type,
                        identifier=identifier,
                        create_office=True,
                        create_office_mailing_address=True,
                        create_office_delivery_address=True,
                        firm_num_persons_roles=2,
                        create_firm_party_address=True,
                        filing_types=['registration'],
                        filing_has_completing_party=[True],
                        create_completing_party_address=[True],
                        start_date=datetime.utcnow())

    rv = client.get(f'/api/v2/businesses/{identifier}/tasks', headers=create_header(jwt, [STAFF_ROLE], identifier))

    assert rv.status_code == HTTPStatus.OK
    rv_json = rv.json

    if conversion_task_expected:
        conversion_to_do = any(x['task']['todo']['header']['name'] == 'conversion'
                               and x['task']['todo']['header']['status'] == 'NEW'
                               for x in rv_json['tasks'])
        assert conversion_to_do
    else:
        conversion_to_do = any(x['task']['todo']['header']['name'] == 'conversion'
                               and x['task']['todo']['header']['status'] == 'NEW'
                               for x in rv_json['tasks'])
        assert not conversion_to_do
