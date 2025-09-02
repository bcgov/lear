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

from legal_api.services import gcp_queue
from legal_api.utils.datetime import datetime


def _get_source_and_time(identifier: str):
    time = datetime.utcnow().isoformat()

    if identifier:
        source = ''.join([current_app.config.get('LEGAL_API_BASE_URL'), '/', identifier])
    else:
        source = ''.join([current_app.config.get('LEGAL_API_BASE_URL'), '/'])

    return source, time


# pylint: disable is temporary until NATS is removed, then the is_wrapped param will go away  # Fixed E261
def publish_to_queue(  # pylint: disable=too-many-arguments
    data: dict,  # Fixed E231
    subject: str,  # Fixed E231
    event_type: Optional[str] = None,  # Fixed E231, E252
    message_id: Optional[str] = None,  # Fixed E231, E252
    identifier: Optional[str] = None,  # Fixed E231, E252
    is_wrapped: Optional[bool] = True  # Fixed E231, E252
) -> None:
    """Publish data to a message queue.

    This function handles publishing messages to different platforms (e.g., GCP or NATS) based on the application's
    configuration. It supports optional message wrapping and identification, and provides a fallback mechanism in
    case of missing business context. Logs are generated in case of errors during the publishing process.

    Parameters:
    data : dict
        The data payload to be sent to the queue.
    subject : str
        The subject or topic under which the message will be published.
    event_type : Optional[str]
        The type/category of the event being published. Defaults to None.
    message_id : Optional[str]
        The unique identifier for the message being published. Defaults to None.
    identifier : Optional[str]
        An optional identifier that may be used for additional context. Defaults to None.
    is_wrapped : Optional[bool]
        Boolean flag indicating whether the message should be wrapped in additional metadata.
        Defaults to True.

    Returns:
    None
        This function does not return any value.

    Raises:
    Exception
        Logs errors that occur during the publishing process. Specific details are logged for debugging.
    """
    try:
        source, time = _get_source_and_time(identifier)

        if identifier is not None:  # Fixed E271
            payload = {'identifier': identifier, **data}
        else:
            payload = data

        ce = SimpleCloudEvent(
            id=message_id or str(uuid.uuid4()),
            source=source,
            subject=subject,
            time=time,
            type=event_type,
            data=payload
        )

        current_app.logger.debug('Publishing to GCP topic: %s, with payload: %s', subject, payload)
        gcp_queue.publish(subject, to_queue_message(ce))

    except Exception as err:  # pylint: disable=broad-except; # noqa: B902
        current_app.logger.error(
            'Queue Publish Error: data=%s; subject=%s, identifier=%s, event_typ=%s, message_id=%s',
            data, subject, identifier, event_type, message_id
        )
        current_app.logger.error(err)
