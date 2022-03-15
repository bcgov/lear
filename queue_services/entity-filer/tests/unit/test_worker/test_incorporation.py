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
"""The Test Suites to ensure that the worker is operating correctly."""
import asyncio
import copy
import datetime
import random

import pytest
from entity_queue_common.messages import get_data_from_msg
from entity_queue_common.service_utils import subscribe_to_queue
from legal_api.models import Business, Filing, PartyRole
from legal_api.services import RegistrationBootstrapService
from registry_schemas.example_data import INCORPORATION_FILING_TEMPLATE

from entity_filer.worker import process_filing
from tests.pytest_marks import colin_api_integration, integration_affiliation, integration_namex_api
from tests.unit import create_filing


@pytest.fixture(scope='function')
def bootstrap(account):
    """Create a IA filing for processing."""
    from legal_api.services.bootstrap import AccountService

    bootstrap = RegistrationBootstrapService.create_bootstrap(account=account)
    RegistrationBootstrapService.register_bootstrap(bootstrap, bootstrap.identifier)
    identifier = bootstrap.identifier

    yield identifier

    try:
        rv = AccountService.delete_affiliation(account, identifier)
        print(rv)
    except Exception as err:
        print(err)


@colin_api_integration
@integration_affiliation
@integration_namex_api
async def test_incorporation_filing(app, session, bootstrap):
    """Assert we can retrieve a new corp number from COLIN and incorporate a business."""
    filing = copy.deepcopy(INCORPORATION_FILING_TEMPLATE)
    filing['filing']['incorporationApplication']['nameRequest']['nrNumber'] = 'NR 0000021'
    payment_id = str(random.SystemRandom().getrandbits(0x58))
    filing_id = (create_filing(payment_id, filing, bootstrap_id=bootstrap)).id

    filing_msg = {'filing': {'id': filing_id}}

    # Test
    await process_filing(filing_msg, app)

    # Check outcome
    filing = Filing.find_by_id(filing_id)
    business = Business.find_by_internal_id(filing.business_id)

    filing_json = filing.filing_json
    assert business
    assert filing
    assert filing.status == Filing.Status.COMPLETED.value
    assert business.identifier == filing_json['filing']['business']['identifier']
    assert business.founding_date.isoformat() == filing_json['filing']['business']['foundingDate']
    assert len(business.share_classes.all()) == len(filing_json['filing']['incorporationApplication']['shareClasses'])
    assert len(business.offices.all()) == len(filing_json['filing']['incorporationApplication']['offices'])

    assert len(PartyRole.get_parties_by_role(business.id, 'director')) == 1
    assert len(PartyRole.get_parties_by_role(business.id, 'incorporator')) == 1
    assert len(PartyRole.get_parties_by_role(business.id, 'completing_party')) == 1
    incorporator = (PartyRole.get_parties_by_role(business.id, 'incorporator'))[0]
    completing_party = (PartyRole.get_parties_by_role(business.id, 'completing_party'))[0]
    assert incorporator.appointment_date
    assert completing_party.appointment_date


def test_update_affiliation_error(mocker):
    """Assert that a message is posted to sentry if an error occurs."""
    import sentry_sdk
    from entity_filer.filing_processors import incorporation_filing
    filing = Filing(id=1)
    mocker.patch('sentry_sdk.capture_message')
    incorporation_filing.update_affiliation(None, filing)

    sentry_sdk.capture_message.assert_called_once_with(
        f"Queue Error: Affiliation error for filing:{filing.id}, with err:'NoneType' object has no attribute 'account'",
        level='error'
    )

@pytest.mark.skip("AttributeError: can't set attribute")
@pytest.mark.asyncio
async def test_publish_email_message(app, session, stan_server, event_loop, client_id, entity_stan, future):
    """Assert that payment tokens can be retrieved and decoded from the Queue."""
    # Call back for the subscription
    from entity_queue_common.service import ServiceWorker
    from entity_filer.worker import APP_CONFIG, publish_email_message, qsm
    from legal_api.models import Filing

    # file handler callback
    msgs = []

    async def cb_file_handler(msg):
        nonlocal msgs
        nonlocal future
        msgs.append(msg)
        if len(msgs) == 1:
            future.set_result(True)

    file_handler_subject = APP_CONFIG.EMAIL_PUBLISH_OPTIONS['subject']
    await subscribe_to_queue(entity_stan,
                             file_handler_subject,
                             f'entity_queue.{file_handler_subject}',
                             f'entity_durable_name.{file_handler_subject}',
                             cb_file_handler)

    s = ServiceWorker()
    s.sc = entity_stan
    qsm.service = s

    # Test
    filing = Filing()
    filing.id = 101
    filing._filing_type = 'incorporationApplication'
    filing_date = datetime.datetime.utcnow()
    filing._filing_date = filing_date
    filing.effective_date = filing_date

    await publish_email_message(qsm, APP_CONFIG.EMAIL_PUBLISH_OPTIONS['subject'], filing, 'registered')

    try:
        await asyncio.wait_for(future, 2, loop=event_loop)
    except Exception as err:
        print(err)

    # check it out
    assert len(msgs) == 1
    assert get_data_from_msg(msgs[0], 'id') == filing.id
    assert get_data_from_msg(msgs[0], 'type') == filing.filing_type
    assert get_data_from_msg(msgs[0], 'option') == 'registered'

    await publish_email_message(qsm, APP_CONFIG.EMAIL_PUBLISH_OPTIONS['subject'], filing, 'mras')

    try:
        await asyncio.wait_for(future, 2, loop=event_loop)
    except Exception as err:
        print(err)

    # check it out
    assert len(msgs) == 1
    assert get_data_from_msg(msgs[0], 'id') == filing.id
    assert get_data_from_msg(msgs[0], 'type') == filing.filing_type
    assert get_data_from_msg(msgs[0], 'option') == 'mras'
