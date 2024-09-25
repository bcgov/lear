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
"""This module contains all of the Legal Filing specific processors.

Processors hold the logic to communicate with CRA.
"""
import jinja2
import requests
from entity_queue_common.service import QueueServiceManager
from entity_queue_common.service_utils import logger
from flask import current_app
from legal_api.models import Business, RequestTracker


qsm = QueueServiceManager()  # pylint: disable=invalid-name

bn_note = ('Cannot inform CRA about this change before receiving ' +  # pylint: disable=invalid-name
           'Business Number (BN15). Modify the ' +
           'request xml by providing businessRegistrationNumber, businessProgramIdentifier and ' +
           'businessProgramAccountReferenceNumber before resubmitting it.')

program_type_code = {
    'SP': '113',
    'GP': '114',
    'BC': '100',
    'BEN': '100',
    'ULC': '125',
    'CC': '126',
}

document_sub_type = {
    RequestTracker.RequestType.CHANGE_PARTY: '102',
    RequestTracker.RequestType.CHANGE_NAME: '103',
    RequestTracker.RequestType.CHANGE_DELIVERY_ADDRESS: '107',
    RequestTracker.RequestType.CHANGE_MAILING_ADDRESS: '108'
}


def get_business_type_and_sub_type_code(legal_type: str, business_owned: bool, owner_legal_type: str):
    """Get business_type and business_sub_type."""
    business_type = None
    business_sub_type = None

    if legal_type == 'SP':
        if business_owned:  # Owned by an org
            if owner_legal_type in ['GP', 'LP', 'XP', 'LL', 'XL']:
                business_type = '02'  # Partnership
                business_sub_type = '99'  # Business
            elif owner_legal_type in ['S', 'XS']:
                business_type = '03'  # Corporation
                business_sub_type = '09'  # Society
            elif owner_legal_type in ['CP', 'XCP']:
                business_type = '03'  # Corporation
                business_sub_type = '08'  # Association
            elif owner_legal_type in ['QC', 'QD', 'QB', 'QE', 'QA', 'BC', 'BEN',
                                      'A', 'C', 'CBEN', 'LLC', 'CUL', 'ULC', 'CC', 'CCC', 'FI', 'PA']:
                business_type = '03'  # Corporation
                business_sub_type = '99'  # Business
            else:
                business_type = '99'  # Other
                business_sub_type = '99'  # Unknown
        else:  # Owned by an individual
            business_type = '01'  # Sole Proprietorship
            business_sub_type = '01'  # Sole Proprietor
    elif legal_type == 'GP':
        business_type = '02'  # Partnership
        business_sub_type = '99'  # Business

    return business_type, business_sub_type


def build_input_xml(template_name, data):
    """Build input XML.

    Using jinja2 FileSystemLoader to load template from path.
    Which helps jinja2 to identify the file type (which is .xml)
    to perform autoescape of special characters according to the file type.
    """
    template_loader = jinja2.FileSystemLoader(searchpath=current_app.config.get("TEMPLATE_PATH"))
    template_env = jinja2.Environment(loader=template_loader, autoescape=True)
    template = template_env.get_template(f'{template_name}.xml')
    return template.render(data)


def get_splitted_business_number(tax_id: str):
    """Split BN15 as required by CRA."""
    registration_number = ''
    program_identifier = ''
    program_account_reference_number = ''

    if tax_id and len(tax_id) == 15:
        registration_number = tax_id[0:9]
        program_identifier = tax_id[9:11]
        program_account_reference_number = tax_id[11:15]

    return {
        'businessRegistrationNumber': registration_number,
        'businessProgramIdentifier': program_identifier,
        'businessProgramAccountReferenceNumber': program_account_reference_number
    }


def request_bn_hub(input_xml):
    """Get request to BN Hub."""
    try:
        url = current_app.config.get('BN_HUB_API_URL')
        username = current_app.config.get('BN_HUB_CLIENT_ID')
        secret = current_app.config.get('BN_HUB_CLIENT_SECRET')
        response = requests.get(url=url, params={'inputXML': input_xml}, auth=(username, secret))
        return response.status_code, response.text
    except requests.exceptions.RequestException as err:
        logger.error(err, exc_info=True)
        return None, str(err)


def get_owners_legal_type(identifier):
    """Get owners legal type."""
    if not identifier:
        return None, None

    if business := Business.find_by_identifier(identifier):
        return business.legal_type, business

    try:
        url = f'{current_app.config["SEARCH_API"]}/businesses/search/facets?\
                start=0&rows=20&categories=status:ACTIVE&query=value:{identifier}'
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        if results := data.get('searchResults', {}).get('results'):
            for entity in results:
                if entity.get('identifier') == identifier:
                    return entity.get('legalType'), None
        return None, None
    except (requests.exceptions.RequestException, requests.exceptions.HTTPError) as err:
        logger.error(err, exc_info=True)
        return None, None


async def publish_event(payload: dict, subject: str):  # pylint: disable=redefined-outer-name
    """Publish the message onto the NATS subject."""
    await qsm.service.publish(subject, payload)
