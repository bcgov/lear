# Copyright © 2026 Province of British Columbia
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
"""The Test Suites to ensure that the core process_filing wrapper is operating correctly."""
import pytest
import copy
from registry_schemas.example_data import ANNUAL_REPORT, REGISTRATION, FILING_HEADER

from business_filer.common.filing_message import FilingMessage
from business_filer.exceptions import DefaultError
from business_filer.services.filer import process_filing
from business_model.models import Filing
from tests.unit import create_business, create_filing


def test_process_filing_not_found(app, session):
    """Assert that a DefaultError is raised when filing is not found."""
    filing_msg = FilingMessage(filing_identifier=999999)
    with pytest.raises(DefaultError) as excinfo:
        process_filing(filing_msg)
    assert "filing not found for 999999" in excinfo.value.error_text


def test_process_filing_duplicate(app, session, mocker):
    """Assert that process_filing handles duplicate messages and the DB query succeeds without mocking."""
    # mock out the event publishing so we don't try to send emails
    mocker.patch('business_filer.services.publish_event.PublishEvent.publish_email_message', return_value=None)
    mocker.patch('business_filer.services.publish_event.PublishEvent.publish_event', return_value=None)

    business = create_business(identifier="CP1234567")
    filing = create_filing("payment123", ANNUAL_REPORT, business.id)
    filing_msg = FilingMessage(filing_identifier=filing.id)

    # First attempt: Processes successfully and commits (triggering DB updates)
    process_filing(filing_msg)

    # Verify status changed to completed in DB
    completed_filing = Filing.find_by_id(filing.id)
    assert completed_filing.status == Filing.Status.COMPLETED.value

    # Second attempt (Duplicate queue message):
    # This verifies that db.session.query(Filing).with_for_update() executes successfully against Postgres
    # and properly halts execution by returning None, None when status is COMPLETED.
    res1, res2 = process_filing(filing_msg)

    assert res1 is None
    assert res2 is None


def test_process_filing_locked(app, session, mocker):
    """Assert that process_filing propagates OperationalError when the row is locked by another transaction."""
    import time
    import concurrent
    from sqlalchemy.exc import OperationalError

    filing_json = copy.deepcopy(FILING_HEADER)
    filing_json['filing']['header']['name'] = 'registration'
    filing_json['filing']['registration'] = copy.deepcopy(REGISTRATION)
    filing_json['filing']['registration']['startDate'] = '2026-03-19'

    filing = create_filing('123', filing_json)
    filing_msg = FilingMessage(filing_identifier=filing.id)

    def mock_get_next_corp_num(legal_type):
        time.sleep(3) # simulate delay
        return "FM1234567"
        
    mocker.patch(
        'business_filer.filing_processors.filing_components.business_info.get_next_corp_num',
        side_effect=mock_get_next_corp_num
    )

    from business_filer.common.services import NaicsService
    naics_response = {
        'code': REGISTRATION['business']['naics']['naicsCode'],
        'naicsKey': 'a4667c26-d639-42fa-8af3-7ec73e392569'
    }
    mocker.patch.object(NaicsService, 'find_by_code', return_value=naics_response)

    mocker.patch('business_filer.filing_processors.filing_components.business_profile.update_business_profile', return_value=None)
    mocker.patch('business_filer.filing_processors.filing_components.business_profile.update_affiliation', return_value=None)


    def run_process():
        with app.app_context():
            try:
                process_filing(filing_msg)
                return "SUCCESS"
            except Exception as e:
                import traceback
                return traceback.format_exc()

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        f1 = executor.submit(run_process)
        f2 = executor.submit(run_process)

        res1 = f1.result()
        res2 = f2.result()

    assert res1 == "SUCCESS", f"Thread 1 failed with: {res1}"
    assert res2 == "SUCCESS", f"Thread 2 failed with: {res2}"
