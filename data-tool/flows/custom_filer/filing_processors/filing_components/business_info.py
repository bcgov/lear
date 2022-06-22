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

import requests
from flask import current_app
from flask_babel import _ as babel  # noqa: N813
from legal_api.core import BusinessIdentifier, BusinessType
from legal_api.models import Business, Filing
from legal_api.services import NaicsService


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


def update_business_info(corp_num: str, tax_id: str, business: Business, business_info: Dict, filing: Filing):
    """Format and update the business entity from incorporation filing."""
    if corp_num and business and business_info and filing:
        set_legal_name(corp_num, business, business_info)
        business.identifier = corp_num
        business.legal_type = business_info.get('legalType', None)
        business.founding_date = filing.effective_date
        business.last_coa_date = filing.effective_date
        business.last_cod_date = filing.effective_date
        business.tax_id = tax_id
        return business
    return None


def update_naics_info(business: Business, naics: Dict):
    """Update naics info."""
    business.naics_code = naics.get('naicsCode')
    business.naics_description = naics.get('naicsDescription')


def get_next_corp_num(legal_type: str):
    """Retrieve the next available sequential corp-num from Lear or fallback to COLIN."""
    # this gets called if the new services are generating the Business.identifier.
    if legal_type in BusinessType:
        if business_type := BusinessType.get_enum_by_value(legal_type):
            return BusinessIdentifier.next_identifier(business_type)
        return None

    # legacy Business.Identifier generation
    try:
        # TODO: update this to grab the legal 'class' after legal classes have been defined in lear
        if legal_type == Business.LegalTypes.BCOMP.value:
            business_type = 'BC'
        else:
            business_type = legal_type
        resp = requests.post(f'{current_app.config["COLIN_API"]}/{business_type}')
    except requests.exceptions.ConnectionError:
        current_app.logger.error(f'Failed to connect to {current_app.config["COLIN_API"]}')
        return None

    if resp.status_code == 200:
        new_corpnum = int(resp.json()['corpNum'])
        if new_corpnum and new_corpnum <= 9999999:
            # TODO: Fix endpoint
            return f'{business_type}{new_corpnum:07d}'
    return None
