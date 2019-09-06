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
"""Test Suite to ensure the worker routines are working as expected."""
import asyncio
import datetime
import random

import pytest

from .utils import helper_add_payment_to_queue, subscribe_to_queue


@pytest.mark.asyncio
async def test_cb_subscription_handler(app, session, stan_server, event_loop, client_id, entity_stan, future):
    """Assert that payment tokens can be retrieved and decoded from the Queue."""
    # Call back for the subscription
    from entity_filer.worker import cb_subscription_handler
    from entity_filer.worker import get_filing_by_payment_id
    from legal_api.models import Business
    from tests.unit import create_filing, AR_FILING, create_business

    # vars
    payment_id = str(random.SystemRandom().getrandbits(0x58))
    identifier = 'CP1234567'
    agm_date = datetime.date.fromisoformat(AR_FILING['filing']['annualReport'].get('annualGeneralMeetingDate'))
    ar_date = datetime.date.fromisoformat(AR_FILING['filing']['annualReport'].get('annualReportDate'))

    # setup
    business = create_business(identifier)
    business_id = business.id
    create_filing(payment_id, AR_FILING, business.id)

    # register the handler to test it
    entity_subject = await subscribe_to_queue(entity_stan, cb_subscription_handler)

    # add payment tokens to queue
    await helper_add_payment_to_queue(entity_stan, entity_subject, payment_id=payment_id, status_code='COMPLETED')

    try:
        await asyncio.sleep(1)
        # await asyncio.wait_for(cb_future, 2, loop=event_loop)
    except Exception as err:
        print(err)

    # Get modified data
    filing = get_filing_by_payment_id(payment_id)
    business = Business.find_by_internal_id(business_id)

    # check it out
    assert filing.transaction_id
    assert filing.business_id == business_id
    assert datetime.datetime.date(business.last_agm_date) == agm_date
    assert datetime.datetime.date(business.last_ar_date) == ar_date
