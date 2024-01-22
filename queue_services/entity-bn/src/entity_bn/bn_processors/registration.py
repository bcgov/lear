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
import xml.etree.ElementTree as Et
from contextlib import suppress
from http import HTTPStatus

import requests
from flask import current_app, request
from legal_api.models import ColinEntity, EntityRole, LegalEntity, RequestTracker
from legal_api.services.bootstrap import AccountService
from legal_api.utils.datetime import datetime
from legal_api.utils.legislation_datetime import LegislationDatetime
from simple_cloudevent import SimpleCloudEvent

from entity_bn.bn_processors import (
    Message,
    build_input_xml,
    get_business_type_and_sub_type_code,
    get_owners_legal_type,
    program_type_code,
    request_bn_hub,
)
from entity_bn.exceptions import BNException, BNRetryExceededException
from entity_bn.services import queue
from entity_bn.services.logging import structured_log


FIRMS = ("SP", "GP")
CORPS = ("BEN", "BC", "ULC", "CC")


def process(
    legal_entity: LegalEntity,  # pylint: disable=too-many-branches, too-many-arguments, too-many-statements
    is_admin: bool = False,
    msg: Message = None,
    skip_build=False,
):
    """Process the incoming registration request."""
    max_retry = current_app.config.get("BN_HUB_MAX_RETRY")

    message_id, business_number = None, None
    if is_admin:
        if not msg:
            raise Exception("code issue: msg is required for admin request")

        message_id = msg.id
        business_number = msg.business_number
    elif legal_entity.bn9:
        # TODO: Do we get bn9 from legal entity for SP/GP?
        business_number = legal_entity.bn9

    request_trackers = RequestTracker.find_by(
        legal_entity.id,
        RequestTracker.ServiceName.BN_HUB,
        RequestTracker.RequestType.INFORM_CRA,
        message_id=message_id,
    )
    if not request_trackers:
        inform_cra_tracker = RequestTracker()
        inform_cra_tracker.legal_entity_id = legal_entity.id
        inform_cra_tracker.request_type = RequestTracker.RequestType.INFORM_CRA
        inform_cra_tracker.service_name = RequestTracker.ServiceName.BN_HUB
        inform_cra_tracker.retry_number = 0
        inform_cra_tracker.is_processed = False
        inform_cra_tracker.is_admin = is_admin
        inform_cra_tracker.message_id = message_id
    elif (
        inform_cra_tracker := request_trackers.pop()
    ) and not inform_cra_tracker.is_processed:
        inform_cra_tracker.last_modified = datetime.utcnow()
        inform_cra_tracker.retry_number += 1

    _inform_cra(legal_entity, inform_cra_tracker, business_number, skip_build)

    if not inform_cra_tracker.is_processed:
        if skip_build:
            return  # No retry for resubmit admin request

        if inform_cra_tracker.retry_number < max_retry:
            raise BNException(
                f"Retry number: {inform_cra_tracker.retry_number + 1}"
                + f" for {legal_entity.identifier}, TrackerId: {inform_cra_tracker.id}."
            )

        raise BNRetryExceededException(
            f"Retry exceeded the maximum count for {legal_entity.identifier}, TrackerId: {inform_cra_tracker.id}."
        )

    root = Et.fromstring(inform_cra_tracker.response_object)
    transaction_id = root.find("./header/transactionID").text

    request_trackers = RequestTracker.find_by(
        legal_entity.id,
        RequestTracker.ServiceName.BN_HUB,
        RequestTracker.RequestType.GET_BN,
        message_id=message_id,
    )

    if not request_trackers:
        get_bn_tracker = RequestTracker()
        get_bn_tracker.legal_entity_id = legal_entity.id
        get_bn_tracker.request_type = RequestTracker.RequestType.GET_BN
        get_bn_tracker.service_name = RequestTracker.ServiceName.BN_HUB
        get_bn_tracker.retry_number = 0
        get_bn_tracker.is_processed = False
        get_bn_tracker.is_admin = is_admin
        get_bn_tracker.message_id = message_id
    elif (get_bn_tracker := request_trackers.pop()) and not get_bn_tracker.is_processed:
        get_bn_tracker.last_modified = datetime.utcnow()
        get_bn_tracker.retry_number += 1

    _get_bn(legal_entity, get_bn_tracker, transaction_id)

    if not get_bn_tracker.is_processed:
        if get_bn_tracker.retry_number < max_retry:
            raise BNException(
                f"Retry number: {get_bn_tracker.retry_number + 1}"
                + f" for {legal_entity.identifier}, TrackerId: {get_bn_tracker.id}."
            )

        raise BNRetryExceededException(
            f"Retry exceeded the maximum count for {legal_entity.identifier}, TrackerId: {get_bn_tracker.id}."
        )

    try:
        # Once BN15 received send an email to user
        cloud_event = SimpleCloudEvent(
            source=__name__[: __name__.find(".")],
            subject="email",
            type="Email",
            data={
                "identifier": legal_entity.identifier,
                "type": "businessNumber",
                "option": "bn",
            },
        )

        mail_topic = current_app.config.get("ENTITY_MAILER_TOPIC", "mailer")
        queue.publish(topic=mail_topic,
                      payload=queue.to_queue_message(cloud_event))
    except (
        Exception
    ) as err:  # pylint: disable=broad-except, unused-variable # noqa F841;
        structured_log(
            request,
            "ERROR",
            "Failed to publish BN email message onto the emailer subject",
        )


