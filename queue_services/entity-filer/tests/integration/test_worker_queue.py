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
import copy

import pytest

from .utils import helper_add_filing_to_queue, subscribe_to_queue


@pytest.mark.asyncio
async def test_cb_subscription_handler(app, session, stan_server, event_loop, client_id, entity_stan, future):
    """Assert that payment tokens can be retrieved and decoded from the Queue."""
    # Call back for the subscription
    from entity_filer.worker import cb_subscription_handler
    from legal_api.models import Business, Filing
    from registry_schemas.example_data import ANNUAL_REPORT
    from tests.unit import create_filing, create_business

    # vars
    identifier = 'CP1234567'

    # setup
    business = create_business(identifier)
    business_id = business.id
    filing = create_filing('test_pay_id', ANNUAL_REPORT, business.id)
    filing_id = filing.id

    # register the handler to test it
    entity_subject = await subscribe_to_queue(entity_stan, cb_subscription_handler)

    # add payment tokens to queue
    await helper_add_filing_to_queue(entity_stan, entity_subject, filing_id=filing_id)

    try:
        await asyncio.sleep(1)
        # await asyncio.wait_for(cb_future, 2, loop=event_loop)
    except Exception as err:
        print(err)

    # Get modified data
    business = Business.find_by_internal_id(business_id)
    filing = Filing.find_by_id(filing_id)

    # check it out
    assert filing.transaction_id
    assert filing.business_id == business_id
