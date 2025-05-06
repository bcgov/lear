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
"""Processing admin actions."""

import xml.etree.ElementTree as Et
from contextlib import suppress
from http import HTTPStatus

from business_bn.bn_processors import registration, request_bn_hub
from business_common.utils.datetime import datetime
from business_model.models import Business, RequestTracker


def process(msg: dict):
    """Process admin actions."""
    business = Business.find_by_identifier(msg["business"]["identifier"])
    if msg["header"]["request"] == "BN15":
        registration.process(business, is_admin=True, msg=msg)
    elif msg["header"]["request"] == "RESUBMIT_INFORM_CRA":
        # Keeping it separate due to the colin-api call to get BN15
        registration.process(business, is_admin=True, msg=msg, skip_build=True)
    elif msg["header"]["request"] in [
        "RESUBMIT_CHANGE_DELIVERY_ADDRESS",
        "RESUBMIT_CHANGE_MAILING_ADDRESS",
        "RESUBMIT_CHANGE_NAME",
        "RESUBMIT_CHANGE_STATUS",
        "RESUBMIT_CHANGE_PARTY",
    ]:
        message_id = msg.get("id")
        request_type = msg["header"]["request"].replace("RESUBMIT_", "")
        request_trackers = RequestTracker.find_by(
            business.id,
            RequestTracker.ServiceName.BN_HUB,
            request_type=RequestTracker.RequestType[request_type],
            message_id=message_id,
        )

        request_tracker = request_trackers.pop()
        if request_tracker.is_processed:
            return

        request_tracker.last_modified = datetime.utcnow()
        request_tracker.retry_number += 1

        status_code, response = request_bn_hub(request_tracker.request_object)
        if status_code == HTTPStatus.OK:
            with suppress(Et.ParseError):
                root = Et.fromstring(response)
                if root.tag == "SBNAcknowledgement":
                    request_tracker.is_processed = True
        request_tracker.response_object = response
        request_tracker.save()
