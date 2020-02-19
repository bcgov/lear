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
"""File processing rules and actions for the incorporation of a business."""
from typing import Dict

import requests
from entity_queue_common.service_utils import logger
from flask import Flask
from legal_api.models import Business, db

from entity_filer.filing_processors import create_office


def get_next_corp_num(business_type, application: Flask):
    """Retrieve the next available sequential corp-num from COLIN."""
    resp = requests.get(f'{application.config["COLIN_API"]}/api/v1/businesses')

    if resp.status_code == 200:
        new_corpnum = resp.json()['corpNum']
        if new_corpnum:
            # TODO: Fix endpoint
            return business_type + str(new_corpnum)
    return None


def update_business_info(corp_num: str, business: Business, business_info: Dict):
    """Format and update the business entity from incorporation filing."""
    if corp_num and business and business_info:
        business.identifier = corp_num
        # TODO: Other properties contained in the NR
    else:
        return None
    return business


def process(business: Business, filing: Dict, app: Flask = None):
    """Process the incoming incorporation filing."""
    # Extract the filing information for incorporation
    incorp_filing = filing['incorporationApplication']

    if incorp_filing:
        # Extract the office, business, addresses, directors etc.
        # these will have to be inserted into the db.
        offices = incorp_filing['offices']
        business_info = incorp_filing['nameRequest']

        # Sanity check
        if business and business.identifier == business_info['nrNumber']:
            # Reserve the Corp Numper for this entity
            corp_num = get_next_corp_num(business_info['legalType'], app)

            # Initial insert of the business record
            business = update_business_info(corp_num, business, business_info)

            if business:
                for office_type, addresses in offices.items():
                    office = create_office(business, office_type, addresses)
                    db.session.add(office)
        else:
            logger.error('No business exists for NR number: %s', business_info['nrNUmber'])
