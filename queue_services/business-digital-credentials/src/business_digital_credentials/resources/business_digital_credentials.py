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
    auth_unaffiliation,
    business_number,
    change_of_directors,
    change_of_registration,
    dissolution,
    put_back_on,
    restoration,
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


# Prefix constants
ADMIN_PREFIX = "bc.registry.admin"
AUTH_PREFIX = "bc.registry.auth"
BUSINESS_PREFIX = "bc.registry.business"


class AdminMessage(Enum):
    """Business Digital Credential admin message type."""

    REVOKE = f"{ADMIN_PREFIX}.revoke"


class AuthMessageType(Enum):
    """Relevant auth messages type subscribed from Auth system."""

    BUSINESS_UNAFFILIATED = f"{AUTH_PREFIX}.businessUnaffiliated"
    TEAM_MEMBER_REMOVED = f"{AUTH_PREFIX}.teamMemberRemoved"


class BusinessMessageType(Enum):
    """Business Digital Credential business message type."""

    BN = f"{BUSINESS_PREFIX}.bn"
    CHANGE_OF_DIRECTORS = f"{BUSINESS_PREFIX}.{FilingTypes.CHANGEOFDIRECTORS.value}"
    CHANGE_OF_REGISTRATION = (
        f"{BUSINESS_PREFIX}.{FilingTypes.CHANGEOFREGISTRATION.value}"
    )
    DISSOLUTION = f"{BUSINESS_PREFIX}.{FilingTypes.DISSOLUTION.value}"
    PUT_BACK_ON = f"{BUSINESS_PREFIX}.{FilingTypes.PUTBACKON.value}"
    RESTORATION = f"{BUSINESS_PREFIX}.{FilingTypes.RESTORATION.value}"

@bp.route("/", methods=("POST",))
def worker():
    """Use endpoint to process Queue Msg objects."""
    try:
        if not request.data:
            return {}, HTTPStatus.OK

        if msg := verify_gcp_jwt(request):
            current_app.logger.info(msg)
            return {}, HTTPStatus.FORBIDDEN

        current_app.logger.info(f"Incoming raw msg: {request.data!s}")

        # 1. Get cloud event
        ce = gcp_queue.get_simple_cloud_event(request, wrapped=True)
        if not ce and not isinstance(ce, SimpleCloudEvent):
            current_app.logger.debug(f"ignoring message, raw payload: {ce!s}")
            return {}, HTTPStatus.OK

        current_app.logger.debug(f"received ce: {ce!s}")

        # Process event
        process_event(ce)
        return {}, HTTPStatus.OK

    except FilingStatusException as err:
        # Catch FilingStatusException to handle cases where the filing can't be processed
        # and add to retry logic if needed
        current_app.logger.error(f"Filing Status Error: {err}", exc_info=True)
        current_app.logger.error(f"Cloud event that caused error: {ce}")
        return {}, HTTPStatus.INTERNAL_SERVER_ERROR
    except (QueueException, Exception) as err:
        # Catch Exception so that any error is still caught and the message is removed from the queue
        current_app.logger.error(f"Queue Error or unhandled: {err}", exc_info=True)
        current_app.logger.error(f"Cloud event that caused error: {ce}")
        return {}, HTTPStatus.BAD_REQUEST


