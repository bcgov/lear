# Copyright © 2025 Province of British Columbia
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
"""The Unit Tests for the Notice Of Withdrawal filing."""
import copy
import datetime
import random
import pytest
from unittest.mock import patch
from freezegun import freeze_time

from legal_api.models import Filing, Business
from legal_api.services import RegistrationBootstrapService
from registry_schemas.example_data import ALTERATION, FILING_HEADER, INCORPORATION, NOTICE_OF_WITHDRAWAL

from entity_filer.filing_meta import FilingMeta
from entity_filer.filing_processors import notice_of_withdrawal
from entity_filer.worker import process_filing, APP_CONFIG, get_filing_types, publish_event, qsm
from tests.unit import create_business, create_filing


@pytest.mark.parametrize('test_name,filing_type,filing_template,identifier', [
    ('IA Withdrawn Filing', 'incorporationApplication', INCORPORATION, 'TJO4XI2qMo'),
    ('alteration Withdrawn Filing', 'alteration', ALTERATION, 'BC1234567')
])
async def test_worker_notice_of_withdrawal(app, session, test_name, filing_type, filing_template, identifier):
    """Assert that the notice of withdrawal filing processes correctly."""
    import uuid
    from unittest.mock import AsyncMock
    from legal_api.utils.datetime import datetime as legal_datatime
    # Setup
    payment_id = str(random.SystemRandom().getrandbits(0x58))
    
    # Create withdrawn_filing
    withdrawn_filing_json = copy.deepcopy(FILING_HEADER)
    withdrawn_filing_json['filing']['business']['legalType'] = 'BC'
    withdrawn_filing_json['filing']['business']['identifier'] = identifier
    withdrawn_filing_json['filing'][filing_type] = copy.deepcopy(filing_template)
    if identifier.startswith('T'):
        business = RegistrationBootstrapService.create_bootstrap(account=28)
        withdrawn_filing = create_filing(token=payment_id, json_filing=withdrawn_filing_json, bootstrap_id=business.identifier)
    else:
        business = create_business(identifier, legal_type='BC')
        withdrawn_filing = create_filing(payment_id, withdrawn_filing_json, business_id=business.id)
    withdrawn_filing._filing_type = filing_type
    withdrawn_filing.payment_completion_date = datetime.datetime.utcnow()  # for setting the filing status PAID
    withdrawn_filing._meta_data = {}
    withdrawn_filing.save()

    # Create NoW filing
    now_filing_json = copy.deepcopy(FILING_HEADER)
    now_filing_json['filing']['business']['identifier'] = business.identifier
    now_filing_json['filing']['noticeOfWithdrawal'] = copy.deepcopy(NOTICE_OF_WITHDRAWAL)
    now_filing_json['filing']['noticeOfWithdrawal']['filingId'] = withdrawn_filing.id
    now_filing = create_filing(payment_id, now_filing_json)
    now_filing._filing_type = 'noticeOfWithdrawal'
    if not identifier.startswith('T'):
        now_filing.business_id = business.id
    now_filing.withdrawn_filing_id = withdrawn_filing.id
    now_filing.save()

    assert withdrawn_filing.status == Filing.Status.PAID.value

    # Test
    filing_msg = {'filing': {'id': now_filing.id}}
    await process_filing(filing_msg, app)
    business.save()

    # Check NoW filing process results
    final_withdrawn_filing = Filing.find_by_id(withdrawn_filing.id)
    final_now_filing = Filing.find_by_id(now_filing.id)

    assert now_filing_json['filing']['noticeOfWithdrawal']['courtOrder']['orderDetails'] == final_now_filing.order_details
    assert final_withdrawn_filing.status == Filing.Status.WITHDRAWN.value
    assert final_withdrawn_filing.withdrawal_pending == False
    assert final_withdrawn_filing.meta_data.get('withdrawnDate')
    
    # Test the publish_event
    mock_publish = AsyncMock()
    qsm.service = mock_publish
    with freeze_time(legal_datatime.utcnow()), \
            patch.object(uuid, 'uuid4', return_value=1):

        final_business = Business.find_by_internal_id(final_now_filing.business_id)
        await publish_event(final_business, final_now_filing)
        payload = {
            'specversion': '1.x-wip',
            'type': 'bc.registry.business.' + final_now_filing.filing_type,
            'source': ''.join(
                [APP_CONFIG.LEGAL_API_URL,
                 '/business/',
                 business.identifier,
                 '/filing/',
                 str(final_now_filing.id)]),
            'id': str(uuid.uuid4()),
            'time': legal_datatime.utcnow().isoformat(),
            'datacontenttype': 'application/json',
            'identifier': business.identifier,
            'data': {
                'filing': {
                    'header': {'filingId': final_now_filing.id,
                               'effectiveDate': final_now_filing.effective_date.isoformat()
                               },
                    'business': {'identifier': business.identifier},
                    'legalFilings': get_filing_types(final_now_filing.filing_json)
                }
            }
        }

        if identifier.startswith('T'):
            payload['tempidentifier'] = business.identifier

        mock_publish.publish.assert_called_with('entity.events', payload)
