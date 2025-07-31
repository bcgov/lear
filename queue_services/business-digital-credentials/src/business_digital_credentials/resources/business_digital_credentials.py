# Copyright © 2025 Province of British Columbia
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
"""This Module processes simple cloud event messages for Digital Credentials."""
from enum import Enum
from http import HTTPStatus

from flask import Blueprint, current_app, request
from simple_cloudevent import SimpleCloudEvent

from business_digital_credentials.digital_credential_processors import (
    admin_revoke,
    business_number,
    change_of_registration,
    dissolution,
    put_back_on,
)
from business_digital_credentials.exceptions import (
    FilingStatusException,
    QueueException,
)
from business_digital_credentials.services import gcp_queue
from business_digital_credentials.services.gcp_auth import verify_gcp_jwt
from business_model.models import Business, Filing
from business_model.models.types.filings import FilingTypes

bp = Blueprint("worker", __name__)


class AdminMessage(Enum):
    """Business Digital Credential admin message type."""

    REVOKE = "bc.registry.admin.revoke"


class BusinessMessageType(Enum):
    """Business Digital Credential business message type."""

    BN = "bc.registry.business.bn"
    FILING_MESSAGE = "filingMessage"


@bp.route("/", methods=("POST",))
def worker():
    """Use endpoint to process Queue Msg objects."""
    try:
        current_app.logger.debug("Processing worker in DBC")

        if not request.data:
            return {}, HTTPStatus.OK

        if msg := verify_gcp_jwt(request):
            current_app.logger.info(msg)
            return {}, HTTPStatus.FORBIDDEN

        current_app.logger.info(f"Incoming raw msg: {request.data!s}")

        # 1. Get cloud event
        ce = gcp_queue.get_simple_cloud_event(request, wrapped=True)
        if not ce and not isinstance(ce, SimpleCloudEvent):
            # todo: verify this ? this is how it is done in other GCP pub sub consumers
            # Decision here is to return a 200,
            # so the event is removed from the Queue
            current_app.logger.debug(f"ignoring message, raw payload: {ce!s}")
            return {}, HTTPStatus.OK

        current_app.logger.info(f"received ce: {ce!s}")

        # Process event
        process_event(ce)
        return {}, HTTPStatus.OK

    except QueueException as err:
        # Catch Exception so that any error is still caught and the message is removed from the queue
        current_app.logger.error(f"Queue Error: {err}", exc_info=True)
        current_app.logger.error(f"Cloud event that caused error: {ce}")
        return {}, HTTPStatus.BAD_REQUEST
    except FilingStatusException as err:
        # Catch FilingStatusException to handle cases where the filing can't be processed
        # and add to retry logic if needed
        current_app.logger.error(f"Filing Status Error: {err}", exc_info=True)
        current_app.logger.error(f"Cloud event that caused error: {ce}")
        return {}, HTTPStatus.INTERNAL_SERVER_ERROR


def process_event(  # pylint: disable=too-many-branches, too-many-statements  # noqa: PLR0912
    ce: SimpleCloudEvent,
):
    """Process the digital credential-related message subscribed to."""
    etype = ce.type

    current_app.logger.info(f"Processing event type: {etype}")

    if not ce.data or not isinstance(ce.data, dict):
        raise QueueException("Digital credential message is missing data.")

    if etype in (BusinessMessageType.BN.value, AdminMessage.REVOKE.value):
        # When a BN is added or changed or there is a manual administrative update the queue message does not have
        # a data object. We queue the business information using the identifier and revoke/reissue the credential
        # immediately.

        identifier = ce.data.get("identifier")
        if not identifier:
            raise QueueException("Digital credential message is missing identifier.")

        if not (business := Business.find_by_identifier(identifier)):
            raise QueueException(f"Business with identifier: {identifier} not found.")

        current_app.logger.info(
            f"Business record found: {business.identifier} - {business.legal_name}"
        )
        current_app.logger.info(f"record: {vars(business)}")

        if etype == BusinessMessageType.BN.value:
            business_number.process(business)
        elif etype == AdminMessage.REVOKE.value:
            admin_revoke.process(business)

    elif etype == BusinessMessageType.FILING_MESSAGE.value:
        filing_message = ce.data.get("filingMessage")
        if not filing_message:
            raise QueueException("Digital credential message is missing filingMessage.")

        filing_id = filing_message.get("filingIdentifier")
        if not filing_id:
            raise QueueException(
                "Digital credential message is missing filingIdentifier."
            )

        if not (filing := Filing.find_by_id(filing_id)):
            raise QueueException(f"Filing not found for id: {filing_id}.")

        filing_type = filing.filing_type
        current_app.logger.debug(f"Filing type: {filing_type}")
        if filing_type not in (
            FilingTypes.CHANGEOFREGISTRATION.value,
            FilingTypes.DISSOLUTION.value,
            FilingTypes.PUTBACKON.value,
        ):
            current_app.logger.debug(
                f"Unsupported filing type: {filing_type} - message acknowledged"
            )
            return None

        if filing.status != Filing.Status.COMPLETED.value:
            raise FilingStatusException(
                f"Filing with id: {filing_id} processing not complete {filing.status} yet - retry."
            )

        if filing.status != Filing.Status.COMPLETED.value:
            current_app.logger.debug(
                f"Filing with id: {filing_id} processing not complete yet - message acknowledged."
            )
            return None

        # If it's a type we care about, get the business associated with the filing
        business_id = filing.business_id
        if not (business := Business.find_by_internal_id(business_id)):
            raise QueueException(f"Business with internal id: {business_id} not found.")

        current_app.logger.info(
            f"Business record found: {business.identifier} - {business.legal_name}"
        )

        # Process based on filing type
        if filing_type == FilingTypes.CHANGEOFREGISTRATION.value:
            change_of_registration.process(business, filing)
        elif filing_type == FilingTypes.DISSOLUTION.value:
            dissolution.process(business, filing.filing_sub_type)
        elif filing_type == FilingTypes.PUTBACKON.value:
            put_back_on.process(business, filing)

    else:
        # Log unsupported event types but don't throw exception - we want to ack the message
        current_app.logger.info(
            f"Unsupported event type: {etype} - message acknowledged"
        )
        return None
