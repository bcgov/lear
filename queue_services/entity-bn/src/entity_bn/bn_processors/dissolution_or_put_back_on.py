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
"""File processing rules and actions for the dissolution/putBackOn of a business (SP/GP)."""
import xml.etree.ElementTree as Et
from contextlib import suppress
from http import HTTPStatus

from flask import current_app
from legal_api.models import Filing, LegalEntity, RequestTracker
from legal_api.utils.datetime import datetime
from legal_api.utils.legislation_datetime import LegislationDatetime

from entity_bn.bn_processors import (
    bn_note,
    build_input_xml,
    get_splitted_business_number,
    request_bn_hub,
)
from entity_bn.exceptions import BNException, BNRetryExceededException


def process(
    legal_entity: LegalEntity, filing: Filing
):  # pylint: disable=too-many-branches
    """Process the incoming dissolution/putBackOn request (SP/GP)."""
    max_retry = current_app.config.get("BN_HUB_MAX_RETRY")
    request_trackers = RequestTracker.find_by(
        legal_entity.id,
        RequestTracker.ServiceName.BN_HUB,
        RequestTracker.RequestType.CHANGE_STATUS,
        filing.id,
    )
    if not request_trackers:
        request_tracker = RequestTracker()
        request_tracker.legal_entity_id = legal_entity.id
        request_tracker.filing_id = filing.id
        request_tracker.request_type = RequestTracker.RequestType.CHANGE_STATUS
        request_tracker.service_name = RequestTracker.ServiceName.BN_HUB
        request_tracker.retry_number = 0
        request_tracker.is_processed = False
    elif (
        request_tracker := request_trackers.pop()
    ) and not request_tracker.is_processed:
        request_tracker.last_modified = datetime.utcnow()
        request_tracker.retry_number += 1

    if request_tracker.is_processed:
        return

    effective_date = LegislationDatetime.as_legislation_timezone(
        filing.effective_date
    ).strftime("%Y-%m-%d")

    program_account_status_code = {"putBackOn": "01", "dissolution": "02"}
    program_account_reason_code = {"putBackOn": None, "dissolution": "105"}

    alternate_name = legal_entity.alternate_names.first()
    bn15 = alternate_name.bn15

    input_xml = build_input_xml(
        "change_status",
        {
            "retryNumber": str(request_tracker.retry_number),
            "filingId": str(filing.id),
            "programAccountStatusCode": program_account_status_code[filing.filing_type],
            "programAccountReasonCode": program_account_reason_code[filing.filing_type],
            "effectiveDate": effective_date,
            "business": legal_entity.json(),
            **get_splitted_business_number(bn15),
        },
    )

    request_tracker.request_object = input_xml
    if not bn15:
        request_tracker.response_object = bn_note
        request_tracker.save()
        return

    status_code, response = request_bn_hub(input_xml)
    if status_code == HTTPStatus.OK:
        with suppress(Et.ParseError):
            root = Et.fromstring(response)
            if root.tag == "SBNAcknowledgement":
                request_tracker.is_processed = True
    request_tracker.response_object = response
    request_tracker.save()

    if not request_tracker.is_processed:
        if request_tracker.retry_number < max_retry:
            raise BNException(
                f"Retry number: {request_tracker.retry_number + 1}"
                + f" for {legal_entity.identifier}, TrackerId: {request_tracker.id}."
            )

        raise BNRetryExceededException(
            f"Retry exceeded the maximum count for {legal_entity.identifier}, TrackerId: {request_tracker.id}."
        )
