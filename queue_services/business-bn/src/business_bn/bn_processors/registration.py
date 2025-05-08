# Copyright © 2022 Province of British Columbia
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
"""File processing rules and actions for the registration of a business."""
import json
import uuid
import xml.etree.ElementTree as Et
from contextlib import suppress
from datetime import UTC
from http import HTTPStatus

import requests
from flask import current_app
from simple_cloudevent import SimpleCloudEvent, to_queue_message
from sqlalchemy import func

from business_account import AccountService
from business_bn.bn_processors import (
    build_input_xml,
    get_business_type_and_sub_type_code,
    get_owners_legal_type,
    program_type_code,
    request_bn_hub,
)
from business_bn.exceptions import BNException, BNRetryExceededException, QueueException
from business_bn.services import gcp_queue
from business_common.utils.datetime import datetime
from business_common.utils.legislation_datetime import LegislationDatetime
from business_model.models import Business, Party, PartyRole, RequestTracker

FIRMS = ("SP", "GP")
CORPS = ("BEN", "BC", "ULC", "CC")


def process( # noqa: PLR0912, PLR0915
    business: Business,  # pylint: disable=too-many-branches, too-many-arguments, too-many-statements
    is_admin: bool = False,
    msg: dict | None = None,
    skip_build=False,
):
    """Process the incoming registration request."""
    max_retry = current_app.config.get("BN_HUB_MAX_RETRY")
    skip_bn_hub_request = current_app.config.get("SKIP_BN_HUB_REQUEST", False)

    message_id, business_number = None, None
    if is_admin:
        if not msg:
            raise QueueException("code issue: msg is required for admin request")

        message_id = msg.get("id")
        business_number = msg.get("header", {}).get("businessNumber") or None
    elif business.tax_id and len(business.tax_id) == 9:
        business_number = business.tax_id

    request_trackers = RequestTracker.find_by(
        business.id, RequestTracker.ServiceName.BN_HUB, RequestTracker.RequestType.INFORM_CRA, message_id=message_id
    )
    if not request_trackers:
        inform_cra_tracker = RequestTracker()
        inform_cra_tracker.business_id = business.id
        inform_cra_tracker.request_type = RequestTracker.RequestType.INFORM_CRA
        inform_cra_tracker.service_name = RequestTracker.ServiceName.BN_HUB
        inform_cra_tracker.retry_number = 0
        inform_cra_tracker.is_processed = False
        inform_cra_tracker.is_admin = is_admin
        inform_cra_tracker.message_id = message_id
    elif (inform_cra_tracker := request_trackers.pop()) and not inform_cra_tracker.is_processed:
        inform_cra_tracker.last_modified = datetime.utcnow()
        inform_cra_tracker.retry_number += 1

    _inform_cra(business, inform_cra_tracker, business_number, skip_build)

    if not skip_bn_hub_request:
        if not inform_cra_tracker.is_processed:
            if skip_build:
                return  # No retry for resubmit admin request

            if inform_cra_tracker.retry_number < max_retry:
                raise BNException(
                    f"Retry number: {inform_cra_tracker.retry_number + 1}"
                    + f" for {business.identifier}, TrackerId: {inform_cra_tracker.id}."
                )

            raise BNRetryExceededException(
                f"Retry exceeded the maximum count for {business.identifier}, TrackerId: {inform_cra_tracker.id}."
            )

        root = Et.fromstring(inform_cra_tracker.response_object)
        transaction_id = root.find("./header/transactionID").text

    request_trackers = RequestTracker.find_by(
        business.id, RequestTracker.ServiceName.BN_HUB, RequestTracker.RequestType.GET_BN, message_id=message_id
    )

    if not request_trackers:
        get_bn_tracker = RequestTracker()
        get_bn_tracker.business_id = business.id
        get_bn_tracker.request_type = RequestTracker.RequestType.GET_BN
        get_bn_tracker.service_name = RequestTracker.ServiceName.BN_HUB
        get_bn_tracker.retry_number = 0
        get_bn_tracker.is_processed = False
        get_bn_tracker.is_admin = is_admin
        get_bn_tracker.message_id = message_id
    elif (get_bn_tracker := request_trackers.pop()) and not get_bn_tracker.is_processed:
        get_bn_tracker.last_modified = datetime.utcnow()
        get_bn_tracker.retry_number += 1

    if not skip_bn_hub_request:
        _get_bn(business, get_bn_tracker, transaction_id)
        if not get_bn_tracker.is_processed:
            if get_bn_tracker.retry_number < max_retry:
                raise BNException(
                    f"Retry number: {get_bn_tracker.retry_number + 1}"
                    + f" for {business.identifier}, TrackerId: {get_bn_tracker.id}."
                )

            raise BNRetryExceededException(
                f"Retry exceeded the maximum count for {business.identifier}, TrackerId: {get_bn_tracker.id}."
            )

    try:
        # Once BN15 received send an email to user
        ce = SimpleCloudEvent(
            id=str(uuid.uuid4()),
            source="business-bn",
            subject="bn",
            time=datetime.now(UTC),
            type="bc.registry.business.bn",
            data={"email": {"type": "businessNumber", "option": "bn", "identifier": business.identifier}},
        )
        topic = current_app.config.get("BUSINESS_EMAILER_TOPIC")
        gcp_queue.publish(topic, to_queue_message(ce))

    except Exception as err:  # pylint: disable=broad-except, unused-variable
        current_app.logger.error("Failed to publish BN email message", exc_info=True)
        raise err

    # publish identifier (so other things know business has changed)
    try:
        ce = SimpleCloudEvent(
            id=str(uuid.uuid4()),
            source="business-bn",
            subject="bn",
            time=datetime.now(UTC),
            type="bc.registry.business.bn",
            data={"identifier": business.identifier},
        )
        topic = current_app.config.get("BUSINESS_EVENTS_TOPIC")
        gcp_queue.publish(topic, to_queue_message(ce))

        current_app.logger.debug(f"Filer pub/sub message: {ce!s}")

    except Exception as err:  # pylint: disable=broad-except;
        current_app.logger.error("Failed to publish BN update for %s %s", business.identifier, err, exc_info=True)


