# Copyright © 2023 Province of British Columbia
#
# Licensed under the BSD 3 Clause License, (the 'License');
# you may not use this file except in compliance with the License.
# The template for the license can be found here
#    https://opensource.org/license/bsd-3-clause/
#
# Redistribution and use in source and binary forms,
# with or without modification, are permitted provided that the
# following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
# 3. Neither the name of the copyright holder nor the names of its contributors
#    may be used to endorse or promote products derived from this software
#    without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS “AS IS”
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
# THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
"""This Module processes simple cloud event messages for possible cra communication.
"""
from contextlib import suppress
from http import HTTPStatus

from flask import Blueprint
from flask import current_app
from flask import request
from legal_api.models import Filing, LegalEntity
from sentry_sdk import capture_message
from simple_cloudevent import SimpleCloudEvent
from sqlalchemy.exc import OperationalError

from entity_bn.bn_processors import (  # noqa: I001
    Message,
    admin,
    change_of_registration,
    correction,
    dissolution_or_put_back_on,
    registration,
)
from entity_bn.exceptions import BNException, BNRetryExceededException
from entity_bn.services import queue
from entity_bn.services.logging import structured_log

bp = Blueprint("worker", __name__)


@bp.route("/", methods=("POST",))
def worker():
    """Process the incoming cloud event.

    Flow
    --------
    1. Get cloud event
    2. Get filing and business information
    3. Process CRA request
    4. Publish identifier (so other things know business has changed), used to refresh data in business search

    Decisions on returning a 2xx or failing value to
    the Queue should be noted here:
    - Empty or garbaled messages are knocked off the Q
    - If the Filing is already marked paid, skip and knock off Q
    - Once the filing is marked paid, no errors should escape to the Q
    - If there's no matching filing, put back on Q
    """
    structured_log(request, "INFO", f"Incoming raw msg: {request.data}")

    # 1. Get cloud event
    # ##
    if not (ce := queue.get_simple_cloud_event(request)):
        #
        # Decision here is to return a 200,
        # so the event is removed from the Queue
        return {}, HTTPStatus.OK

    structured_log(request, "INFO", f"received ce: {str(ce)}")

    # 2. Get information
    # ##
    if not (message := get_message(ce)):
        # no info, take off Q
        return {}, HTTPStatus.OK

    # 3. Process CRA request
    # ##
    try:
        identifier = process_cra_request(message)
        if identifier:
            # 4. Publish identifier to Q (so other things know business has changed),
            # used to refresh data in business search
            # ##
            cloud_event = SimpleCloudEvent(
                source=__name__[: __name__.find(".")],
                subject="filing",
                type="Filing",
                data={
                    "identifier": identifier,
                    "filingId": message.filing_id,
                },
            )
            with suppress(Exception):
                event_topic = current_app.config.get("ENTITY_EVENT_TOPIC", "filer")
                ret = queue.publish(
                    topic=event_topic, payload=queue.to_queue_message(cloud_event)
                )
                structured_log(
                    request, "INFO", f"publish to entity event: {message.identifier}"
                )

        structured_log(request, "INFO", f"completed ce: {str(ce)}")
        return {}, HTTPStatus.OK

    except OperationalError:
        structured_log(request, "ERROR", f"Queue Blocked - Database Issue: {str(ce)}")
        return {}, HTTPStatus.BAD_REQUEST
        # We don't want to handle the error, as a DB down would drain the queue
    except BNException:
        structured_log(request, "INFO", f"Queue BN Issue: {str(ce)}")
        return {}, HTTPStatus.BAD_REQUEST
        # We don't want to handle the error, try again after sometime
    except BNRetryExceededException as err:
        structured_log(request, "ERROR", f"Queue BN Retry Exceeded: {err}, {str(ce)}")
        return {}, HTTPStatus.OK  # Event is removed from the Queue
    except Exception as err:  # pylint: disable=broad-except
        # Catch Exception so that any error is still caught and the message is removed from the queue
        capture_message("Queue Error:" + str(ce), level="error")
        structured_log(request, "ERROR", f"Queue Error: {err}, {str(ce)}")
        return {}, HTTPStatus.OK  # Event is removed from the Queue


def get_message(ce: SimpleCloudEvent):
    """Return message in the cloud event."""
    if (data := ce.data) and isinstance(data, dict):
        msg = Message()
        msg.id = ce.id
        msg.type = ce.type
        msg.filing_id = ce.data.get("filingId")
        msg.identifier = ce.data.get("identifier")
        msg.request = ce.data.get("request")
        msg.business_number = ce.data.get("businessNumber")
        return msg
    return None


def process_cra_request(
    msg: Message,
):  # pylint: disable=too-many-branches,too-many-statements
    """Process CRA request."""
    if not msg or msg.type not in [
        "bc.registry.business.registration",
        "bc.registry.business.changeOfRegistration",
        "bc.registry.business.correction",
        "bc.registry.business.dissolution",
        "bc.registry.business.putBackOn",
        "bc.registry.admin.bn",
    ]:
        return None

    if msg.type == "bc.registry.admin.bn":
        admin.process(msg)
        return msg.identifier

    filing: Filing = Filing.find_by_id(msg.filing_id)
    if not filing:
        raise Exception

    legal_entity: LegalEntity = LegalEntity.find_by_internal_id(filing.legal_entity_id)
    if not legal_entity:
        raise Exception

    if filing.filing_type == "registration":
        registration.process(legal_entity)
    elif filing.filing_type == "changeOfRegistration":
        change_of_registration.process(legal_entity, filing)
    elif filing.filing_type == "correction" and legal_entity.entity_type in [
        LegalEntity.EntityTypes.SOLE_PROP.value,
        LegalEntity.EntityTypes.PARTNERSHIP.value,
    ]:
        correction.process(legal_entity, filing)
    elif filing.filing_type in [
        "dissolution",
        "putBackOn",
    ] and legal_entity.entity_type in [
        LegalEntity.EntityTypes.SOLE_PROP.value,
        LegalEntity.EntityTypes.PARTNERSHIP.value,
    ]:
        dissolution_or_put_back_on.process(legal_entity, filing)

    return legal_entity.identifier
