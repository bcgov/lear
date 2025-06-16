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
"""This Module processes simple cloud event messages for Digital Credentials.
"""
from enum import Enum
from http import HTTPStatus

from flask import Blueprint, current_app, request
from simple_cloudevent import SimpleCloudEvent

from business_model.models import Business, Filing
from business_model.models.types.filings import FilingTypes
from business_registry_digital_credentials import digital_credentials_helpers

from business_digital_credentials.exceptions import QueueException
from business_digital_credentials.services import gcp_queue
from business_digital_credentials.digital_credential_processors import (
    admin_revoke,
    business_number,
    change_of_registration,
    dissolution,
    put_back_on,
)

bp = Blueprint("worker", __name__)

class AdminMessage(Enum):
    """Entity Digital Credential admin message type."""

    REVOKE = 'bc.registry.admin.revoke'


class BusinessMessage(Enum):
    """Entity Digital Credential business message type."""

    BN = 'bc.registry.business.bn'
    CHANGE_OF_REGISTRATION = f'bc.registry.business.{FilingTypes.CHANGEOFREGISTRATION.value}'
    DISSOLUTION = f'bc.registry.business.{FilingTypes.DISSOLUTION.value}'
    PUT_BACK_ON = f'bc.registry.business.{FilingTypes.PUTBACKON.value}'


@bp.route("/", methods=("POST",))
def worker():
    """Use endpoint to process Queue Msg objects."""
    try:
        current_app.logger.info("IN worker in DBC")

        # TODO: uncomment and remove log tester
        # if not request.data:
        #     return {}, HTTPStatus.OK
        
        digital_credentials_helpers.log_something()

        # if msg := verify_gcp_jwt(request):
        #     current_app.logger.info(msg)
        #     return {}, HTTPStatus.FORBIDDEN

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
    
    # ruff: noqa: PGH004
    except QueueException as err:  # noqa B902; pylint: disable=W0703; :
        # Catch Exception so that any error is still caught and the message is removed from the queue
        current_app.logger.error("Queue Error: %s", ce, exc_info=True)
        return {}, HTTPStatus.BAD_REQUEST

def process_event(ce: SimpleCloudEvent):  # pylint: disable=too-many-branches, too-many-statements # noqa: PLR0912, PLR0915
    """Process the digital credential-related message subscribed to."""
    etype = ce.type
    if not etype or etype not in [
            BusinessMessage.CHANGE_OF_REGISTRATION.value,
            BusinessMessage.DISSOLUTION.value,
            BusinessMessage.PUT_BACK_ON.value,
            BusinessMessage.BN.value,
            AdminMessage.REVOKE.value
    ]:
        return None

    current_app.logger.info(f"Processing event type: {etype}")

    if not ce.data or not isinstance(ce.data, dict):
        raise QueueException("Digital credential message is missing data.")

    if etype in (BusinessMessage.BN.value, AdminMessage.REVOKE.value):
        # When a BN is added or changed or there is a manual administrative update the queue message does not have
        # a data object. We queue the business information using the identifier and revoke/reissue the credential
        # immediately.

        identifier = ce.data.get('identifier')
        if not identifier:
            raise QueueException("Digital credential message is missing identifier.")

        if not (business := Business.find_by_identifier(identifier)):
            raise Exception(f"Business with identifier: {identifier} not found.")
        
        current_app.logger.info(f"Business record found: {business.identifier} - {business.legal_name}")
        current_app.logger.info(f"record: {vars(business)}")

        
        if etype == BusinessMessage.BN.value:
            business_number.process(business)
        elif etype == AdminMessage.REVOKE.value:
            admin_revoke.process(business)
    else:
        filing_id = ce.data.get('filing', {}).get('header', {}).get('filingId')
        if not filing_id:
            raise QueueException("Digital credential message is missing filingId.")

        if not (filing := Filing.find_by_id(filing_id)):
            raise QueueException(f"Filing not found for id: {filing_id}.")

        if filing.status != Filing.Status.COMPLETED.value:
            raise QueueException(f"Filing with id: {filing_id} processing not complete.")

        business_id = filing.business_id
        if not (business := Business.find_by_internal_id(business_id)):
            raise Exception(f"Business with internal id: {business_id} not found.")
        
        # Process individual filing events
        if filing.filing_type == FilingTypes.CHANGEOFREGISTRATION.value:
            change_of_registration.process(business, filing)
        elif filing.filing_type == FilingTypes.DISSOLUTION.value:
            dissolution.process(business, filing.filing_sub_type)
        elif filing.filing_type == FilingTypes.PUTBACKON.value:
            put_back_on.process(business, filing)