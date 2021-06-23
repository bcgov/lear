# Copyright © 2019 Province of British Columbia
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Functionality for tracking processing of messages in queue."""

import json

import nats

from entity_emailer.email_processors import filing_notification
from tracker.models import MessageProcessing
from tracker.services import MessageProcessingService


def get_key_message_properties(queue_msg: nats.aio.client.Msg):  # pylint: disable=too-many-return-statements
    """Get key message properties from a queue message."""
    # todo update this code to just use the cloud event message id when all
    #  publishers are publishing to emailer queue with cloud event format
    raw_message_id = queue_msg.sequence
    email_msg = json.loads(queue_msg.data.decode('utf-8'))
    etype = email_msg.get('type', None)

    message_properties = {
        'type': None,
        'message_id': None,
        'identifier': None,
        'trackable': False
    }

    if etype:
        message_id = email_msg.get('id', None)
        if etype == 'bc.registry.names.request':
            identifier = email_msg.get('identifier', None)
            return create_message_properties(etype, message_id, identifier)

        if etype == 'bc.registry.affiliation':
            identifier = email_msg.get('filing', {})\
                                    .get('business', {})\
                                    .get('identifier', None)
            return create_message_properties(etype, raw_message_id, identifier)
    else:
        email = email_msg.get('email', None)
        etype = email_msg.get('email', {}).get('type', None)
        if not email or not etype:
            return message_properties

        if etype == 'businessNumber':
            identifier = email_msg.get('identifier', None)
            return create_message_properties(etype, raw_message_id, identifier)

        if etype == 'incorporationApplication':
            return create_message_properties(etype, raw_message_id, None)

        if etype in filing_notification.FILING_TYPE_CONVERTER.keys():
            identifier = email.get('filing', {})\
                                .get('business', {})\
                                .get('identifier', None)
            return create_message_properties(etype, raw_message_id, identifier)

    return message_properties


def create_message_properties(message_type, message_id, identifier) -> dict:
    """Create message properties dict from input param values."""
    return {
        'type': message_type,
        'message_id': message_id,
        'identifier': identifier
    }


def is_processable_message(message_id):
    """Determine if message needs to be processed by message_id."""
    msg: MessageProcessing = \
        MessageProcessingService.find_message_by_message_id(message_id)

    if message_id is None:
        return False, None

    if msg is None or msg.status == MessageProcessing.Status.FAILED.value:
        return True, msg

    return False, msg


def start_tracking_message(message_properties: dict, email_msg: dict, existing_tracker_msg: MessageProcessing):
    """Create a new message with PROCESSING status or update an existing message to PROCESSING status."""
    if existing_tracker_msg:
        return update_message_status_to_processing(existing_tracker_msg)

    return create_processing_message(message_properties, email_msg)


def complete_tracking_message(tracker_msg: MessageProcessing):
    """Update existing message state to COMPLETED."""
    update_message_status_to_complete(tracker_msg)


def mark_tracking_message_as_failed(message_id: str,
                                    email_msg: dict,
                                    existing_tracker_msg: MessageProcessing,
                                    error_details: str):
    """Create a new message with FAILED status or update an existing message to FAILED status."""
    if existing_tracker_msg \
            and existing_tracker_msg.status == MessageProcessing.Status.PROCESSING.value:
        return update_message_status_to_failed(existing_tracker_msg, error_details)

    if existing_tracker_msg \
            and existing_tracker_msg.status == MessageProcessing.Status.FAILED.value:
        return update_failed_message(existing_tracker_msg, error_details)

    return create_failed_message(message_id, email_msg, error_details)


def create_message(message_properties: dict,
                   msg: str,
                   status: MessageProcessing.Status,
                   error_details: None):
    """Create MessageProcessing record."""
    message_id = message_properties.get('message_id')
    identifier = message_properties.get('identifier')
    message_type = message_properties.get('type')
    new_status = status
    message_json = msg

    result = MessageProcessingService.create_message(
        message_id=message_id,
        identifier=identifier,
        message_type=message_type,
        status=new_status,
        message_json=message_json,
        last_error=error_details,
        seen_count=1
    )
    return result


def create_processing_message(message_id: str, msg: str):
    """Create message with status of PROCESSING."""
    return create_message(message_id, msg, MessageProcessing.Status.PROCESSING, None)


def create_failed_message(message_id: str, msg: str, error_details: str):
    """Create message with status of FAILED."""
    return create_message(message_id, msg, MessageProcessing.Status.FAILED, error_details)


def update_message_status_to_processing(msg: MessageProcessing):
    """Update existing message status to PROCESSING."""
    return MessageProcessingService.update_message_status(msg, MessageProcessing.Status.PROCESSING, None, True)


def update_message_status_to_complete(tracker_msg: MessageProcessing):
    """Update existing message status to COMPLETE."""
    MessageProcessingService.update_message_status(tracker_msg, MessageProcessing.Status.COMPLETE, None, False)


def update_message_status_to_failed(msg: MessageProcessing, error_details: str):
    """Update existing message status to FAILED."""
    return MessageProcessingService.update_message_status(msg, MessageProcessing.Status.FAILED, error_details, False)


def update_failed_message(msg: MessageProcessing, error_details: str):
    """Update error message for existing failed message."""
    return MessageProcessingService.update_message_last_error(msg, error_details, False)
