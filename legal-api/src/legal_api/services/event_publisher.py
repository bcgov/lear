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
"""This module wraps the calls to external QUEUE services used by the API."""
from __future__ import annotations

import uuid
from typing import Optional

from flask import current_app

from simple_cloudevent import SimpleCloudEvent, to_queue_message

from legal_api.models import Business
from legal_api.services import queue, gcp_queue
from legal_api.utils.datetime import datetime


def _get_source_and_time(business: Business):
    source = ''.join([current_app.config.get('LEGAL_API_BASE_URL'), '/', business.identifier])
    time = datetime.utcnow().isoformat()

    return source, time


def _publish_to_nats_with_wrapper(data, subject, business, event_type, message_id):
    """Publish the wrapped message onto the NATS subject."""
    source, time = _get_source_and_time(business)
    payload = {
        'specversion': '1.x-wip',
        'type': event_type,
        'source': source,
        'id': message_id or str(uuid.uuid4()),
        'time': time,
        'datacontenttype': 'application/json',
        'identifier': business.identifier,
        'data': data
    }
    queue.publish(
        subject=subject,
        payload=payload
    )

def _publish_to_nats(payload, subject):
    """Publish the event message onto the NATS subject."""
    queue.publish(
        subject=subject,
        payload=payload
    )

def _publish_to_gcp(data, subject, business: Business, event_type:str):
    """Publish the event message onto the GCP topic."""
    source, time = _get_source_and_time(business)
    nats_to_gcp_topic = {
        current_app.config['NATS_FILER_SUBJECT']: current_app.config['BUSINESS_FILER_TOPIC'],
        current_app.config['NATS_ENTITY_EVENT_SUBJECT']: current_app.config['BUSINESS_EVENTS_TOPIC'],
        current_app.config['NATS_EMAILER_SUBJECT']: current_app.config['BUSINESS_EMAILER_TOPIC'],
    }

    topic = nats_to_gcp_topic[subject]

    ce = SimpleCloudEvent(id=str(uuid.uuid4()),
                                  source=source,
                                  subject=business.identifier,
                                  time=time,
                                  type=event_type,
                                  data={'identifier': business.identifier, **data}
                          )

    gcp_queue.publish(topic, to_queue_message(ce))

def publish_to_queue(
    data:dict,
    subject:str,
    business: Business, # todo: make this optional ... as some places will not have business ...
    event_type:str,
    message_id:Optional[str],
    is_wrapped:Optional[bool] = True
) -> None:
    """
    Publishes a payload to a message queue based on the configured deployment platform
    and optional wrapping conditions. Supports publishing to GCP or NATS.

    Arguments:
        data (dict): The payload data to be published to the message queue
        subject (str): The subject or topic associated with the message
            in case subject is unknown fallback to `current_app.config.get('NATS_FILER_SUBJECT')`
        business (Business): Business entity data used in the publishing process
        event_type (str): The event type associated with the publishing operation
        message_id (str): Optional. The message identifier to be used in the publishing process.
        is_wrapped (bool): Optional. Specifies if the payload should be wrapped before
            being published. Defaults to True

    Raises:
        Exception: If an error occurs during the publish operation, it is logged.
    """
    try:
        if current_app.config['DEPLOYMENT_PLATFORM'] == 'GCP':
            _publish_to_gcp(data=data, subject=subject, business=business, event_type=event_type)
        elif is_wrapped:
            _publish_to_nats_with_wrapper (
                data=data,
                subject=subject,
                business=business,
                event_type=event_type,
                message_id=message_id
            )
        else:
            _publish_to_nats(payload=data, subject=subject)

    except Exception as err:  # pylint: disable=broad-except; # noqa: B902
        current_app.logger.error('Queue Publish %s Error: business.id=%s', subject, business.id, exc_info=True)
