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
from flask import current_app

from entity_emailer.email_processors import filing_notification, involuntary_dissolution_stage_1_notification
from tracker.models import MessageProcessing
from tracker.services import MessageProcessingService


def get_message_context_properties(queue_msg: nats.aio.client.Msg):
    # pylint: disable=too-many-return-statements, too-many-branches
    """Get key message properties from a queue message."""
    # todo update this code to just use the cloud event message id when all
    #  publishers are publishing to emailer queue with cloud event format
    email_msg = json.loads(queue_msg.data.decode('utf-8'))
    etype = email_msg.get('type', None)

    message_context_properties = {
        'type': None,
        'source': None,
        'message_id': None,
        'identifier': None,
        'is_cloud_event_format': False
    }

    if etype:
        message_id = email_msg.get('id', None)
        if etype == 'bc.registry.names.request':
            source = email_msg.get('source', None)
            identifier = email_msg.get('identifier', None)
            return create_message_context_properties(etype, message_id, source, identifier, True)

        if etype == 'bc.registry.bnmove' \
            and (new_bn := email_msg.get('data', {})
                 .get('newBn', None)):
            identifier = email_msg.get('identifier', None)
            message_id = f'{etype}_{new_bn}'
            return create_message_context_properties(etype, message_id, None, identifier, False)

        if etype == 'bc.registry.affiliation' \
            and (filing_id := email_msg.get('data', {})
                 .get('filing', {})
                 .get('header', {})
                 .get('filingId', None)):
            identifier = email_msg.get('identifier', None)
            message_id = f'{etype}_{filing_id}'
            return create_message_context_properties(etype, message_id, None, identifier, False)

        if etype == 'bc.registry.dissolution':
            furnishing_name = email_msg.get('data', {}).get('furnishing', {}).get('furnishingName', None)
            if furnishing_name \
                    and furnishing_name in involuntary_dissolution_stage_1_notification.PROCESSABLE_FURNISHING_NAMES:
                source = email_msg.get('source', None)
                identifier = email_msg.get('identifier', None)
                return create_message_context_properties(etype, message_id, source, identifier, False)
    else:
        email = email_msg.get('email', None)
        etype = email_msg.get('email', {}).get('type', None)
        if not email or not etype:
            return message_context_properties

        if etype == 'businessNumber' \
                and (identifier := email.get('identifier', None)):
            message_id = f'{etype}_{identifier}'
            return create_message_context_properties(etype, message_id, None, identifier, False)

        # pylint: disable=used-before-assignment
        if etype == 'incorporationApplication' \
                and (option := email.get('option', None)) \
                and option == 'mras' \
                and (filing_id := email.get('filingId', None)):
            message_id = f'{etype}_{option}_{filing_id}'
            return create_message_context_properties(etype, message_id, None, None, False)

        # pylint: disable=used-before-assignment
        if etype == 'annualReport' \
                and (option := email.get('option', None)) \
                and option == 'reminder' \
                and (ar_year := email.get('arYear', None)) \
                and (business_id := email.get('businessId', None)):
            message_id = f'{etype}_{option}_{ar_year}_{business_id}'
            return create_message_context_properties(etype, message_id, None, None, False)

        if etype in ('agmLocationChange', 'agmExtension', 'noticeOfWithdrawal', 'appointReceiver', 'ceaseReceiver') \
                and (option := email.get('option', None)) \
                and option == 'COMPLETED' \
                and (filing_id := email.get('filingId', None)):
            # option contains current status of filing - COMPLETED
            message_id = f'{etype}_{option}_{filing_id}'
            return create_message_context_properties(etype, message_id, None, None, False)

        if etype in ('dissolution', 'registration', 'changeOfRegistration',
                     'restoration', 'specialResolution', 'correction', 'amalgamationApplication', 'continuationIn',
                     'transition') \
                and (option := email.get('option', None)) \
                and (filing_id := email.get('filingId', None)):
            # option contains current status of filing - PAID or COMPLETED or CHANGE_REQUESTED, etc
            message_id = f'{etype}_{option}_{filing_id}'
            return create_message_context_properties(etype, message_id, None, None, False)

        if etype in ('consentContinuationOut', 'continuationOut', 'consentAmalgamationOut', 'amalgamationOut') \
                and (option := email.get('option', None)) \
                and option == 'COMPLETED' \
                and (filing_id := email.get('filingId', None)):
            # option contains current status of filing - COMPLETED
            message_id = f'{etype}_{option}_{filing_id}'
            return create_message_context_properties(etype, message_id, None, None, False)

        if etype in filing_notification.FILING_TYPE_CONVERTER.keys() \
                and (option := email.get('option', None)) \
                and (filing_id := email.get('filingId', None)):
            # option contains current status of filing - PAID or COMPLETED
            message_id = f'{etype}_{option}_{filing_id}'
            return create_message_context_properties(etype, message_id, None, None, False)

    return message_context_properties