def process_event(  # pylint: disable=too-many-branches, too-many-statements  # noqa: PLR0912, PLR0915
    ce: SimpleCloudEvent,
):
    """Process the digital credential-related message subscribed to."""
    etype = ce.type

    if not ce.data or not isinstance(ce.data, dict):
        raise QueueException("Digital credential message is missing data.")

    if not etype or etype not in [
        BusinessMessageType.CHANGE_OF_DIRECTORS.value,
        BusinessMessageType.CHANGE_OF_REGISTRATION.value,
        BusinessMessageType.DISSOLUTION.value,
        BusinessMessageType.PUT_BACK_ON.value,
        BusinessMessageType.RESTORATION.value,
        BusinessMessageType.BN.value,
        AdminMessage.REVOKE.value,
        AuthMessageType.BUSINESS_UNAFFILIATED.value,
        AuthMessageType.TEAM_MEMBER_REMOVED.value,
    ]:
        current_app.logger.debug(
            f"Unsupported event type: {etype} - message acknowledged"
        )
        return None

    if etype in (BusinessMessageType.BN.value, AdminMessage.REVOKE.value):
        # When a BN is added or changed or there is a manual administrative update the queue message does not have
        # a data object. We queue the business information using the identifier and revoke/reissue the credential
        # immediately.

        identifier = ce.data.get("identifier")
        if not identifier:
            raise QueueException("Digital credential message is missing identifier.")

        if not (business := Business.find_by_identifier(identifier)):
            raise FilingStatusException(
                f"Business with identifier: {identifier} not found."
            )

        current_app.logger.info(
            f"Business record found: {business.identifier} - {business.legal_type} - {business.legal_name}"
        )

        if etype == BusinessMessageType.BN.value:
            business_number.process(business)
        elif etype == AdminMessage.REVOKE.value:
            admin_revoke.process(business)
    
    elif etype in (AuthMessageType.BUSINESS_UNAFFILIATED.value, AuthMessageType.TEAM_MEMBER_REMOVED.value):
        # Handle changes from the auth system regarding affiliation changes
        user_events = ce.data.get("userAffiliationEvents", [])
        if not user_events:
            raise QueueException(
                "Digital credential message is missing or has empty user affiliation events."
            ) from None
    
        # Process each user event
        for event in user_events:
            idp_userid = event.get("idpUserid")
            login_source = event.get("loginSource")
            unaffiliated_identifiers = event.get("unaffiliatedIdentifiers", [])
            
            if not idp_userid or not login_source:
                current_app.logger.warning(
                    f"Event missing IDP user data (idpUserid {idp_userid} or loginSource {login_source}), skipping."
                )
                continue
            
            if not unaffiliated_identifiers:
                current_app.logger.info(
                    f"No unaffiliated identifiers for user: {login_source} {idp_userid}, skipping."
                )
                continue

            # Process unaffiliations to see about Digital Business Card usage
            auth_unaffiliation.process(idp_userid, login_source, unaffiliated_identifiers)

    else:
        # For filing-related events, we need to get the filing from the data object 
        try:
            filing_id = ce.data["filing"]["header"]["filingId"]
        except (KeyError, TypeError):
            raise QueueException(
                "Digital credential message is missing filing data."
            ) from None

        if not filing_id:
            raise QueueException("Digital credential message is missing filingId.")

        if not (filing := Filing.find_by_id(filing_id)):
            raise FilingStatusException(f"Filing not found for id: {filing_id}.")

        filing_type = filing.filing_type
        current_app.logger.debug(f"Filing type: {filing_type}")
        if filing_type not in (
            FilingTypes.CHANGEOFDIRECTORS.value,
            FilingTypes.CHANGEOFREGISTRATION.value,
            FilingTypes.DISSOLUTION.value,
            FilingTypes.PUTBACKON.value,
            FilingTypes.RESTORATION.value,
        ):
            current_app.logger.debug(
                f"Unsupported filing type: {filing_type} - message acknowledged"
            )
            return None

        if filing.status != Filing.Status.COMPLETED.value:
            raise FilingStatusException(
                f"Filing with id: {filing_id} processing not complete {filing.status} yet - retry."
            )

        # If it's a type we care about, get the business associated with the filing
        business_id = filing.business_id
        if not (business := Business.find_by_internal_id(business_id)):
            raise FilingStatusException(f"Business with id: {business_id} not found.")

        current_app.logger.info(
            f"Business record found: {business.identifier} - {business.legal_name}"
        )

        # Process based on filing type
        if filing_type == FilingTypes.CHANGEOFDIRECTORS.value:
            change_of_directors.process(business, filing)
        if filing_type == FilingTypes.CHANGEOFREGISTRATION.value:
            change_of_registration.process(business, filing)
        elif filing_type == FilingTypes.DISSOLUTION.value:
            dissolution.process(business, filing.filing_sub_type)
        elif filing_type == FilingTypes.PUTBACKON.value:
            put_back_on.process(business)
        elif filing_type == FilingTypes.RESTORATION.value:
            restoration.process(business)
