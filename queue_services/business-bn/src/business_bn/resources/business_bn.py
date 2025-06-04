# Copyright © 2024 Province of British Columbia
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
"""This Module processes simple cloud event messages for possible filing payments."""

from http import HTTPStatus

from flask import Blueprint, current_app, request
from simple_cloudevent import SimpleCloudEvent
from sqlalchemy.exc import OperationalError

from business_bn.bn_processors import (
    admin,
    change_of_registration,
    correction,
    dissolution_or_put_back_on,
    registration,
)
from business_bn.exceptions import BNException, BNRetryExceededException, QueueException
from business_bn.services import gcp_queue, verify_gcp_jwt
from business_common.core.filing import Filing as FilingCore
from business_model.models import Business, Filing

bp = Blueprint("worker", __name__)


@bp.route("/", methods=("POST",))
def worker():
    """
    Process the incoming cloud event.
    """
    try:
        if not request.data:
            return {}, HTTPStatus.OK

        if msg := verify_gcp_jwt(request):
            current_app.logger.info(msg)
            return {}, HTTPStatus.FORBIDDEN

        current_app.logger.info(f"Incoming raw msg: {request.data!s}")

        # Get cloud event
        if not (ce := gcp_queue.get_simple_cloud_event(request, wrapped=True)) and not isinstance(ce, SimpleCloudEvent):
            #
            # Decision here is to return a 200,
            # so the event is removed from the Queue
            current_app.logger.debug(f"ignoring message, raw payload: {ce!s}")
            return {}, HTTPStatus.OK

        current_app.logger.info(f"received ce: {ce!s}")

        process_event(ce)
        return {}, HTTPStatus.OK

    except OperationalError as err:
        current_app.logger.error("Queue Blocked - Database Issue: %s", ce, exc_info=True)
        raise err  # We don't want to handle the error, as a DB down would drain the queue
    except BNException as err:
        current_app.logger.error("Queue BN Issue: %s, %s", err, ce, exc_info=True)
        raise err  # We don't want to handle the error, try again after sometime
    except BNRetryExceededException as err:
        current_app.logger.error("Queue BN Retry Exceeded: %s, %s", err, ce, exc_info=True)
        raise err
    except (QueueException, Exception) as err:  # pylint: disable=broad-except
        current_app.logger.error("Queue Error: %s, %s", err, ce, exc_info=True)
        return {}, HTTPStatus.BAD_REQUEST

def process_event(ce: SimpleCloudEvent):  # pylint: disable=too-many-branches,too-many-statements
    """Process CRA request."""
    event_type = ce.type
    msg = ce.data
    msg["id"] = ce.id
    if event_type not in [
        "bc.registry.business.registration",
        "bc.registry.business.changeOfRegistration",
        "bc.registry.business.correction",
        "bc.registry.business.dissolution",
        "bc.registry.business.putBackOn",
        "bc.registry.admin.bn",
    ]:
        return None

    if event_type == "bc.registry.admin.bn":
        admin.process(msg)
        return

    filing_submission = Filing.find_by_id(msg["filing"]["header"]["filingId"])

    if not filing_submission:
        raise QueueException

    business = Business.find_by_internal_id(filing_submission.business_id)
    if not business:
        raise QueueException

    if filing_submission.filing_type == FilingCore.FilingTypes.REGISTRATION.value:
        registration.process(business)
    elif filing_submission.filing_type == FilingCore.FilingTypes.CHANGEOFREGISTRATION.value:
        current_app.logger.info(f"change of change of registration -- {business.id}")
        change_of_registration.process(business, filing_submission)
    elif filing_submission.filing_type == FilingCore.FilingTypes.CORRECTION.value and business.legal_type in (
        Business.LegalTypes.SOLE_PROP.value,
        Business.LegalTypes.PARTNERSHIP.value,
    ):
        current_app.logger.info(f"correction (on;y for SP and GP) -- {business.id}")
        correction.process(business, filing_submission)
    elif filing_submission.filing_type in (
        FilingCore.FilingTypes.DISSOLUTION.value,
        FilingCore.FilingTypes.PUTBACKON.value,
    ) and business.legal_type in (Business.LegalTypes.SOLE_PROP.value, Business.LegalTypes.PARTNERSHIP.value):
        current_app.logger.info(f"dissolution or put back on -- {business.id}")
        dissolution_or_put_back_on.process(business, filing_submission)