def create_message_context_properties(message_type, message_id, source, identifier, is_cloud_event_format) -> dict:
    """Create message context properties dict from input param values."""
    return {
        'type': message_type,
        'message_id': message_id,
        'source': source,
        'identifier': identifier,
        'is_cloud_event_format': is_cloud_event_format
    }


def is_processable_message(message_context_properties: dict):
    """Determine if message needs to be processed."""
    msg = None
    is_cloud_event_format = message_context_properties.get('is_cloud_event_format')
    source = message_context_properties.get('source')
    message_id = message_context_properties.get('message_id')

    if is_cloud_event_format:
        if source is None or message_id is None:
            return False, None
        msg: MessageProcessing = \
            MessageProcessingService.find_message_by_source_and_message_id(source, message_id)
    else:
        if message_id is None:
            return False, None
        msg: MessageProcessing = \
            MessageProcessingService.find_message_by_message_id(message_id)

    # limit total number of retries to 1 + msg_retry_num
    msg_retry_num = current_app.config.get('MSG_RETRY_NUM')
    if msg and msg.message_seen_count > msg_retry_num:
        return False, msg

    if msg is None or msg.status == MessageProcessing.Status.FAILED.value:
        return True, msg

    return False, msg


def start_tracking_message(message_context_properties: dict, email_msg: dict, existing_tracker_msg: MessageProcessing):
    """Create a new message with PROCESSING status or update an existing message to PROCESSING status."""
    if existing_tracker_msg:
        return update_message_status_to_processing(existing_tracker_msg)

    return create_processing_message(message_context_properties, email_msg)


def complete_tracking_message(tracker_msg: MessageProcessing):
    """Update existing message state to COMPLETED."""
    update_message_status_to_complete(tracker_msg)


def mark_tracking_message_as_failed(message_context_properties: dict,
                                    email_msg: dict,
                                    existing_tracker_msg: MessageProcessing,
                                    error_details: str):
    """Create a new message with FAILED status or update an existing message to FAILED status."""
    if error_details and len(error_details) > 1000:
        error_details = error_details[:1000]

    if existing_tracker_msg \
            and existing_tracker_msg.status == MessageProcessing.Status.PROCESSING.value:
        return update_message_status_to_failed(existing_tracker_msg, error_details)

    if existing_tracker_msg \
            and existing_tracker_msg.status == MessageProcessing.Status.FAILED.value:
        return update_failed_message(existing_tracker_msg, error_details)

    return create_failed_message(message_context_properties, email_msg, error_details)


def create_message(message_context_properties: dict,
                   msg: str,
                   status: MessageProcessing.Status,
                   error_details: None):
    """Create MessageProcessing record."""
    message_id = message_context_properties.get('message_id')
    source = message_context_properties.get('source')
    identifier = message_context_properties.get('identifier')
    message_type = message_context_properties.get('type')
    new_status = status
    message_json = msg

    result = MessageProcessingService.create_message(
        message_id=message_id,
        source=source,
        identifier=identifier,
        message_type=message_type,
        status=new_status,
        message_json=message_json,
        last_error=error_details,
        seen_count=1
    )
    return result


def create_processing_message(message_context_properties: dict, msg: str):
    """Create message with status of PROCESSING."""
    return create_message(message_context_properties, msg, MessageProcessing.Status.PROCESSING, None)


def create_failed_message(message_context_properties: dict, msg: str, error_details: str):
    """Create message with status of FAILED."""
    return create_message(message_context_properties, msg, MessageProcessing.Status.FAILED, error_details)


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
