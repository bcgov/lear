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
"""File processing rules and actions for the correction of registration or change of registration of a business."""
from contextlib import suppress

import dpath
from legal_api.models import Filing, LegalEntity, RequestTracker

from entity_bn.bn_processors.change_of_registration import (
    change_address,
    change_name,
    has_party_name_changed,
    has_previous_address,
)


def process(legal_entity: LegalEntity, filing: Filing):  # pylint: disable=too-many-branches
    """Process the incoming correction request."""
    if filing.meta_data and filing.meta_data.get("correction", {}).get("toBusinessName"):
        change_name(legal_entity, filing, RequestTracker.RequestType.CHANGE_NAME)

    with suppress(KeyError, ValueError):
        if dpath.util.get(filing.filing_json, "filing/correction/parties") and has_party_name_changed(
            legal_entity, filing
        ):
            change_name(legal_entity, filing, RequestTracker.RequestType.CHANGE_PARTY)

    with suppress(KeyError, ValueError):
        if dpath.util.get(filing.filing_json, "filing/correction/offices/businessOffice"):
            if has_previous_address(
                filing.id,
                legal_entity.office_delivery_address.one_or_none().office_id,
                "delivery",
            ):
                change_address(
                    legal_entity,
                    filing,
                    RequestTracker.RequestType.CHANGE_DELIVERY_ADDRESS,
                )

            if has_previous_address(
                filing.id,
                legal_entity.office_mailing_address.one_or_none().office_id,
                "mailing",
            ):
                change_address(
                    legal_entity,
                    filing,
                    RequestTracker.RequestType.CHANGE_MAILING_ADDRESS,
                )
