# Copyright © 2020 Province of British Columbia
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
"""Manages the type of Business."""
from typing import Dict

from flask_babel import _ as babel  # noqa: N813
from legal_api.models import Business, Filing


def set_corp_type(business: Business, business_info: Dict) -> Dict:
    """Set the legal type of the business."""
    if not business:
        return {'error': babel('Business required before type can be set.')}

    try:
        legal_type = business_info.get('legalType')
        if legal_type:
            business.legal_type = legal_type
    except (IndexError, KeyError, TypeError):
        return {'error': babel('A valid legal type must be provided.')}

    return None


def set_legal_name(corp_num: str, business: Business, business_info: Dict):
    """Set the legal_name in the business object."""
    legal_name = business_info.get('legalName', None)
    business.legal_name = legal_name if legal_name else corp_num[2:] + ' B.C. LTD.'


def update_business_info(corp_num: str, business: Business, business_info: Dict, filing: Filing):
    """Format and update the business entity from incorporation filing."""
    if corp_num and business and business_info and filing:
        set_legal_name(corp_num, business, business_info)
        business.identifier = corp_num
        business.legal_type = business_info.get('legalType', None)
        business.founding_date = filing.effective_date
        return business
    return None
