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
from legal_api.models import Business, Filing, RequestTracker

from entity_bn.bn_processors.change_of_registration import (
    change_address,
    change_name,
    has_party_name_changed,
    has_previous_address,
)
from entity_bn.exceptions import BNException


def process(business: Business, filing: Filing):  # pylint: disable=too-many-branches
    """Process the incoming correction request."""
    if not business.tax_id or len(business.tax_id) != 15:
        raise BNException(f'Business {business.identifier}, ' +
                          'Cannot inform CRA about correction before receiving Business Number (BN15).')

    if filing.meta_data and filing.meta_data.get('correction', {}).get('toLegalName'):
        change_name(business, filing, RequestTracker.RequestType.CHANGE_NAME)

    with suppress(KeyError, ValueError):
        if dpath.util.get(filing.filing_json, 'filing/correction/parties') and \
                has_party_name_changed(business, filing):
            change_name(business, filing, RequestTracker.RequestType.CHANGE_PARTY)

    with suppress(KeyError, ValueError):
        if dpath.util.get(filing.filing_json, 'filing/correction/offices/businessOffice'):
            if has_previous_address(filing.transaction_id,
                                    business.delivery_address.one_or_none().office_id, 'delivery'):
                change_address(business, filing, RequestTracker.RequestType.CHANGE_DELIVERY_ADDRESS)

            if has_previous_address(filing.transaction_id,
                                    business.mailing_address.one_or_none().office_id, 'mailing'):
                change_address(business, filing, RequestTracker.RequestType.CHANGE_MAILING_ADDRESS)