def _inform_cra(
    business: Business,  # pylint: disable=too-many-locals
    request_tracker: RequestTracker,
    business_number: str,
    skip_build: bool,
):
    """Inform CRA about new registration."""
    if request_tracker.is_processed:
        return

    if skip_build:
        input_xml = request_tracker.request_object
    else:
        is_firms = business.legal_type in FIRMS
        is_corps = business.legal_type in Business.CORPS

        owner_legal_type = None
        business_owned = False  # True when SP is owned by GP
        legal_names = ""  # Applicable for Firm registration
        founding_date = LegislationDatetime.as_legislation_timezone(business.founding_date).strftime("%Y-%m-%d")
        parties = []
        if is_firms:
            legal_names, parties = _get_firm_legal_name(business)
            if business.legal_type == "SP" and parties[0].party_type == Party.PartyTypes.ORGANIZATION.value:
                business_owned = True
                owner_legal_type, owner_business = get_owners_legal_type(parties[0].identifier)
                if owner_legal_type == "GP":
                    if owner_business:
                        legal_names, _ = _get_firm_legal_name(owner_business)
                    else:
                        # This should not happen. We migrated all Firms to lear
                        legal_names = "{Unable to find legal name: business is not in BCROS}"
        elif is_corps:
            parties = [
                party_role.party
                for party_role in business.party_roles.all()
                if party_role.role.lower() in (PartyRole.RoleTypes.DIRECTOR.value)
            ]

        business_type_code, business_sub_type_code = get_business_type_and_sub_type_code(
            business.legal_type, business_owned, owner_legal_type
        )

        retry_number = str(request_tracker.retry_number)
        if request_tracker.message_id:
            retry_number = request_tracker.message_id + "-" + retry_number

        input_xml = build_input_xml(
            "create_program_account_request",
            {
                "business": {
                    "identifier": business.identifier,
                    "legalName": business.legal_name,  # name of the new business (operating name of SP, GP)
                    "naicsDescription": business.naics_description,
                },
                "businessNumber": business_number,
                "userRole": "01" if request_tracker.is_admin else "02",
                "retryNumber": retry_number,
                "programTypeCode": program_type_code[business.legal_type],
                "businessTypeCode": business_type_code,
                "businessSubTypeCode": business_sub_type_code,
                "foundingDate": founding_date,
                "legalNames": legal_names,
                "parties": [party.json for party in parties[:5]],
                "deliveryAddress": business.delivery_address.one_or_none().json,
                "mailingAddress": business.mailing_address.one_or_none().json,
                "businessOwned": business_owned,
                "isFirms": is_firms,
                "isCorps": is_corps,
            },
        )

        request_tracker.request_object = input_xml

    status_code, response = request_bn_hub(input_xml)
    if status_code == HTTPStatus.OK:
        with suppress(Et.ParseError):
            root = Et.fromstring(response)
            if root.tag == "SBNAcknowledgement":
                request_tracker.is_processed = True
    request_tracker.response_object = response
    request_tracker.save()


def _get_bn(business: Business, request_tracker: RequestTracker, transaction_id: str):
    """Get business number from CRA."""
    if request_tracker.is_processed:
        return

    request_tracker.request_object = f"{business.identifier}/{transaction_id}"

    status_code, response = _get_program_account(business.identifier, transaction_id)
    if status_code == HTTPStatus.OK:
        program_account_ref_no = str(response["program_account_ref_no"]).zfill(4)
        bn15 = f"{response['business_no']}{response['business_program_id']}{program_account_ref_no}"
        business.tax_id = bn15
        business.save()
        request_tracker.is_processed = True

    request_tracker.response_object = json.dumps(response)
    request_tracker.save()


def _get_program_account(identifier, transaction_id):
    """Get program_account from colin-api BNI link."""
    try:
        # Note: Dev environment has no BNI link. So this will never work in Dev environment.
        # Use Test environment for testing.
        token = AccountService.get_bearer_token()
        url = f"{current_app.config['COLIN_API']}/programAccount/{identifier}/{transaction_id}"
        response = requests.get(
            url,
            headers={**AccountService.CONTENT_TYPE_JSON, "Authorization": AccountService.BEARER + token},
            timeout=AccountService.timeout,
        )
        return response.status_code, response.json()
    except requests.exceptions.RequestException as err:
        current_app.logger.error(err, exc_info=True)
        return None, str(err)


def _get_firm_legal_name(business: Business):
    """Get sorted firm legal name."""
    sort_name = func.trim(
        func.coalesce(Party.organization_name, "")
        + func.coalesce(Party.last_name + " ", "")
        + func.coalesce(Party.first_name + " ", "")
        + func.coalesce(Party.middle_initial, "")
    )

    parties_query = (
        business.party_roles.join(Party)
        .filter(
            func.lower(PartyRole.role).in_([PartyRole.RoleTypes.PARTNER.value, PartyRole.RoleTypes.PROPRIETOR.value])
        )
        .order_by(sort_name)
    )

    parties = [party_role.party for party_role in parties_query.all()]

    legal_names = ",".join(party.name for party in parties[:2])
    if len(parties) > 2:  # Include only 2 parties in legal name
        legal_names += ", et al"
    return legal_names, parties
