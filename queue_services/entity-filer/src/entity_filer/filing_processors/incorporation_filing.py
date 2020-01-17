# Copyright © 2019 Province of British Columbia
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

from legal_api.models import Business, db, Filing, Address
from flask import Flask
from flask_jwt_oidc import JwtManager
from entity_filer import config

import requests

from entity_queue_common.service_utils import logger
from entity_filer.filing_processors import create_office

def get_next_corp_num(business_type, application: Flask):
    """Retrieve the next available sequential corp-num from COLIN"""
    r = requests.get(f'{application.config["COLIN_API"]}/api/v1/businesses')
    
    if r.status_code == 200:
        new_corpnum = r.json()['corpNum']
        if new_corpnum:
            # TODO: Fix endpoint
            return business_type + str(new_corpnum[0])
    return None

def insert_business_info(corp_num: str, business: Business, business_info: Dict):
    if corp_num and business and business_info:
        business.identifier = corp_num
        # TODO: Other properties contained in the NR
    else:
        return None
    return business

def process(business: Business, filing: Dict, app: Flask = None):
    # Extract the filing information for incorporation 
    incorpFiling = filing['incorporationApplication']
    
    if incorpFiling:
        # Extract the office, business, addresses, directors etc. 
        # these will have to be inserted into the db.
        offices = incorpFiling['offices']
        businessInfo = incorpFiling['nameRequest']
        business = Business.find_by_identifier(businessInfo['nrNumber'])
        
        if business:
            # Reserve the Corp Numper for this entity
            corp_num = get_next_corp_num(businessInfo['legalType'], app)

            # Initial insert of the business record
            business = insert_business_info(corp_num, business, businessInfo)

            if business:
                for office_type, addresses in offices.items():
                    office = create_office(business, office_type, addresses)
                    db.session.add(office)
        else:
            logger.error('No business exists for NR number: %s', businessInfo['nrNUmber'])