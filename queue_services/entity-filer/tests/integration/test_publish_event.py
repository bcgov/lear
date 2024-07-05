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
"""Test Suite to ensure event publishing is working as expected."""
import asyncio
import json
from datetime import datetime
from datetime import timezone
from queue import Queue

import pytest
# import pytest_asyncio
from registry_schemas.example_data import ANNUAL_REPORT
from testcontainers.google import PubSubContainer
from testcontainers.core.waiting_utils import wait_for_logs


@pytest.mark.skip
def test_publish_gcp_queue_event(app, session):
    """Assert that filing event is placed on the queue."""
    # Call back for the subscription
    from entity_filer.worker import APP_CONFIG, publish_gcp_queue_event, gcp_queue
    from legal_api.models import Business, Filing

    # Setup
    gcp_queue.init_app(app)

    event_handler_subject = APP_CONFIG.BUSINESS_EVENTS_TOPIC

    filing = Filing()
    filing.id = 101
    filing.effective_date = datetime.now(timezone.utc)
    filing.filing_json = ANNUAL_REPORT
    business = Business()
    business.identifier = 'CP1234567'
    business.legal_name = 'CP1234567 - Legal Name'

    with PubSubContainer() as pubsub:
        wait_for_logs(pubsub, r"Server started, listening on \d+", timeout=10)

        # Create a new topic
        publisher = pubsub.get_publisher_client()
        # topic_path = publisher.topic_path(pubsub.project, "my-topic")
        # publisher.create_topic(name=topic_path)
        # topic_path = publisher.topic_path(pubsub.project, "my-topic")
        publisher.create_topic(name=event_handler_subject)

        # Create a subscription
        subscriber = pubsub.get_subscriber_client()
        subscription_path = subscriber.subscription_path(
            pubsub.project, "my-subscription"
        )
        subscriber.create_subscription(
            request={"name": subscription_path, "topic": event_handler_subject}
        )

        gcp_queue._publisher = publisher

        # Test
        publish_gcp_queue_event(business, filing)

        # Receive the message
        queue = Queue()
        subscriber.subscribe(subscription_path, queue.put)
        message = queue.get(timeout=1)
        message.ack()
        assert message.data
        event_data = json.loads(message.data.decode())
        assert event_data['data']['filing']['header']['filingId'] == 101
        assert event_data['data']['filing']['business']['identifier'] == 'CP1234567'
        assert event_data['data']['filing']['legalFilings'] == ['annualReport']


# @pytest_asyncio.fixture(scope="session")
@pytest.mark.asyncio
async def test_publish_nats_event(app, session, stan_server, event_loop, client_id, entity_stan, future):
    """Assert that filing event is placed on the queue."""
    # Call back for the subscription
    from entity_queue_common.service import ServiceWorker
    from entity_filer.worker import APP_CONFIG, publish_event, qsm
    from legal_api.models import Business, Filing

    # file handler callback
    msgs = []

    async def cb_file_handler(msg):
        nonlocal msgs
        nonlocal future
        msgs.append(msg)
        if len(msgs) == 1:
            future.set_result(True)

    event_handler_subject = APP_CONFIG.ENTITY_EVENT_PUBLISH_OPTIONS['subject']

    await entity_stan.subscribe(subject=event_handler_subject,
                                queue=f'entity_queue.{event_handler_subject}',
                                durable_name=f'entity_durable_name.{event_handler_subject}',
                                cb=cb_file_handler)

    s = ServiceWorker()
    s.sc = entity_stan
    qsm.service = s

    # Setup
    filing = Filing()
    filing.id = 101
    filing.effective_date = datetime.utcnow().replace(tzinfo=timezone.utc)
    filing.filing_json = ANNUAL_REPORT
    business = Business()
    business.identifier = 'CP1234567'
    business.legal_name = 'CP1234567 - Legal Name'

    # Test
    await publish_event(business, filing)

    try:
        await asyncio.wait_for(future, 2, loop=event_loop)
    except Exception as err:
        print(err)

    # check it out
    assert len(msgs) == 1

    event_msg = json.loads(msgs[0].data.decode('utf-8'))
    assert event_msg['data']['filing']['header']['filingId'] == 101
    assert event_msg['identifier'] == 'CP1234567'
    assert event_msg['data']['filing']['legalFilings'] == ['annualReport']