def _inform_cra(
    legal_entity: LegalEntity,  # pylint: disable=too-many-locals
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
        is_firms = legal_entity.entity_type in FIRMS
        is_corps = legal_entity.entity_type in CORPS

        owner_legal_type = None
        business_owned = False  # True when SP is owned by org
        founding_date = LegislationDatetime.as_legislation_timezone(
            legal_entity.founding_date
        ).strftime("%Y-%m-%d")
        parties = []
        if is_firms:
            parties = legal_entity.entity_roles.all()
            entity_role = parties[0]
            party = (
                entity_role.related_colin_entity
                if entity_role.is_related_colin_entity
                else entity_role.related_entity
            )

            if legal_entity.entity_type == "SP" and (
                (
                    isinstance(party, LegalEntity)
                    and party.entity_type == LegalEntity.EntityTypes.ORGANIZATION.value
                )
                or isinstance(party, ColinEntity)
            ):
                business_owned = True
                owner_legal_type = get_owners_legal_type(party.identifier)
        elif is_corps:
            parties = [
                entity_role
                for entity_role in legal_entity.entity_roles.all()
                if entity_role.role_type == EntityRole.RoleTypes.director
            ]

        (
            business_type_code,
            business_sub_type_code,
        ) = get_business_type_and_sub_type_code(
            legal_entity.entity_type, business_owned, owner_legal_type
        )

        retry_number = str(request_tracker.retry_number)
        if request_tracker.message_id:
            retry_number = request_tracker.message_id + "-" + retry_number

        input_xml = build_input_xml(
            "create_program_account_request",
            {
                "business": legal_entity.json(),
                "businessNumber": business_number,
                "userRole": "01" if request_tracker.is_admin else "02",
                "retryNumber": retry_number,
                "programTypeCode": program_type_code[legal_entity.entity_type],
                "businessTypeCode": business_type_code,
                "businessSubTypeCode": business_sub_type_code,
                "foundingDate": founding_date,
                "parties": [party.json for party in parties[:5]],
                "deliveryAddress": legal_entity.office_delivery_address.one_or_none().json,
                "mailingAddress": legal_entity.office_mailing_address.one_or_none().json,
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


def _get_bn(
    legal_entity: LegalEntity, request_tracker: RequestTracker, transaction_id: str
):
    """Get business number from CRA."""
    if request_tracker.is_processed:
        return

    request_tracker.request_object = f"{legal_entity.identifier}/{transaction_id}"

    status_code, response = _get_program_account(
        legal_entity.identifier, transaction_id
    )
    if status_code == HTTPStatus.OK:
        program_account_ref_no = str(
            response["program_account_ref_no"]).zfill(4)
        bn15 = f"{response['business_no']}{response['business_program_id']}{program_account_ref_no}"
        alternate_name = legal_entity._alternate_names.first()
        alternate_name.bn15 = bn15
        legal_entity.save()
        request_tracker.is_processed = True

    request_tracker.response_object = json.dumps(response)
    request_tracker.save()


def _get_program_account(identifier, transaction_id):
    """Get program_account from colin-api BNI link."""
    try:
        # Note: Dev environment don’t have BNI link. So this will never work in Dev environment.
        # Use Test environment for testing.
        token = AccountService.get_bearer_token()
        url = f'{current_app.config["COLIN_API"]}/programAccount/{identifier}/{transaction_id}'
        response = requests.get(url,
                                headers={**AccountService.CONTENT_TYPE_JSON,
                                         "Authorization": AccountService.BEARER + token},
                                timeout=AccountService.timeout)
        return response.status_code, response.json()
    except requests.exceptions.RequestException as err:
        structured_log(request, "ERROR", str(err))
        return None, str(err)
